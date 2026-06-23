#!/usr/bin/env python3
"""
Example usage patterns for IRIS Production Diagnostics

This shows how to use the ProductionDiagnostics class programmatically
for common troubleshooting scenarios.
"""

from production_diagnostics import ProductionDiagnostics


def example_1_basic_diagnosis():
    """Example 1: Run a full diagnostic on your production."""
    
    print("="*70)
    print("EXAMPLE 1: Full Production Diagnostic")
    print("="*70)
    
    # Connect to your IRIS instance
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    # Run full diagnostic
    diagnostics.run_full_diagnostic()


def example_2_check_status_only():
    """Example 2: Just check if production is running."""
    
    print("\n" + "="*70)
    print("EXAMPLE 2: Quick Status Check")
    print("="*70)
    
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    status = diagnostics.get_production_status()
    
    # Use the status in your code
    if status.get("state") == "RUNNING":
        print("\n✅ Production is running - all good!")
        return True
    elif status.get("state") == "STOPPED":
        print("\n⏹  Production is stopped - needs attention")
        return False
    else:
        print("\n❌ Production issue detected")
        return False


def example_3_restart_if_stopped():
    """Example 3: Automatically restart production if it's stopped."""
    
    print("\n" + "="*70)
    print("EXAMPLE 3: Auto-Restart if Stopped")
    print("="*70)
    
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    # Check status
    status = diagnostics.get_production_status()
    
    # Restart if stopped
    if status.get("state") == "STOPPED":
        print("\n🔄 Production is stopped, attempting restart...")
        success = diagnostics.start_production()
        
        if success:
            print("✅ Production restarted successfully")
        else:
            print("❌ Failed to restart production")
    else:
        print(f"\n✅ Production state is: {status.get('state')}")


def example_4_monitor_queues():
    """Example 4: Monitor queue depths and alert on backlog."""
    
    print("\n" + "="*70)
    print("EXAMPLE 4: Queue Monitoring")
    print("="*70)
    
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    queues = diagnostics.get_queue_depths()
    
    # Check for high queue depths
    if queues and "queues" in queues:
        for q in queues["queues"]:
            depth = q.get("depth", 0)
            component = q.get("component", "Unknown")
            
            if depth > 100:
                print(f"\n🚨 ALERT: High queue depth on {component}: {depth} messages")
                # You could send an email, Slack message, etc. here
            elif depth > 10:
                print(f"\n⚠️  WARNING: Moderate queue on {component}: {depth} messages")


def example_5_recover_faulted_production():
    """Example 5: Recover a production that's in error state."""
    
    print("\n" + "="*70)
    print("EXAMPLE 5: Recover Faulted Production")
    print("="*70)
    
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    # Check for faulted components
    status = diagnostics.get_production_status()
    
    if status.get("components", {}).get("faulted", 0) > 0:
        print("\n⚠️  Faulted components detected, attempting recovery...")
        success = diagnostics.recover_production()
        
        if success:
            print("✅ Recovery successful, checking status...")
            diagnostics.get_production_status()
        else:
            print("❌ Recovery failed, manual intervention may be needed")
    else:
        print("\n✅ No faulted components detected")


def example_6_check_errors_and_restart():
    """Example 6: Check for recent errors and restart if needed."""
    
    print("\n" + "="*70)
    print("EXAMPLE 6: Error Check & Conditional Restart")
    print("="*70)
    
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    # Check for errors in last hour
    errors = diagnostics.get_recent_errors(hours=1)
    
    if len(errors) > 10:
        print(f"\n🚨 ALERT: {len(errors)} errors in the last hour!")
        print("   Consider restarting the production...")
        
        response = input("\nRestart production? (yes/no): ")
        if response.lower() == 'yes':
            print("\nStopping production...")
            diagnostics.stop_production(timeout=30)
            
            print("Starting production...")
            diagnostics.start_production()
            
            print("\nVerifying status...")
            diagnostics.get_production_status()
    else:
        print(f"\n✅ Only {len(errors)} errors in last hour - within normal range")


def example_7_custom_namespace():
    """Example 7: Working with a custom namespace (e.g., HSCUSTOM)."""
    
    print("\n" + "="*70)
    print("EXAMPLE 7: Custom Namespace (HSCUSTOM)")
    print("="*70)
    
    # Many IRIS applications use custom namespaces
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="HSCUSTOM",  # HealthShare custom namespace
        username="_SYSTEM",
        password="SYS"
    )
    
    diagnostics.run_full_diagnostic()


def example_8_scheduled_monitoring():
    """
    Example 8: A complete monitoring function you could run via cron.
    
    This could be scheduled to run every 5 minutes to monitor production health.
    """
    
    print("\n" + "="*70)
    print("EXAMPLE 8: Automated Monitoring (Cron-style)")
    print("="*70)
    
    diagnostics = ProductionDiagnostics(
        host="localhost",
        port=52773,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    
    # Check 1: Is production running?
    status = diagnostics.get_production_status()
    
    if status.get("state") != "RUNNING":
        print("🚨 CRITICAL: Production is not running!")
        # Send alert here (email, Slack, PagerDuty, etc.)
        return False
    
    # Check 2: Any faulted components?
    if status.get("components", {}).get("faulted", 0) > 0:
        print("⚠️  WARNING: Faulted components detected")
        # Send warning alert
    
    # Check 3: Queue backlog?
    queues = diagnostics.get_queue_depths()
    total_queued = sum(q.get("depth", 0) for q in queues.get("queues", []))
    
    if total_queued > 500:
        print(f"⚠️  WARNING: High queue backlog: {total_queued} messages")
        # Send warning alert
    
    # Check 4: Recent errors?
    errors = diagnostics.get_recent_errors(hours=1)
    
    if len(errors) > 20:
        print(f"⚠️  WARNING: High error rate: {len(errors)} errors in last hour")
        # Send warning alert
    
    print("\n✅ Monitoring check complete")
    return True


if __name__ == "__main__":
    import sys
    
    examples = {
        "1": ("Full diagnostic", example_1_basic_diagnosis),
        "2": ("Status check", example_2_check_status_only),
        "3": ("Auto-restart", example_3_restart_if_stopped),
        "4": ("Queue monitoring", example_4_monitor_queues),
        "5": ("Recover faulted", example_5_recover_faulted_production),
        "6": ("Error check & restart", example_6_check_errors_and_restart),
        "7": ("Custom namespace", example_7_custom_namespace),
        "8": ("Scheduled monitoring", example_8_scheduled_monitoring),
    }
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        if example_num in examples:
            name, func = examples[example_num]
            print(f"\nRunning: {name}\n")
            func()
        else:
            print(f"Unknown example: {example_num}")
    else:
        print("\nAvailable examples:")
        print("-" * 70)
        for num, (name, _) in examples.items():
            print(f"  {num}. {name}")
        print("\nUsage: python production_diagnostics_examples.py <example_number>")
        print("Example: python production_diagnostics_examples.py 1")
