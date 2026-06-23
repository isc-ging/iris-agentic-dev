#!/usr/bin/env python3
"""
IRIS Production Diagnostics via Docker Exec

More reliable alternative that works through docker exec instead of REST API.
Best for containerized IRIS instances.
"""

import subprocess
import json
import sys
import argparse
from typing import Dict, List, Optional


class DockerProductionDiagnostics:
    """Production diagnostics using docker exec."""
    
    def __init__(self, container: str, namespace: str = "USER"):
        self.container = container
        self.namespace = namespace
        
    def _exec_iris(self, code: str) -> str:
        """Execute ObjectScript code via docker exec."""
        # Wrap code to ensure clean JSON output
        wrapped_code = f"""
        set $NAMESPACE = "{self.namespace}"
        try {{
            {code}
        }} catch ex {{
            set result = {{}}
            set result.error = ex.DisplayString()
            write result.%ToJSON()
        }}
        """
        
        cmd = [
            "docker", "exec", "-i", self.container,
            "iris", "session", "IRIS", "-U", self.namespace
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=wrapped_code,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Extract JSON from output (may have extra IRIS output)
            output = result.stdout.strip()
            
            # Find JSON in output
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('{') or line.startswith('['):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            
            # If no JSON found, return raw output
            return {"raw_output": output, "stderr": result.stderr}
            
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_production_status(self) -> Dict:
        """Get production status."""
        print("\n" + "="*70)
        print("STEP 1: Checking Production Status")
        print("="*70)
        
        code = """
        set status = {}
        set status.namespace = $NAMESPACE
        set status.timestamp = $ZDATETIME($HOROLOG, 3)
        
        set prodName = ##class(Ens.Director).GetActiveProductionName()
        set status.productionName = prodName
        
        if prodName = "" {
            set status.state = "NO_PRODUCTION"
            set status.running = 0
        } else {
            set state = ##class(Ens.Director).GetProductionStatus(.isRunning)
            set status.state = $CASE(isRunning, 1:"RUNNING", 0:"STOPPED", :"UNKNOWN")
            set status.running = isRunning
            
            if isRunning {
                set status.components = {}
                set status.components.running = 0
                set status.components.stopped = 0
                set status.components.disabled = 0
                set status.components.faulted = 0
                
                set sql = "SELECT Name, Status, Enabled FROM Ens_Config.Item WHERE Production = ?"
                set result = ##class(%SQL.Statement).%ExecDirect(, sql, prodName)
                
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
            }
        }
        
        write status.%ToJSON()
        """
        
        result = self._exec_iris(code)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            return result
        
        # Display results
        state = result.get("state", "UNKNOWN")
        prod_name = result.get("productionName", "None")
        
        if state == "NO_PRODUCTION":
            print("⚠️  NO ACTIVE PRODUCTION FOUND")
            print("\nℹ️  No production is configured or started in this namespace.")
        elif state == "RUNNING":
            print(f"✅ Production RUNNING: {prod_name}")
            if "components" in result:
                comps = result["components"]
                print(f"\n📊 Component Status:")
                print(f"   ✓ Running:  {comps.get('running', 0)}")
                print(f"   ⏹ Stopped:  {comps.get('stopped', 0)}")
                print(f"   ❌ Faulted:  {comps.get('faulted', 0)}")
                print(f"   ⊘ Disabled: {comps.get('disabled', 0)}")
                
                if comps.get('faulted', 0) > 0:
                    print("\n⚠️  WARNING: Some components are in FAULTED state!")
        elif state == "STOPPED":
            print(f"⏹  Production STOPPED: {prod_name}")
        
        return result
    
    def get_queue_depths(self) -> Dict:
        """Get queue depths."""
        print("\n" + "="*70)
        print("STEP 2: Analyzing Queue Depths")
        print("="*70)
        
        code = """
        set result = {}
        set result.queues = []
        
        set prodName = ##class(Ens.Director).GetActiveProductionName()
        if prodName = "" {
            set result.error = "No active production"
            write result.%ToJSON()
            quit
        }
        
        set sql = "SELECT TargetConfigName, COUNT(*) as QueueDepth FROM Ens.MessageHeader WHERE Status = 'Queued' GROUP BY TargetConfigName"
        set stmt = ##class(%SQL.Statement).%ExecDirect(, sql)
        
        while stmt.%Next() {
            set queue = {}
            set queue.component = stmt.TargetConfigName
            set queue.depth = stmt.QueueDepth
            do result.queues.%Push(queue)
        }
        
        write result.%ToJSON()
        """
        
        result = self._exec_iris(code)
        
        if "error" in result:
            print(f"⚠️  {result['error']}")
            return result
        
        queues = result.get("queues", [])
        
        if not queues:
            print("✅ All queues are empty - no backlog detected")
        else:
            print(f"📋 Found {len(queues)} components with queued messages:\n")
            total = 0
            for q in queues:
                comp = q.get("component", "Unknown")
                depth = q.get("depth", 0)
                total += depth
                
                icon = "🔴" if depth > 100 else "🟡" if depth > 10 else "🟢"
                print(f"   {icon} {comp}: {depth} messages")
            
            print(f"\n   Total queued: {total} messages")
            
            if total > 100:
                print("\n⚠️  WARNING: High queue backlog detected!")
        
        return result
    
    def get_recent_errors(self, hours: int = 1, limit: int = 20) -> List[Dict]:
        """Get recent errors."""
        print("\n" + "="*70)
        print(f"STEP 3: Checking Recent Errors (last {hours} hour(s))")
        print("="*70)
        
        code = f"""
        set result = []
        
        set now = $HOROLOG
        set startTime = $ZDATETIME($HOROLOG - ({hours} / 24), 3, 1)
        
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
        """
        
        result = self._exec_iris(code)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            return []
        
        if isinstance(result, list):
            errors = result
        else:
            errors = result.get("errors", [])
        
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
    
    def start_production(self, production_name: Optional[str] = None) -> bool:
        """Start production."""
        print("\n" + "="*70)
        print("Starting Production")
        print("="*70)
        
        if not production_name:
            # Try to detect
            code = """
            set prodName = ##class(Ens.Director).GetActiveProductionName()
            if prodName = "" {
                set sql = "SELECT TOP 1 Name FROM Ens_Config.Production ORDER BY Name"
                set stmt = ##class(%SQL.Statement).%ExecDirect(, sql)
                if stmt.%Next() {
                    set prodName = stmt.Name
                }
            }
            write {"productionName": (prodName)}.%ToJSON()
            """
            result = self._exec_iris(code)
            production_name = result.get("productionName")
        
        if not production_name:
            print("❌ No production name found")
            return False
        
        print(f"Starting: {production_name}")
        
        code = f"""
        set sc = ##class(Ens.Director).StartProduction("{production_name}")
        if $$$ISOK(sc) {{
            write {{"status":"success"}}.%ToJSON()
        }} else {{
            write {{"status":"error", "message":$SYSTEM.Status.GetErrorText(sc)}}.%ToJSON()
        }}
        """
        
        result = self._exec_iris(code)
        
        if result.get("status") == "success":
            print("✅ Production started successfully")
            return True
        else:
            print(f"❌ Failed: {result.get('message', 'Unknown error')}")
            return False
    
    def stop_production(self, timeout: int = 30) -> bool:
        """Stop production."""
        print("\n" + "="*70)
        print("Stopping Production")
        print("="*70)
        
        code = f"""
        set sc = ##class(Ens.Director).StopProduction({timeout}, 0)
        if $$$ISOK(sc) {{
            write {{"status":"success"}}.%ToJSON()
        }} else {{
            write {{"status":"error", "message":$SYSTEM.Status.GetErrorText(sc)}}.%ToJSON()
        }}
        """
        
        result = self._exec_iris(code)
        
        if result.get("status") == "success":
            print("✅ Production stopped successfully")
            return True
        else:
            print(f"❌ Failed: {result.get('message', 'Unknown error')}")
            return False
    
    def recover_production(self) -> bool:
        """Recover production."""
        print("\n" + "="*70)
        print("Recovering Production")
        print("="*70)
        
        code = """
        set sc = ##class(Ens.Director).RecoverProduction()
        if $$$ISOK(sc) {
            write {"status":"success"}.%ToJSON()
        } else {
            write {"status":"error", "message":$SYSTEM.Status.GetErrorText(sc)}.%ToJSON()
        }
        """
        
        result = self._exec_iris(code)
        
        if result.get("status") == "success":
            print("✅ Production recovered successfully")
            return True
        else:
            print(f"❌ Failed: {result.get('message', 'Unknown error')}")
            return False
    
    def run_full_diagnostic(self):
        """Run complete diagnostic."""
        print("\n" + "="*70)
        print("IRIS INTEROPERABILITY PRODUCTION DIAGNOSTICS")
        print("="*70)
        print(f"Container: {self.container}")
        print(f"Namespace: {self.namespace}")
        print()
        
        status = self.get_production_status()
        
        if status.get("state") == "NO_PRODUCTION":
            print("\n💡 RECOMMENDATION: No production found.")
            return
        
        self.get_queue_depths()
        self.get_recent_errors(hours=1)
        
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        
        if status.get("state") == "STOPPED":
            print("🔧 Production is stopped.")
            print("   → Use: diagnostics.start_production()")
        elif status.get("state") == "RUNNING":
            comps = status.get("components", {})
            if comps.get("faulted", 0) == 0:
                print("✅ Production appears healthy!")


def main():
    parser = argparse.ArgumentParser(description="IRIS Production Diagnostics (Docker)")
    parser.add_argument("--container", required=True, help="IRIS container name")
    parser.add_argument("--namespace", default="USER", help="Namespace")
    parser.add_argument("--action", choices=["diagnose", "start", "stop", "recover"],
                       default="diagnose")
    
    args = parser.parse_args()
    
    diagnostics = DockerProductionDiagnostics(args.container, args.namespace)
    
    if args.action == "diagnose":
        diagnostics.run_full_diagnostic()
    elif args.action == "start":
        diagnostics.start_production()
    elif args.action == "stop":
        diagnostics.stop_production()
    elif args.action == "recover":
        diagnostics.recover_production()


if __name__ == "__main__":
    main()
