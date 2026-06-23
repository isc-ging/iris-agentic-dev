#!/usr/bin/env python3
"""
Quick production diagnostic examples using Python + IRIS REST API

This shows the essential patterns for checking and fixing production issues.
"""

import requests
import json


def check_production_running(host="localhost", port=52773, namespace="USER", 
                             username="SuperUser", password="SYS"):
    """Check if production is running - simplest check"""
    
    # Execute ObjectScript via Atelier REST API
    url = f"http://{host}:{port}/api/atelier/v1/{namespace}/action/execute"
    
    code = """
    set prodName = ##class(Ens.Director).GetActiveProductionName()
    if (prodName = "") {
        write "NO_PRODUCTION"
    } else {
        set state = ##class(Ens.Director).GetProductionStatus()
        write prodName_":"_state
    }
    """
    
    response = requests.post(
        url,
        auth=(username, password),
        json={"code": code}
    )
    
    result = response.json()
    if result.get("status") == "OK":
        output = result.get("content", [""])[0]
        print(f"Production status: {output}")
        
        if output == "NO_PRODUCTION":
            print("\n⚠️  No production is running!")
            return False
        else:
            parts = output.split(":")
            if len(parts) == 2:
                prod_name, state = parts
                print(f"✓ Production '{prod_name}' - State: {state}")
                return state == "1"  # 1 = Running
    
    return False


def get_queue_depths(host="localhost", port=52773, namespace="USER",
                     username="SuperUser", password="SYS"):
    """Check message queue depths - find bottlenecks"""
    
    url = f"http://{host}:{port}/api/atelier/v1/{namespace}/action/execute"
    
    code = """
    set sql = "SELECT Name, Count FROM Ens_Util.Statistics "_
             "WHERE Type='Queue' AND Count > 0 ORDER BY Count DESC"
    set rs = ##class(%SQL.Statement).%ExecDirect(, sql)
    
    set total = 0
    while rs.%Next() {
        write rs.Name_":"_rs.Count_"|"
        set total = total + rs.Count
    }
    write "TOTAL:"_total
    """
    
    response = requests.post(
        url,
        auth=(username, password),
        json={"code": code}
    )
    
    result = response.json()
    if result.get("status") == "OK":
        output = result.get("content", [""])[0]
        
        if not output or output == "TOTAL:0":
            print("✓ No messages in queues")
            return {}
        
        queues = {}
        for item in output.split("|"):
            if ":" in item:
                name, count = item.rsplit(":", 1)
                if name != "TOTAL":
                    queues[name] = int(count)
        
        print(f"\n📊 Queue depths:")
        for name, count in sorted(queues.items(), key=lambda x: x[1], reverse=True):
            print(f"   {name}: {count}")
        
        return queues
    
    return {}


def get_recent_errors(host="localhost", port=52773, namespace="USER",
                      username="SuperUser", password="SYS", hours=1):
    """Get recent error log entries"""
    
    url = f"http://{host}:{port}/api/atelier/v1/{namespace}/action/execute"
    
    code = f"""
    set threshold = $ZDATETIME($HOROLOG - ({hours}/24), 3)
    set sql = "SELECT TOP 5 TimeLogged, ConfigName, Text "_
             "FROM Ens_Util.Log "_
             "WHERE Type = 'Error' AND TimeLogged > ? "_
             "ORDER BY TimeLogged DESC"
    
    set stmt = ##class(%SQL.Statement).%New()
    do stmt.%Prepare(sql)
    set rs = stmt.%Execute(threshold)
    
    while rs.%Next() {{
        write rs.TimeLogged_"|"_rs.ConfigName_"|"_rs.Text_"||"
    }}
    """
    
    response = requests.post(
        url,
        auth=(username, password),
        json={"code": code}
    )
    
    result = response.json()
    if result.get("status") == "OK":
        output = result.get("content", [""])[0]
        
        if not output:
            print("✓ No recent errors")
            return []
        
        errors = []
        for entry in output.split("||"):
            if entry.strip():
                parts = entry.split("|", 2)
                if len(parts) == 3:
                    errors.append({
                        "time": parts[0],
                        "component": parts[1],
                        "message": parts[2][:100]
                    })
        
        if errors:
            print(f"\n⚠️  Found {len(errors)} recent errors:")
            for err in errors:
                print(f"\n   [{err['time']}] {err['component']}")
                print(f"   {err['message']}")
        
        return errors
    
    return []


def start_production(production_name, host="localhost", port=52773, 
                    namespace="USER", username="SuperUser", password="SYS"):
    """Start a production"""
    
    url = f"http://{host}:{port}/api/atelier/v1/{namespace}/action/execute"
    
    code = f"""
    set sc = ##class(Ens.Director).StartProduction("{production_name}")
    if $$$ISERR(sc) {{
        write "ERROR:"_$SYSTEM.Status.GetErrorText(sc)
    }} else {{
        write "OK:Production started"
    }}
    """
    
    response = requests.post(
        url,
        auth=(username, password),
        json={"code": code}
    )
    
    result = response.json()
    if result.get("status") == "OK":
        output = result.get("content", [""])[0]
        
        if output.startswith("OK"):
            print(f"✓ {output}")
            return True
        else:
            print(f"✗ {output}")
            return False
    
    return False


def main():
    """Run quick diagnostic"""
    print("="*60)
    print("IRIS Production Quick Diagnostic")
    print("="*60)
    
    # Connection settings - adjust these for your environment
    config = {
        "host": "localhost",
        "port": 52773,
        "namespace": "USER",
        "username": "SuperUser",
        "password": "SYS"
    }
    
    print(f"\nConnecting to: {config['host']}:{config['port']}/{config['namespace']}\n")
    
    try:
        # Step 1: Check if production is running
        print("1. Checking production status...")
        is_running = check_production_running(**config)
        
        if not is_running:
            print("\n❌ Production is not running!")
            print("\nTo start it:")
            print("   production = 'YourApp.Production'")
            print("   start_production(production, **config)")
            return
        
        print()
        
        # Step 2: Check queues
        print("2. Checking message queues...")
        queues = get_queue_depths(**config)
        
        print()
        
        # Step 3: Check for errors
        print("3. Checking recent errors...")
        errors = get_recent_errors(**config, hours=1)
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        if not queues and not errors:
            print("\n✅ Production appears healthy!")
            print("   - Running normally")
            print("   - No queued messages")
            print("   - No recent errors")
        else:
            if queues:
                total = sum(queues.values())
                print(f"\n⚠️  {total} messages in queues - check for bottlenecks")
            
            if errors:
                print(f"\n⚠️  {len(errors)} recent errors - review above")
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection error: {e}")
        print("\nCheck:")
        print("  - IRIS is running")
        print("  - Port 52773 is correct")
        print("  - Credentials are correct")


if __name__ == "__main__":
    main()
