#!/usr/bin/env python3
"""
IRIS Production - Common Patterns

Quick reference examples for the most common production management tasks.
Copy and adapt these patterns for your own scripts.

Usage:
    python production_patterns.py <command>

Commands:
    status      - Check production status
    start       - Start a production
    stop        - Stop production
    restart     - Restart production
    errors      - Show recent errors
    queues      - Show queue depths
    components  - List all components
"""

import sys
import iris


def connect_to_iris(host='localhost', port=1972, namespace='USER', 
                   username='_SYSTEM', password='SYS'):
    """
    Pattern: Connect to IRIS
    
    Returns tuple: (connection, iris_object)
    """
    conn = iris.connect(
        hostname=host,
        port=port,
        namespace=namespace,
        username=username,
        password=password
    )
    iris_obj = iris.createIRIS(conn)
    return conn, iris_obj


def get_production_status(iris_obj):
    """
    Pattern: Check if production is running and its state
    
    Returns tuple: (production_name, state_code, state_name)
    """
    status = iris_obj.classMethodValue("Ens.Director", "GetProductionStatus", "")
    
    parts = str(status).split("^")
    
    if len(parts) >= 3:
        prod_name = parts[1]
        state = int(parts[2])
        
        states = {
            0: "STOPPED",
            1: "RUNNING",
            2: "SUSPENDED",
            3: "STOPPING",
            4: "TROUBLED",
            5: "NETWORK_STOPPED"
        }
        
        return prod_name, state, states.get(state, "UNKNOWN")
    
    return None, None, None


def start_production(iris_obj, production_name):
    """
    Pattern: Start a production
    
    Returns: True if successful, False otherwise
    """
    result = iris_obj.classMethodValue(
        "Ens.Director",
        "StartProduction",
        production_name,
        0  # timeout (0 = use default)
    )
    
    return str(result) == "1"


def stop_production(iris_obj, timeout=30, force=False):
    """
    Pattern: Stop the running production
    
    timeout: seconds to wait for graceful shutdown
    force: if True, force immediate stop (may lose messages)
    
    Returns: True if successful, False otherwise
    """
    result = iris_obj.classMethodValue(
        "Ens.Director",
        "StopProduction",
        timeout,
        1 if force else 0
    )
    
    return str(result) == "1"


def restart_production(iris_obj, production_name):
    """
    Pattern: Restart a production (stop + start)
    
    Useful for recovering from TROUBLED state
    """
    import time
    
    # Stop
    stop_production(iris_obj, timeout=30, force=False)
    print("✓ Stopped production")
    
    # Wait for clean shutdown
    time.sleep(2)
    
    # Start
    success = start_production(iris_obj, production_name)
    
    if success:
        print("✓ Started production")
    else:
        print("❌ Failed to start production")
    
    return success


def get_recent_errors(conn, limit=20):
    """
    Pattern: Query recent error messages
    
    Returns list of tuples: (time, component, text)
    """
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT TOP {limit}
            TimeCreated,
            SourceConfigName,
            Text
        FROM Ens_Util.Log
        WHERE Type IN (2, 3)  -- Error (2), Alert (3)
        ORDER BY TimeCreated DESC
    """)
    
    errors = cursor.fetchall()
    cursor.close()
    
    return errors


def get_queue_depths(conn):
    """
    Pattern: Get message queue depths by component
    
    Returns list of tuples: (component_name, message_count)
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            TargetConfigName,
            COUNT(*) as Depth
        FROM Ens_Util.Log
        WHERE SessionId IN (
            SELECT TOP 1000 SessionId 
            FROM Ens_Util.Log 
            ORDER BY TimeCreated DESC
        )
        GROUP BY TargetConfigName
        HAVING COUNT(*) > 0
        ORDER BY COUNT(*) DESC
    """)
    
    queues = cursor.fetchall()
    cursor.close()
    
    return queues


def get_components(conn, production_name):
    """
    Pattern: List all components in a production
    
    Returns list of tuples: (name, class_name, enabled)
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Name, ClassName, Enabled
        FROM Ens_Config.Item
        WHERE Production = ?
        ORDER BY Name
    """, [production_name])
    
    components = cursor.fetchall()
    cursor.close()
    
    return components


def enable_component(iris_obj, component_name, enable=True, apply_now=True):
    """
    Pattern: Enable or disable a component
    
    enable: True to enable, False to disable
    apply_now: True to apply immediately (hot-reload)
    
    Returns: True if successful, False otherwise
    """
    result = iris_obj.classMethodValue(
        "Ens.Director",
        "EnableConfigItem",
        component_name,
        1 if enable else 0,
        1 if apply_now else 0
    )
    
    return str(result) == "1"


def update_production(iris_obj):
    """
    Pattern: Apply pending configuration changes (hot-reload)
    
    No restart needed - applies changes immediately
    
    Returns: True if successful, False otherwise
    """
    result = iris_obj.classMethodValue("Ens.Director", "UpdateProduction")
    
    return str(result) == "1"


# ============================================================================
# Command-line interface
# ============================================================================

def cmd_status():
    """Show production status"""
    conn, iris_obj = connect_to_iris()
    
    prod_name, state, state_name = get_production_status(iris_obj)
    
    print(f"Production: {prod_name or 'None'}")
    print(f"Status: {state_name}")
    
    conn.close()


def cmd_start():
    """Start a production"""
    conn, iris_obj = connect_to_iris()
    
    # List available productions
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM Ens_Config.Production")
    prods = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    if not prods:
        print("No productions found")
        conn.close()
        return
    
    print("Available productions:")
    for idx, p in enumerate(prods, 1):
        print(f"  {idx}. {p}")
    
    choice = input(f"\nSelect (1-{len(prods)}): ").strip()
    
    try:
        idx = int(choice) - 1
        prod_name = prods[idx]
        
        print(f"\nStarting {prod_name}...")
        
        if start_production(iris_obj, prod_name):
            print("✓ Production started")
        else:
            print("❌ Failed to start")
    except:
        print("Invalid selection")
    
    conn.close()


def cmd_stop():
    """Stop production"""
    conn, iris_obj = connect_to_iris()
    
    prod_name, state, state_name = get_production_status(iris_obj)
    
    if state == 0:
        print("No production is running")
        conn.close()
        return
    
    print(f"Stopping {prod_name}...")
    
    if stop_production(iris_obj):
        print("✓ Production stopped")
    else:
        print("❌ Failed to stop")
    
    conn.close()


def cmd_restart():
    """Restart production"""
    conn, iris_obj = connect_to_iris()
    
    prod_name, state, state_name = get_production_status(iris_obj)
    
    if state == 0:
        print("No production is running")
        conn.close()
        return
    
    print(f"Restarting {prod_name}...")
    restart_production(iris_obj, prod_name)
    
    conn.close()


def cmd_errors():
    """Show recent errors"""
    conn, iris_obj = connect_to_iris()
    
    errors = get_recent_errors(conn, limit=20)
    
    if not errors:
        print("✓ No recent errors")
    else:
        print(f"Recent errors ({len(errors)}):\n")
        
        for idx, err in enumerate(errors[:10], 1):
            time_created = err[0]
            component = err[1] or "Unknown"
            text = err[2] or "No message"
            
            print(f"{idx}. [{time_created}] {component}")
            print(f"   {text[:100]}")
            print()
    
    conn.close()


def cmd_queues():
    """Show queue depths"""
    conn, iris_obj = connect_to_iris()
    
    queues = get_queue_depths(conn)
    
    if not queues:
        print("✓ No queues")
    else:
        print(f"Queue depths:\n")
        
        for q in queues:
            component = q[0]
            depth = q[1]
            status = "⚠️  HIGH" if depth > 100 else "OK"
            print(f"  {component}: {depth} messages [{status}]")
    
    conn.close()


def cmd_components():
    """List components"""
    conn, iris_obj = connect_to_iris()
    
    prod_name, state, state_name = get_production_status(iris_obj)
    
    if not prod_name:
        print("No production is running")
        conn.close()
        return
    
    components = get_components(conn, prod_name)
    
    print(f"Components in {prod_name} ({len(components)}):\n")
    
    for comp in components:
        name = comp[0]
        class_name = comp[1]
        enabled = "Enabled" if comp[2] else "DISABLED"
        
        print(f"  • {name}")
        print(f"    Class: {class_name}")
        print(f"    Status: {enabled}")
        print()
    
    conn.close()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'status': cmd_status,
        'start': cmd_start,
        'stop': cmd_stop,
        'restart': cmd_restart,
        'errors': cmd_errors,
        'queues': cmd_queues,
        'components': cmd_components,
    }
    
    if command in commands:
        try:
            commands[command]()
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
