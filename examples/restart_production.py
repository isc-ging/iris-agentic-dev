#!/usr/bin/env python3
"""
IRIS Interoperability Production Restart Script

This script safely stops and restarts an IRIS production with proper validation.

Usage:
    python restart_production.py --host localhost --port 52773 --namespace USER --username _SYSTEM --password SYS

    # Just check if restart is needed
    python restart_production.py --check-only

    # Force restart even if running
    python restart_production.py --force

Requirements:
    pip install requests
"""

import argparse
import requests
import json
import time
import sys
from typing import Dict, Optional


class IRISProductionManager:
    """Manage IRIS Interoperability production lifecycle."""
    
    def __init__(self, host: str, port: int, namespace: str, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.namespace = namespace
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def _execute_objectscript(self, code: str) -> Dict:
        """Execute ObjectScript code via Atelier REST API."""
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/execute"
        
        payload = {
            "code": code
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _query_sql(self, query: str) -> Dict:
        """Execute SQL query via Atelier REST API."""
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        payload = {
            "query": query,
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_production_status(self) -> Dict:
        """Get current production status."""
        code = """
        Set sc = ##class(Ens.Director).GetProductionStatus(.prodName, .state)
        Write "{""success"": " _ $Select(sc: "true", 1: "false")
        Write ", ""productionName"": """ _ $Replace(prodName, """", "\""") _ """"
        Write ", ""state"": " _ state
        Write ", ""stateText"": """ _ $Case(state, 0:"Stopped", 1:"Running", 2:"Suspended", 3:"Troubled", :"Unknown") _ """"
        Write "}"
        """
        
        result = self._execute_objectscript(code)
        
        if result["status"] == "success":
            try:
                # Parse the output
                output = result["data"].get("result", {}).get("content", ["{}"])[0]
                return json.loads(output)
            except:
                return {"success": False, "error": "Could not parse production status"}
        else:
            return {"success": False, "error": result.get("message")}
    
    def stop_production(self, timeout: int = 30, force: bool = False) -> Dict:
        """Stop the production."""
        print(f"🛑 Stopping production (timeout: {timeout}s, force: {force})...")
        
        code = f"""
        Set timeout = {timeout}
        Set force = {1 if force else 0}
        Set sc = ##class(Ens.Director).StopProduction(timeout, force)
        
        If $$$ISOK(sc) {{
            Write "{{""success"": true, ""message"": ""Production stopped successfully""}}"
        }} Else {{
            Write "{{""success"": false, ""error"": """ _ $System.Status.GetErrorText(sc) _ """}}"
        }}
        """
        
        result = self._execute_objectscript(code)
        
        if result["status"] == "success":
            try:
                output = result["data"].get("result", {}).get("content", ["{}"])[0]
                return json.loads(output)
            except:
                return {"success": False, "error": "Could not parse stop result"}
        else:
            return {"success": False, "error": result.get("message")}
    
    def start_production(self, production_name: Optional[str] = None) -> Dict:
        """Start the production."""
        # If no production name provided, get the active one
        if not production_name:
            status = self.get_production_status()
            production_name = status.get("productionName", "")
            
            if not production_name:
                return {"success": False, "error": "No production name found. Specify --production parameter."}
        
        print(f"▶️  Starting production: {production_name}...")
        
        code = f"""
        Set prodName = "{production_name}"
        Set sc = ##class(Ens.Director).StartProduction(prodName)
        
        If $$$ISOK(sc) {{
            Write "{{""success"": true, ""message"": ""Production started successfully"", ""productionName"": """ _ prodName _ """}}"
        }} Else {{
            Write "{{""success"": false, ""error"": """ _ $System.Status.GetErrorText(sc) _ """}}"
        }}
        """
        
        result = self._execute_objectscript(code)
        
        if result["status"] == "success":
            try:
                output = result["data"].get("result", {}).get("content", ["{}"])[0]
                return json.loads(output)
            except:
                return {"success": False, "error": "Could not parse start result"}
        else:
            return {"success": False, "error": result.get("message")}
    
    def recover_production(self) -> Dict:
        """Recover a troubled production."""
        print("🔧 Recovering production...")
        
        code = """
        Set sc = ##class(Ens.Director).RecoverProduction()
        
        If $$$ISOK(sc) {
            Write "{""success"": true, ""message"": ""Production recovered successfully""}"
        } Else {
            Write "{""success"": false, ""error"": """ _ $System.Status.GetErrorText(sc) _ """}"
        }
        """
        
        result = self._execute_objectscript(code)
        
        if result["status"] == "success":
            try:
                output = result["data"].get("result", {}).get("content", ["{}"])[0]
                return json.loads(output)
            except:
                return {"success": False, "error": "Could not parse recover result"}
        else:
            return {"success": False, "error": result.get("message")}
    
    def update_production(self) -> Dict:
        """Hot-apply production configuration changes."""
        print("🔄 Updating production configuration...")
        
        code = """
        Set sc = ##class(Ens.Director).UpdateProduction()
        
        If $$$ISOK(sc) {
            Write "{""success"": true, ""message"": ""Production updated successfully""}"
        } Else {
            Write "{""success"": false, ""error"": """ _ $System.Status.GetErrorText(sc) _ """}"
        }
        """
        
        result = self._execute_objectscript(code)
        
        if result["status"] == "success":
            try:
                output = result["data"].get("result", {}).get("content", ["{}"])[0]
                return json.loads(output)
            except:
                return {"success": False, "error": "Could not parse update result"}
        else:
            return {"success": False, "error": result.get("message")}
    
    def restart_production(self, production_name: Optional[str] = None, 
                          timeout: int = 30, force: bool = False) -> bool:
        """Full restart workflow: stop, verify, start, verify."""
        print("\n" + "="*60)
        print("🔄 IRIS Production Restart Workflow")
        print("="*60 + "\n")
        
        # 1. Check current status
        print("Step 1: Checking current status...")
        status = self.get_production_status()
        
        if not status.get("success"):
            print(f"❌ Could not get production status: {status.get('error')}")
            return False
        
        current_state = status.get("state")
        prod_name = status.get("productionName")
        state_text = status.get("stateText")
        
        print(f"   Production: {prod_name}")
        print(f"   Current state: {state_text}\n")
        
        # Use provided name or detected name
        if production_name:
            prod_name = production_name
        
        # 2. Handle troubled state
        if current_state == 3:  # Troubled
            print("⚠️  Production is in 'Troubled' state. Attempting recovery...")
            recover_result = self.recover_production()
            
            if not recover_result.get("success"):
                print(f"❌ Recovery failed: {recover_result.get('error')}")
                return False
            
            print("✅ Production recovered\n")
            time.sleep(2)
        
        # 3. Stop production if running
        if current_state in [1, 2]:  # Running or Suspended
            stop_result = self.stop_production(timeout=timeout, force=force)
            
            if not stop_result.get("success"):
                print(f"❌ Stop failed: {stop_result.get('error')}")
                return False
            
            print("✅ Production stopped\n")
            time.sleep(2)
        else:
            print("ℹ️  Production already stopped, skipping stop step\n")
        
        # 4. Verify stopped
        print("Step 2: Verifying production is stopped...")
        status = self.get_production_status()
        
        if status.get("state") != 0:
            print(f"⚠️  Warning: Production state is {status.get('stateText')}, not Stopped")
        else:
            print("✅ Confirmed stopped\n")
        
        # 5. Start production
        start_result = self.start_production(prod_name)
        
        if not start_result.get("success"):
            print(f"❌ Start failed: {start_result.get('error')}")
            return False
        
        print("✅ Production started\n")
        time.sleep(3)
        
        # 6. Verify running
        print("Step 3: Verifying production is running...")
        status = self.get_production_status()
        
        if status.get("state") != 1:
            print(f"❌ Production state is {status.get('stateText')}, not Running")
            return False
        
        print("✅ Confirmed running\n")
        
        print("="*60)
        print("✅ Production restart completed successfully!")
        print("="*60 + "\n")
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Restart IRIS Interoperability production"
    )
    parser.add_argument("--host", default="localhost", help="IRIS host (default: localhost)")
    parser.add_argument("--port", type=int, default=52773, help="IRIS web port (default: 52773)")
    parser.add_argument("--namespace", default="USER", help="IRIS namespace (default: USER)")
    parser.add_argument("--username", default="_SYSTEM", help="IRIS username (default: _SYSTEM)")
    parser.add_argument("--password", default="SYS", help="IRIS password (default: SYS)")
    parser.add_argument("--production", help="Production class name (auto-detected if not specified)")
    parser.add_argument("--timeout", type=int, default=30, help="Stop timeout in seconds (default: 30)")
    parser.add_argument("--force", action="store_true", help="Force stop (may lose in-flight messages)")
    parser.add_argument("--check-only", action="store_true", help="Only check status, don't restart")
    parser.add_argument("--recover", action="store_true", help="Recover troubled production without full restart")
    
    args = parser.parse_args()
    
    # Create manager instance
    manager = IRISProductionManager(
        host=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    # Check-only mode
    if args.check_only:
        status = manager.get_production_status()
        
        if status.get("success"):
            print(f"Production: {status.get('productionName')}")
            print(f"State: {status.get('stateText')}")
            
            if status.get("state") == 1:
                print("✅ Production is running")
                sys.exit(0)
            else:
                print("❌ Production is not running")
                sys.exit(1)
        else:
            print(f"❌ Error: {status.get('error')}")
            sys.exit(1)
    
    # Recover-only mode
    if args.recover:
        result = manager.recover_production()
        
        if result.get("success"):
            print("✅ Production recovered")
            sys.exit(0)
        else:
            print(f"❌ Recovery failed: {result.get('error')}")
            sys.exit(1)
    
    # Full restart
    success = manager.restart_production(
        production_name=args.production,
        timeout=args.timeout,
        force=args.force
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
