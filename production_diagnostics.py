#!/usr/bin/env python3
"""
IRIS Interoperability Production Diagnostics Toolkit

This script helps diagnose and fix common production issues using Python
and the IRIS REST API.

Usage:
    python production_diagnostics.py --host localhost --port 52773 \
        --namespace USER --username _SYSTEM --password SYS

Features:
    1. Check production status
    2. Analyze queue depths
    3. Search and trace messages
    4. View component logs
    5. Restart/recover production
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from requests.auth import HTTPBasicAuth


class ProductionDiagnostics:
    """Diagnostic toolkit for IRIS Interoperability productions."""
    
    def __init__(self, host: str, port: int, namespace: str, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.namespace = namespace
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def _call_class_method(self, class_name: str, method_name: str, *args) -> Dict:
        """Call an IRIS class method via REST API."""
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        # Build ObjectScript command
        args_str = ",".join([f'"{arg}"' if isinstance(arg, str) else str(arg) for arg in args])
        query = f"SELECT ##class({class_name}).{method_name}({args_str})"
        
        payload = {"query": query}
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}
    
    def _execute_objectscript(self, code: str) -> Dict:
        """Execute ObjectScript code via REST API."""
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/execute"
        
        payload = {"code": code}
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}

    def get_production_status(self, full_status: bool = True) -> Dict:
        """
        Get current production status.
        
        Returns:
            Dict with production state, running components, and health info
        """
        print("\n" + "="*70)
        print("STEP 1: Checking Production Status")
        print("="*70)
        
        code = """
        set status = {}
        set status.namespace = $NAMESPACE
        set status.timestamp = $ZDATETIME($HOROLOG, 3)
        
        // Get production name and state
        set prodName = ##class(Ens.Director).GetActiveProductionName()
        set status.productionName = prodName
        
        if prodName = "" {
            set status.state = "NO_PRODUCTION"
            set status.running = 0
        } else {
            set state = ##class(Ens.Director).GetProductionStatus(.isRunning)
            set status.state = $CASE(isRunning, 1:"RUNNING", 0:"STOPPED", :"UNKNOWN")
            set status.running = isRunning
            
            // Get component counts if running
            if isRunning {
                do ..GetComponentCounts(.status)
            }
        }
        
        write status.%ToJSON()
        quit
        
        GetComponentCounts(status)
            new sql, result, row
            set status.components = {}
            set status.components.running = 0
            set status.components.stopped = 0
            set status.components.disabled = 0
            set status.components.faulted = 0
            
            set sql = "SELECT Name, Status, Enabled FROM Ens_Config.Item WHERE Production = ?"
            set result = ##class(%SQL.Statement).%ExecDirect(, sql, status.productionName)
            
            while result.%Next() {
                set compStatus = result.Status
                set enabled = result.Enabled
                
                if 'enabled {
                    set status.components.disabled = status.components.disabled + 1
                } else {
                    if compStatus = "OK" {
                        set status.components.running = status.components.running + 1
                    } elseif compStatus = "Error" {
                        set status.components.faulted = status.components.faulted + 1
                    } else {
                        set status.components.stopped = status.components.stopped + 1
                    }
                }
            }
            quit
        """
        
        result = self._execute_objectscript(code)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            return result
        
        # Parse the response
        try:
            # Extract JSON from result
            if "result" in result:
                status_data = result["result"]
                if isinstance(status_data, str):
                    status_data = json.loads(status_data)
            else:
                status_data = result
            
            # Display results
            state = status_data.get("state", "UNKNOWN")
            prod_name = status_data.get("productionName", "None")
            
            if state == "NO_PRODUCTION":
                print("⚠️  NO ACTIVE PRODUCTION FOUND")
                print("\nℹ️  No production is configured or started in this namespace.")
                print("   You need to start a production first.")
            elif state == "RUNNING":
                print(f"✅ Production RUNNING: {prod_name}")
                if "components" in status_data:
                    comps = status_data["components"]
                    print(f"\n📊 Component Status:")
                    print(f"   ✓ Running:  {comps.get('running', 0)}")
                    print(f"   ⏹ Stopped:  {comps.get('stopped', 0)}")
                    print(f"   ❌ Faulted:  {comps.get('faulted', 0)}")
                    print(f"   ⊘ Disabled: {comps.get('disabled', 0)}")
                    
                    if comps.get('faulted', 0) > 0:
                        print("\n⚠️  WARNING: Some components are in FAULTED state!")
            elif state == "STOPPED":
                print(f"⏹  Production STOPPED: {prod_name}")
                print("\nℹ️  The production exists but is not running.")
                print("   Use start_production() to start it.")
            
            return status_data
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing response: {e}")
            return {"error": str(e), "raw_result": result}

    def get_queue_depths(self) -> Dict:
        """
        Get queue depths for all production components.
        
        Returns:
            Dict with queue depths per component
        """
        print("\n" + "="*70)
        print("STEP 2: Analyzing Queue Depths")
        print("="*70)
        
        code = """
        set result = {}
        set result.queues = []
        
        // Get active production name
        set prodName = ##class(Ens.Director).GetActiveProductionName()
        if prodName = "" {
            set result.error = "No active production"
            write result.%ToJSON()
            quit
        }
        
        // Query queue depths
        set sql = "SELECT TargetConfigName, COUNT(*) as QueueDepth FROM Ens.MessageHeader WHERE Status = 'Queued' GROUP BY TargetConfigName"
        set stmt = ##class(%SQL.Statement).%ExecDirect(, sql)
        
        while stmt.%Next() {
            set queue = {}
            set queue.component = stmt.TargetConfigName
            set queue.depth = stmt.QueueDepth
            do result.queues.%Push(queue)
        }
        
        write result.%ToJSON()
        quit
        """
        
        result = self._execute_objectscript(code)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            return result
        
        try:
            if "result" in result:
                queue_data = result["result"]
                if isinstance(queue_data, str):
                    queue_data = json.loads(queue_data)
            else:
                queue_data = result
            
            if "error" in queue_data:
                print(f"⚠️  {queue_data['error']}")
                return queue_data
            
            queues = queue_data.get("queues", [])
            
            if not queues:
                print("✅ All queues are empty - no backlog detected")
            else:
                print(f"📋 Found {len(queues)} components with queued messages:\n")
                total = 0
                for q in queues:
                    comp = q.get("component", "Unknown")
                    depth = q.get("depth", 0)
                    total += depth
                    
                    if depth > 100:
                        icon = "🔴"
                    elif depth > 10:
                        icon = "🟡"
                    else:
                        icon = "🟢"
                    
                    print(f"   {icon} {comp}: {depth} messages")
                
                print(f"\n   Total queued: {total} messages")
                
                if total > 100:
                    print("\n⚠️  WARNING: High queue backlog detected!")
                    print("   Check for faulted components or slow operations.")
            
            return queue_data
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing response: {e}")
            return {"error": str(e)}

    def get_recent_errors(self, hours: int = 1, limit: int = 20) -> List[Dict]:
        """
        Get recent error messages from the production.
        
        Args:
            hours: Look back this many hours
            limit: Maximum number of errors to return
            
        Returns:
            List of error messages
        """
        print("\n" + "="*70)
        print(f"STEP 3: Checking Recent Errors (last {hours} hour(s))")
        print("="*70)
        
        code = f"""
        set result = []
        
        // Calculate time range
        set now = $HOROLOG
        set startTime = $ZDATETIME($HOROLOG - ({hours} / 24), 3, 1)
        
        // Query recent errors
        set sql = "SELECT TOP {limit} TimeCreated, SourceConfigName, MessageBodyClassName, Status, ErrorStatus "_
                  "FROM Ens.MessageHeader "_
                  "WHERE TimeCreated > ? AND (Status = 'Error' OR ErrorStatus IS NOT NULL) "_
                  "ORDER BY TimeCreated DESC"
        
        set stmt = ##class(%SQL.Statement).%ExecDirect(, sql, startTime)
        
        while stmt.%Next() {{
            set error = {{}}
            set error.time = stmt.TimeCreated
            set error.component = stmt.SourceConfigName
            set error.messageType = stmt.MessageBodyClassName
            set error.status = stmt.Status
            set error.errorStatus = stmt.ErrorStatus
            do result.%Push(error)
        }}
        
        write result.%ToJSON()
        quit
        """
        
        result = self._execute_objectscript(code)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            return []
        
        try:
            if "result" in result:
                errors_data = result["result"]
                if isinstance(errors_data, str):
                    errors_data = json.loads(errors_data)
            else:
                errors_data = result
            
            if isinstance(errors_data, list):
                errors = errors_data
            else:
                errors = []
            
            if not errors:
                print("✅ No errors found in the specified time range")
            else:
                print(f"❌ Found {len(errors)} error(s):\n")
                for i, err in enumerate(errors, 1):
                    time = err.get("time", "Unknown")
                    comp = err.get("component", "Unknown")
                    error_status = err.get("errorStatus", "Unknown error")
                    
                    print(f"   {i}. [{time}] {comp}")
                    print(f"      Error: {error_status}")
                    print()
            
            return errors
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing response: {e}")
            return []

    def stop_production(self, timeout: int = 30, force: bool = False) -> bool:
        """
        Stop the production gracefully or forcefully.
        
        Args:
            timeout: Seconds to wait for graceful shutdown
            force: If True, force stop without waiting for messages
            
        Returns:
            True if successful
        """
        print("\n" + "="*70)
        print(f"Stopping Production ({'FORCE' if force else 'GRACEFUL'})")
        print("="*70)
        
        force_flag = 1 if force else 0
        
        code = f"""
        set sc = ##class(Ens.Director).StopProduction({timeout}, {force_flag})
        if $$$ISOK(sc) {{
            write {{"status":"success", "message":"Production stopped successfully"}}.%ToJSON()
        }} else {{
            write {{"status":"error", "message":$SYSTEM.Status.GetErrorText(sc)}}.%ToJSON()
        }}
        quit
        """
        
        result = self._execute_objectscript(code)
        
        try:
            if "result" in result:
                stop_result = result["result"]
                if isinstance(stop_result, str):
                    stop_result = json.loads(stop_result)
            else:
                stop_result = result
            
            if stop_result.get("status") == "success":
                print("✅ Production stopped successfully")
                return True
            else:
                print(f"❌ Failed to stop production: {stop_result.get('message', 'Unknown error')}")
                return False
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error: {e}")
            return False

    def start_production(self, production_name: Optional[str] = None) -> bool:
        """
        Start the production.
        
        Args:
            production_name: Name of production to start (if known)
            
        Returns:
            True if successful
        """
        print("\n" + "="*70)
        print("Starting Production")
        print("="*70)
        
        # If no production name provided, try to get the last one
        if not production_name:
            code = """
            set prodName = ##class(Ens.Director).GetActiveProductionName()
            if prodName = "" {
                // Try to get from config
                set sql = "SELECT TOP 1 Name FROM Ens_Config.Production ORDER BY Name"
                set stmt = ##class(%SQL.Statement).%ExecDirect(, sql)
                if stmt.%Next() {
                    set prodName = stmt.Name
                }
            }
            write {"productionName": prodName}.%ToJSON()
            quit
            """
            
            result = self._execute_objectscript(code)
            
            try:
                if "result" in result:
                    prod_data = result["result"]
                    if isinstance(prod_data, str):
                        prod_data = json.loads(prod_data)
                    production_name = prod_data.get("productionName")
            except:
                pass
        
        if not production_name:
            print("❌ No production name provided and none could be detected")
            return False
        
        print(f"Starting production: {production_name}")
        
        code = f"""
        set sc = ##class(Ens.Director).StartProduction("{production_name}")
        if $$$ISOK(sc) {{
            write {{"status":"success", "message":"Production started successfully"}}.%ToJSON()
        }} else {{
            write {{"status":"error", "message":$SYSTEM.Status.GetErrorText(sc)}}.%ToJSON()
        }}
        quit
        """
        
        result = self._execute_objectscript(code)
        
        try:
            if "result" in result:
                start_result = result["result"]
                if isinstance(start_result, str):
                    start_result = json.loads(start_result)
            else:
                start_result = result
            
            if start_result.get("status") == "success":
                print("✅ Production started successfully")
                return True
            else:
                print(f"❌ Failed to start production: {start_result.get('message', 'Unknown error')}")
                return False
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error: {e}")
            return False

    def recover_production(self) -> bool:
        """
        Recover a faulted production (equivalent to Management Portal 'Recover' button).
        
        Returns:
            True if successful
        """
        print("\n" + "="*70)
        print("Recovering Production")
        print("="*70)
        
        code = """
        set sc = ##class(Ens.Director).RecoverProduction()
        if $$$ISOK(sc) {
            write {"status":"success", "message":"Production recovered successfully"}.%ToJSON()
        } else {
            write {"status":"error", "message":$SYSTEM.Status.GetErrorText(sc)}.%ToJSON()
        }
        quit
        """
        
        result = self._execute_objectscript(code)
        
        try:
            if "result" in result:
                recover_result = result["result"]
                if isinstance(recover_result, str):
                    recover_result = json.loads(recover_result)
            else:
                recover_result = result
            
            if recover_result.get("status") == "success":
                print("✅ Production recovered successfully")
                return True
            else:
                print(f"❌ Failed to recover production: {recover_result.get('message', 'Unknown error')}")
                return False
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error: {e}")
            return False

    def run_full_diagnostic(self):
        """Run complete diagnostic workflow."""
        print("\n" + "="*70)
        print("IRIS INTEROPERABILITY PRODUCTION DIAGNOSTICS")
        print("="*70)
        print(f"Namespace: {self.namespace}")
        print(f"Server: {self.base_url}")
        print()
        
        # Step 1: Check status
        status = self.get_production_status()
        
        if status.get("state") == "NO_PRODUCTION":
            print("\n💡 RECOMMENDATION:")
            print("   No production found. You need to:")
            print("   1. Create or import a production configuration")
            print("   2. Start it using start_production()")
            return
        
        # Step 2: Check queues
        queues = self.get_queue_depths()
        
        # Step 3: Check recent errors
        errors = self.get_recent_errors(hours=1)
        
        # Step 4: Provide recommendations
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        
        if status.get("state") == "STOPPED":
            print("🔧 Production is stopped.")
            print("   → Use: diagnostics.start_production()")
        
        elif status.get("state") == "RUNNING":
            comps = status.get("components", {})
            
            if comps.get("faulted", 0) > 0:
                print("🔧 Some components are FAULTED.")
                print("   → Check component configuration")
                print("   → View detailed logs for faulted components")
                print("   → Consider: diagnostics.recover_production()")
            
            if queues and len(queues.get("queues", [])) > 0:
                print("\n🔧 Message queues have backlog.")
                print("   → Check if any components are stopped or slow")
                print("   → Review component performance")
            
            if errors:
                print("\n🔧 Recent errors detected.")
                print("   → Review error messages above")
                print("   → Check component logs for details")
                print("   → Fix configuration issues")
            
            if comps.get("faulted", 0) == 0 and not errors and not queues.get("queues"):
                print("✅ Production appears healthy!")
                print("   No immediate issues detected.")
        
        print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="IRIS Interoperability Production Diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--host", default="localhost", help="IRIS host (default: localhost)")
    parser.add_argument("--port", type=int, default=52773, help="IRIS web port (default: 52773)")
    parser.add_argument("--namespace", default="USER", help="IRIS namespace (default: USER)")
    parser.add_argument("--username", default="_SYSTEM", help="IRIS username (default: _SYSTEM)")
    parser.add_argument("--password", default="SYS", help="IRIS password (default: SYS)")
    
    parser.add_argument("--action", choices=["diagnose", "start", "stop", "recover"],
                      default="diagnose", help="Action to perform (default: diagnose)")
    
    parser.add_argument("--production", help="Production name (for start action)")
    
    args = parser.parse_args()
    
    # Create diagnostics instance
    diagnostics = ProductionDiagnostics(
        host=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    # Perform requested action
    if args.action == "diagnose":
        diagnostics.run_full_diagnostic()
    elif args.action == "start":
        diagnostics.start_production(args.production)
    elif args.action == "stop":
        diagnostics.stop_production()
    elif args.action == "recover":
        diagnostics.recover_production()


if __name__ == "__main__":
    main()
