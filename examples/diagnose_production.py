#!/usr/bin/env python3
"""
IRIS Interoperability Production Diagnostic Script

This script helps diagnose why an IRIS production has stopped processing messages.
It checks production status, queue depths, recent errors, and provides actionable fixes.

Usage:
    python diagnose_production.py --host localhost --port 52773 --namespace USER --username _SYSTEM --password SYS

Requirements:
    pip install requests
"""

import argparse
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sys


class IRISProductionDiagnostic:
    """Diagnostic tool for IRIS Interoperability productions."""
    
    def __init__(self, host: str, port: int, namespace: str, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.namespace = namespace
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def _call_class_method(self, class_name: str, method: str, args: List = None) -> Dict:
        """Call an IRIS class method via Atelier REST API."""
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        # Build ObjectScript command
        if args:
            args_str = ",".join([f'"{arg}"' if isinstance(arg, str) else str(arg) for arg in args])
            command = f"##class({class_name}).{method}({args_str})"
        else:
            command = f"##class({class_name}).{method}()"
        
        payload = {
            "query": f"SELECT {command} AS Result",
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_production_status(self) -> Dict:
        """Get current production status."""
        print("🔍 Checking production status...")
        
        # Use Ens.Director to get production status
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        # Get production name and state
        payload = {
            "query": """
                SELECT 
                    ##class(Ens.Director).GetProductionStatus(.prodName, .state) AS Status,
                    prodName AS ProductionName,
                    state AS State
            """,
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result", {}).get("content", []):
                row = data["result"]["content"][0]
                return {
                    "production_name": row.get("ProductionName", "Unknown"),
                    "state": row.get("State", 0),
                    "state_text": self._state_to_text(row.get("State", 0)),
                    "status": "success"
                }
            else:
                return {"status": "error", "message": "No production found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _state_to_text(self, state: int) -> str:
        """Convert production state integer to text."""
        states = {
            0: "Stopped",
            1: "Running",
            2: "Suspended",
            3: "Troubled"
        }
        return states.get(state, f"Unknown({state})")
    
    def get_component_status(self) -> List[Dict]:
        """Get status of all production components."""
        print("🔍 Checking component status...")
        
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        payload = {
            "query": """
                SELECT 
                    Name,
                    Status,
                    BusinessType
                FROM Ens_Config.Item
                WHERE Production = (
                    SELECT TOP 1 Name 
                    FROM Ens_Config.Production 
                    WHERE Name = ##class(Ens.Director).GetActiveProductionName()
                )
            """,
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            components = []
            for row in data.get("result", {}).get("content", []):
                components.append({
                    "name": row.get("Name"),
                    "status": row.get("Status"),
                    "type": row.get("BusinessType")
                })
            return components
        except Exception as e:
            print(f"❌ Error getting component status: {e}")
            return []
    
    def get_queue_depths(self) -> List[Dict]:
        """Get message queue depths for all components."""
        print("🔍 Checking message queues...")
        
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        payload = {
            "query": """
                SELECT 
                    TargetConfigName,
                    COUNT(*) AS QueueDepth,
                    MIN(TimeCreated) AS OldestMessage
                FROM Ens.MessageHeader
                WHERE Status = 'Queued'
                GROUP BY TargetConfigName
                ORDER BY QueueDepth DESC
            """,
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            queues = []
            for row in data.get("result", {}).get("content", []):
                queues.append({
                    "component": row.get("TargetConfigName"),
                    "depth": row.get("QueueDepth", 0),
                    "oldest": row.get("OldestMessage")
                })
            return queues
        except Exception as e:
            print(f"❌ Error getting queue depths: {e}")
            return []
    
    def get_recent_errors(self, hours: int = 1) -> List[Dict]:
        """Get recent error log entries."""
        print(f"🔍 Checking errors in the last {hours} hour(s)...")
        
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        # Calculate time threshold
        threshold = datetime.now() - timedelta(hours=hours)
        time_str = threshold.strftime("%Y-%m-%d %H:%M:%S")
        
        payload = {
            "query": f"""
                SELECT TOP 50
                    TimeLogged,
                    ConfigName,
                    Text,
                    Type
                FROM Ens_Util.Log
                WHERE Type >= 2
                AND TimeLogged > '{time_str}'
                ORDER BY TimeLogged DESC
            """,
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            errors = []
            for row in data.get("result", {}).get("content", []):
                errors.append({
                    "time": row.get("TimeLogged"),
                    "component": row.get("ConfigName"),
                    "message": row.get("Text"),
                    "type": self._log_type_to_text(row.get("Type", 0))
                })
            return errors
        except Exception as e:
            print(f"❌ Error getting recent errors: {e}")
            return []
    
    def _log_type_to_text(self, log_type: int) -> str:
        """Convert log type integer to text."""
        types = {
            0: "Trace",
            1: "Info",
            2: "Warning",
            3: "Error",
            4: "Alert",
            5: "Assert"
        }
        return types.get(log_type, f"Unknown({log_type})")
    
    def diagnose(self) -> Dict:
        """Run full diagnostic check."""
        print("\n" + "="*60)
        print("🏥 IRIS Interoperability Production Diagnostic")
        print("="*60 + "\n")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "namespace": self.namespace
        }
        
        # 1. Production Status
        status = self.get_production_status()
        results["production"] = status
        
        if status.get("status") == "success":
            print(f"✅ Production: {status['production_name']}")
            print(f"   State: {status['state_text']}")
        else:
            print(f"❌ Production Status Check Failed: {status.get('message')}")
            return results
        
        print()
        
        # 2. Component Status
        components = self.get_component_status()
        results["components"] = components
        
        if components:
            running = sum(1 for c in components if c['status'] == 'Running')
            stopped = sum(1 for c in components if c['status'] == 'Stopped')
            disabled = sum(1 for c in components if c['status'] == 'Disabled')
            
            print(f"📊 Components: {len(components)} total")
            print(f"   ✅ Running: {running}")
            print(f"   ⏸️  Stopped: {stopped}")
            print(f"   🚫 Disabled: {disabled}")
            
            if stopped > 0:
                print(f"\n⚠️  WARNING: {stopped} component(s) are stopped!")
                for c in components:
                    if c['status'] == 'Stopped':
                        print(f"   - {c['name']} ({c['type']})")
        else:
            print("⚠️  No components found")
        
        print()
        
        # 3. Queue Depths
        queues = self.get_queue_depths()
        results["queues"] = queues
        
        if queues:
            total_queued = sum(q['depth'] for q in queues)
            print(f"📬 Message Queues: {total_queued} total queued messages")
            
            if total_queued > 0:
                print("\n⚠️  Messages waiting in queues:")
                for q in queues[:10]:  # Top 10
                    print(f"   - {q['component']}: {q['depth']} messages (oldest: {q['oldest']})")
        else:
            print("✅ No queued messages (queues are empty)")
        
        print()
        
        # 4. Recent Errors
        errors = self.get_recent_errors(hours=1)
        results["errors"] = errors
        
        if errors:
            print(f"❌ Recent Errors: {len(errors)} in the last hour")
            print("\nMost recent errors:")
            for err in errors[:5]:  # Top 5
                print(f"   [{err['time']}] {err['component']}")
                print(f"   {err['type']}: {err['message'][:100]}...")
        else:
            print("✅ No recent errors")
        
        print()
        
        return results
    
    def generate_recommendations(self, results: Dict) -> List[str]:
        """Generate actionable recommendations based on diagnostic results."""
        recommendations = []
        
        prod = results.get("production", {})
        components = results.get("components", [])
        queues = results.get("queues", [])
        errors = results.get("errors", [])
        
        # Production not running
        if prod.get("state") == 0:  # Stopped
            recommendations.append(
                "🔴 CRITICAL: Production is stopped. Start it with:\n"
                f"   python restart_production.py --namespace {self.namespace}"
            )
        
        # Production in troubled state
        if prod.get("state") == 3:  # Troubled
            recommendations.append(
                "🔴 CRITICAL: Production is in 'Troubled' state. Recover it with:\n"
                f"   ##class(Ens.Director).RecoverProduction()"
            )
        
        # Stopped components
        stopped_components = [c for c in components if c['status'] == 'Stopped']
        if stopped_components:
            recommendations.append(
                f"⚠️  {len(stopped_components)} component(s) are stopped. "
                "Check component configuration and enable them in the Management Portal."
            )
        
        # Large queues
        large_queues = [q for q in queues if q['depth'] > 100]
        if large_queues:
            recommendations.append(
                f"⚠️  {len(large_queues)} component(s) have large message queues (>100). "
                "This indicates a bottleneck or component failure. "
                "Check the component's logs and adapter settings."
            )
        
        # Recent errors
        if len(errors) > 10:
            recommendations.append(
                f"⚠️  {len(errors)} errors in the last hour. "
                "Review the error log for specific failure patterns."
            )
        
        # All good
        if not recommendations:
            recommendations.append(
                "✅ Production appears healthy. If messages aren't processing, check:\n"
                "   - Inbound adapter settings (file paths, TCP ports, etc.)\n"
                "   - Message routing rules\n"
                "   - Business logic in Process/Operation classes"
            )
        
        return recommendations


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose IRIS Interoperability production issues"
    )
    parser.add_argument("--host", default="localhost", help="IRIS host (default: localhost)")
    parser.add_argument("--port", type=int, default=52773, help="IRIS web port (default: 52773)")
    parser.add_argument("--namespace", default="USER", help="IRIS namespace (default: USER)")
    parser.add_argument("--username", default="_SYSTEM", help="IRIS username (default: _SYSTEM)")
    parser.add_argument("--password", default="SYS", help="IRIS password (default: SYS)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    # Create diagnostic instance
    diagnostic = IRISProductionDiagnostic(
        host=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    # Run diagnostics
    results = diagnostic.diagnose()
    
    # Generate recommendations
    print("\n" + "="*60)
    print("💡 Recommendations")
    print("="*60 + "\n")
    
    recommendations = diagnostic.generate_recommendations(results)
    for rec in recommendations:
        print(rec)
        print()
    
    # JSON output
    if args.json:
        print("\n" + "="*60)
        print("📄 JSON Output")
        print("="*60 + "\n")
        print(json.dumps(results, indent=2))
    
    # Exit code
    prod = results.get("production", {})
    if prod.get("state") != 1:  # Not running
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
