#!/usr/bin/env python3
"""
Production diagnostic examples - copy these patterns into your own scripts
"""

import requests
import json


class IRISProduction:
    """Simple wrapper for IRIS production operations"""
    
    def __init__(self, host="localhost", port=52773, namespace="USER",
                 username="SuperUser", password="SYS"):
        self.base_url = f"http://{host}:{port}/api/atelier/v1/{namespace}"
        self.auth = (username, password)
    
    def execute(self, code: str) -> dict:
        """Execute ObjectScript code and return JSON response"""
        response = requests.post(
            f"{self.base_url}/action/execute",
            auth=self.auth,
            json={"code": code}
        )
        response.raise_for_status()
        return response.json()
    
    def is_running(self) -> bool:
        """Check if any production is running"""
        code = """
        set name = ##class(Ens.Director).GetActiveProductionName()
        if (name = "") {
            write "false"
        } else {
            set state = ##class(Ens.Director).GetProductionStatus()
            write $CASE(state, 1:"true", :"false")
        }
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            return result.get("content", ["false"])[0] == "true"
        return False
    
    def get_production_name(self) -> str:
        """Get active production name"""
        code = 'write ##class(Ens.Director).GetActiveProductionName()'
        result = self.execute(code)
        if result.get("status") == "OK":
            return result.get("content", [""])[0]
        return ""
    
    def start(self, production_name: str) -> tuple[bool, str]:
        """Start a production - returns (success, message)"""
        code = f"""
        set sc = ##class(Ens.Director).StartProduction("{production_name}")
        if $$$ISERR(sc) {{
            write "ERROR:"_$SYSTEM.Status.GetErrorText(sc)
        }} else {{
            write "OK:Started"
        }}
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            output = result.get("content", [""])[0]
            success = output.startswith("OK")
            return success, output
        return False, "API call failed"
    
    def stop(self, timeout: int = 30) -> tuple[bool, str]:
        """Stop production gracefully - returns (success, message)"""
        code = f"""
        set sc = ##class(Ens.Director).StopProduction({timeout}, 0)
        if $$$ISERR(sc) {{
            write "ERROR:"_$SYSTEM.Status.GetErrorText(sc)
        }} else {{
            write "OK:Stopped"
        }}
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            output = result.get("content", [""])[0]
            success = output.startswith("OK")
            return success, output
        return False, "API call failed"
    
    def recover(self) -> tuple[bool, str]:
        """Recover a faulted production - returns (success, message)"""
        code = """
        set sc = ##class(Ens.Director).RecoverProduction()
        if $$$ISERR(sc) {
            write "ERROR:"_$SYSTEM.Status.GetErrorText(sc)
        } else {
            write "OK:Recovered"
        }
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            output = result.get("content", [""])[0]
            success = output.startswith("OK")
            return success, output
        return False, "API call failed"
    
    def get_queue_summary(self) -> dict[str, int]:
        """Get message queue depths by component"""
        code = """
        set queues = {}
        set sql = "SELECT Name, Count FROM Ens_Util.Statistics "_
                 "WHERE Type='Queue' AND Count > 0 ORDER BY Count DESC"
        set rs = ##class(%SQL.Statement).%ExecDirect(, sql)
        while rs.%Next() {
            set queues.%Set(rs.Name, rs.Count)
        }
        write queues.%ToJSON()
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            content = result.get("content", ["{}"])[0]
            return json.loads(content) if content else {}
        return {}
    
    def get_component_status(self) -> list[dict]:
        """Get status of all production components"""
        code = """
        set components = []
        set prodName = ##class(Ens.Director).GetActiveProductionName()
        if (prodName '= "") {
            set rs = ##class(Ens.Config.Production).EnumerateConfigItemsClose(prodName)
            while rs.%Next() {
                set item = {}
                set item.name = rs.ConfigName
                set item.enabled = rs.Enabled
                set item.class = rs.ClassName
                
                set sc = ##class(Ens.Director).GetItemStatus(rs.ConfigName, .state)
                set item.state = $CASE(state, 0:"OK", 1:"INACTIVE", 2:"TROUBLED", 3:"ERROR", :"UNKNOWN")
                
                do components.%Push(item)
            }
        }
        write components.%ToJSON()
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            content = result.get("content", ["[]"])[0]
            return json.loads(content) if content else []
        return []
    
    def get_recent_errors(self, hours: int = 1, limit: int = 10) -> list[dict]:
        """Get recent error log entries"""
        code = f"""
        set errors = []
        set threshold = $ZDATETIME($HOROLOG - ({hours}/24), 3)
        set sql = "SELECT TOP {limit} TimeLogged, ConfigName, Text, Type "_
                 "FROM Ens_Util.Log "_
                 "WHERE Type IN ('Error', 'Warning') AND TimeLogged > ? "_
                 "ORDER BY TimeLogged DESC"
        
        set stmt = ##class(%SQL.Statement).%New()
        do stmt.%Prepare(sql)
        set rs = stmt.%Execute(threshold)
        
        while rs.%Next() {{
            set err = {{}}
            set err.time = rs.TimeLogged
            set err.component = rs.ConfigName
            set err.message = rs.Text
            set err.type = rs.Type
            do errors.%Push(err)
        }}
        write errors.%ToJSON()
        """
        result = self.execute(code)
        if result.get("status") == "OK":
            content = result.get("content", ["[]"])[0]
            return json.loads(content) if content else []
        return []


# ============================================================================
# Usage Examples
# ============================================================================

def example_basic_check():
    """Example: Basic health check"""
    prod = IRISProduction()
    
    print("Checking production...")
    if prod.is_running():
        name = prod.get_production_name()
        print(f"✓ Production '{name}' is running")
        
        # Check for issues
        queues = prod.get_queue_summary()
        if queues:
            print(f"\n⚠️  Messages in queues:")
            for component, count in queues.items():
                print(f"   {component}: {count}")
        
        errors = prod.get_recent_errors(hours=1)
        if errors:
            print(f"\n⚠️  {len(errors)} recent errors")
    else:
        print("✗ Production is not running")


def example_component_check():
    """Example: Check component status"""
    prod = IRISProduction()
    
    components = prod.get_component_status()
    
    print(f"Production has {len(components)} components:\n")
    
    running = [c for c in components if c['enabled'] and c['state'] == 'OK']
    faulted = [c for c in components if c['enabled'] and c['state'] in ['TROUBLED', 'ERROR']]
    disabled = [c for c in components if not c['enabled']]
    
    print(f"  Running:  {len(running)}")
    print(f"  Faulted:  {len(faulted)}")
    print(f"  Disabled: {len(disabled)}")
    
    if faulted:
        print(f"\n⚠️  Faulted components:")
        for c in faulted:
            print(f"   - {c['name']}: {c['state']}")


def example_start_production():
    """Example: Start a production"""
    prod = IRISProduction()
    
    production_name = "MyApp.Production"
    
    print(f"Starting production: {production_name}")
    success, message = prod.start(production_name)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")


def example_recover_production():
    """Example: Recover faulted production"""
    prod = IRISProduction()
    
    print("Attempting to recover production...")
    success, message = prod.recover()
    
    if success:
        print(f"✓ {message}")
        
        # Check if it's now running
        if prod.is_running():
            print("✓ Production is now running")
        else:
            print("⚠️  Production recovered but not running - may need manual start")
    else:
        print(f"✗ {message}")


def example_full_diagnostic():
    """Example: Complete diagnostic workflow"""
    prod = IRISProduction()
    
    print("="*60)
    print("IRIS Production Diagnostic")
    print("="*60)
    
    # Step 1: Check if running
    print("\n1. Production Status")
    if prod.is_running():
        name = prod.get_production_name()
        print(f"   ✓ Running: {name}")
    else:
        print(f"   ✗ Not running")
        print("\n   Action: Start production with start() method")
        return
    
    # Step 2: Check components
    print("\n2. Component Status")
    components = prod.get_component_status()
    running = sum(1 for c in components if c['enabled'] and c['state'] == 'OK')
    faulted = sum(1 for c in components if c['enabled'] and c['state'] in ['TROUBLED', 'ERROR'])
    
    print(f"   {running} running, {faulted} faulted")
    
    if faulted > 0:
        faulted_list = [c for c in components if c['enabled'] and c['state'] in ['TROUBLED', 'ERROR']]
        for c in faulted_list:
            print(f"   ⚠️  {c['name']}: {c['state']}")
    
    # Step 3: Check queues
    print("\n3. Message Queues")
    queues = prod.get_queue_summary()
    if queues:
        total = sum(queues.values())
        print(f"   {total} messages queued")
        for component, count in list(queues.items())[:5]:
            print(f"   - {component}: {count}")
    else:
        print(f"   ✓ No backlog")
    
    # Step 4: Check errors
    print("\n4. Recent Errors")
    errors = prod.get_recent_errors(hours=1)
    if errors:
        print(f"   ⚠️  {len(errors)} errors in last hour")
        for err in errors[:3]:
            print(f"   - [{err['type']}] {err['component']}: {err['message'][:60]}")
    else:
        print(f"   ✓ No recent errors")
    
    # Summary
    print("\n" + "="*60)
    if faulted == 0 and not queues and not errors:
        print("✅ Production is healthy")
    else:
        print("⚠️  Issues detected - review above")


def example_restart_production():
    """Example: Restart production (stop then start)"""
    prod = IRISProduction()
    
    # Get current production name before stopping
    prod_name = prod.get_production_name()
    if not prod_name:
        print("✗ No production is running")
        return
    
    print(f"Restarting production: {prod_name}")
    
    # Stop
    print("\n1. Stopping...")
    success, message = prod.stop(timeout=30)
    if not success:
        print(f"✗ Stop failed: {message}")
        return
    print(f"✓ {message}")
    
    # Start
    print("\n2. Starting...")
    success, message = prod.start(prod_name)
    if success:
        print(f"✓ {message}")
        print("\n✅ Production restarted successfully")
    else:
        print(f"✗ Start failed: {message}")


if __name__ == "__main__":
    # Run full diagnostic by default
    example_full_diagnostic()
    
    # Uncomment to try other examples:
    # example_basic_check()
    # example_component_check()
    # example_start_production()
    # example_recover_production()
    # example_restart_production()
