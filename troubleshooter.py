#!/usr/bin/env python3
"""
Interactive IRIS Production Troubleshooter

Asks questions to diagnose your specific issue and provides targeted solutions.

Usage:
    python troubleshooter.py
"""

import sys

try:
    from intersystems_pyprod import director
except ImportError:
    print("ERROR: intersystems_pyprod not installed")
    print("Install with: pip install intersystems-pyprod")
    sys.exit(1)


def print_header(text):
    """Print a formatted header."""
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)
    print()


def print_section(text):
    """Print a section header."""
    print()
    print(f"--- {text} ---")
    print()


def ask_yes_no(question):
    """Ask a yes/no question."""
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer 'y' or 'n'")


def get_production_name():
    """Get production name from user or auto-detect."""
    status, prod_name, state = director.get_production_status()
    
    if prod_name:
        print(f"Detected running production: {prod_name}")
        use_detected = ask_yes_no("Use this production?")
        if use_detected:
            return prod_name
    
    # List available productions
    status, names, details = director.list_all_productions()
    
    if not names:
        print("\nNo productions found in this namespace.")
        return None
    
    print("\nAvailable productions:")
    for idx, name in enumerate(names, 1):
        print(f"  {idx}. {name}")
    
    while True:
        try:
            choice = input(f"\nSelect production (1-{len(names)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(names):
                return names[idx]
            else:
                print(f"Please enter a number between 1 and {len(names)}")
        except ValueError:
            print("Please enter a valid number")


def troubleshoot_wont_start(prod_name):
    """Troubleshoot production that won't start."""
    print_section("Troubleshooting: Production Won't Start")
    
    print("Checking current state...")
    status, current_prod, state = director.get_production_status()
    
    if state == 1:  # RUNNING
        print(f"⚠️  A production is already running: {current_prod}")
        print()
        print("Only one production can run at a time per namespace.")
        print()
        
        if current_prod != prod_name:
            print(f"To start {prod_name}, you must first stop {current_prod}")
            if ask_yes_no("Stop the current production and start yours?"):
                print("\nStopping current production...")
                director.stop_production(timeout=30, force=False)
                
                print(f"Starting {prod_name}...")
                status = director.start_production(prod_name)
                
                if status.is_ok():
                    print("✓ Production started successfully!")
                else:
                    print(f"❌ Failed to start: {status.get_error_text()}")
        return
    
    print(f"Attempting to start {prod_name}...")
    status = director.start_production(prod_name)
    
    if status.is_ok():
        print("✓ Production started successfully!")
        
        # Verify
        status, _, state = director.get_production_status()
        if state == 4:
            print("\n⚠️  Production started but is TROUBLED")
            troubleshoot_troubled(prod_name)
        return
    
    # Startup failed
    error = status.get_error_text()
    print(f"\n❌ Failed to start: {error}")
    print()
    
    # Provide specific guidance based on error
    if "not licensed" in error.lower() or "license" in error.lower():
        print("LICENSE ISSUE:")
        print("  Your IRIS instance is not licensed for Interoperability")
        print()
        print("  Fix:")
        print("  1. Go to Management Portal → System → License")
        print("  2. Install an Interoperability-enabled license key")
        print("  3. Restart IRIS")
    
    elif "not found" in error.lower() or "does not exist" in error.lower():
        print("CLASS NOT FOUND:")
        print(f"  The production class '{prod_name}' does not exist")
        print()
        print("  Fix:")
        print("  1. Check the class name spelling")
        print("  2. Compile the production class")
        print("  3. Verify you're in the correct namespace")
    
    elif "database" in error.lower():
        print("DATABASE ISSUE:")
        print("  A required database is not mounted or accessible")
        print()
        print("  Fix:")
        print("  1. Go to Management Portal → System Explorer → Databases")
        print("  2. Verify all databases are mounted")
        print("  3. Check database file permissions")
    
    else:
        print("GENERAL TROUBLESHOOTING:")
        print("  1. Check Event Log:")
        print("     Management Portal → System → Event Log")
        print()
        print("  2. Verify configuration:")
        print("     Management Portal → Interoperability → Configure → Production")
        print()
        print("  3. Check component settings for:")
        print("     - Invalid file paths")
        print("     - Wrong IP addresses or ports")
        print("     - Missing credentials")


def troubleshoot_troubled(prod_name):
    """Troubleshoot a production in troubled state."""
    print_section("Troubleshooting: Production is TROUBLED")
    
    print("A TROUBLED production means a component failed during startup.")
    print()
    print("Checking recent errors...")
    
    messages = director.get_host_messages(prod_name, max_results=50)
    errors = [m for m in messages if 'ERROR' in m.get('status', '').upper()]
    
    if errors:
        print(f"\nFound {len(errors)} error message(s):")
        
        # Group by component
        from collections import defaultdict
        by_component = defaultdict(list)
        
        for err in errors:
            component = err.get('source', 'Unknown')
            by_component[component].append(err)
        
        for component, errs in list(by_component.items())[:3]:
            print(f"\n  Component: {component}")
            print(f"  Error count: {len(errs)}")
            if errs:
                print(f"  Last error: {errs[0].get('time_created')}")
                print(f"  Message type: {errs[0].get('body_class')}")
    else:
        print("\nNo error messages found in recent history.")
    
    print()
    if ask_yes_no("Attempt to recover (stop and restart)?"):
        print("\nStopping production...")
        director.stop_production(timeout=30, force=False)
        
        import time
        time.sleep(2)
        
        print(f"Starting {prod_name}...")
        status = director.start_production(prod_name)
        
        if status.is_ok():
            print("✓ Production restarted")
            
            # Check final state
            status, _, state = director.get_production_status()
            if state == 1:
                print("✓ Production is now RUNNING")
            elif state == 4:
                print("⚠️  Production is still TROUBLED")
                print()
                print("MANUAL INTERVENTION REQUIRED:")
                print("  1. Check Management Portal → Event Log")
                print("  2. Review component adapter settings")
                print("  3. Disable failing components if needed")
        else:
            print(f"❌ Failed to restart: {status.get_error_text()}")


def troubleshoot_no_messages(prod_name):
    """Troubleshoot production not processing messages."""
    print_section("Troubleshooting: No Messages Processing")
    
    print("Checking production state...")
    status, _, state = director.get_production_status()
    
    if state != 1:
        print("⚠️  Production is not running!")
        if ask_yes_no("Start the production?"):
            troubleshoot_wont_start(prod_name)
        return
    
    print("✓ Production is running")
    print()
    
    # Check for any messages
    messages = director.get_host_messages(prod_name, max_results=100)
    
    if not messages:
        print("No messages found in history.")
        print()
        print("COMMON CAUSES:")
        print("  1. Inbound adapter not configured")
        print("     → Check file path, IP address, port settings")
        print()
        print("  2. External system not sending data")
        print("     → Verify external system is active")
        print()
        print("  3. Production just started")
        print("     → Wait for incoming messages")
        print()
        print("  4. Message history was purged")
        print("     → Check if older messages exist in Portal")
    else:
        # Has messages but user says not processing
        latest = messages[0]
        print(f"Found {len(messages)} message(s)")
        print(f"Most recent: {latest.get('time_created')}")
        print()
        
        # Check for recent activity (within last minute)
        print("COMMON CAUSES:")
        print("  1. Message flow has stopped")
        print("     → Check if external system stopped sending")
        print()
        print("  2. Component disabled")
        print("     → Check component status in Portal")
        print()
        print("  3. Error in processing")
        print("     → Check for error messages")
        
        errors = [m for m in messages if 'ERROR' in m.get('status', '').upper()]
        if errors:
            print()
            print(f"⚠️  Found {len(errors)} error(s) in recent messages")
            if ask_yes_no("Show error details?"):
                for err in errors[:5]:
                    print(f"\n  {err.get('time_created')}")
                    print(f"    {err.get('source')} → {err.get('target')}")
                    print(f"    Status: {err.get('status')}")


def troubleshoot_errors(prod_name):
    """Troubleshoot production with errors."""
    print_section("Troubleshooting: Production Has Errors")
    
    print("Fetching recent error messages...")
    messages = director.get_host_messages(prod_name, max_results=100)
    errors = [m for m in messages if 'ERROR' in m.get('status', '').upper()]
    
    if not errors:
        print("✓ No errors found in recent messages")
        return
    
    print(f"\nFound {len(errors)} error(s) out of {len(messages)} total messages")
    print(f"Error rate: {len(errors)/len(messages)*100:.1f}%")
    print()
    
    # Group by component
    from collections import defaultdict
    by_component = defaultdict(list)
    
    for err in errors:
        component = err.get('source', 'Unknown')
        by_component[component].append(err)
    
    print("Errors by component:")
    for component, errs in by_component.items():
        print(f"  • {component}: {len(errs)} error(s)")
    
    print()
    print("RECOMMENDATIONS:")
    print()
    
    # Find most problematic component
    worst_component = max(by_component.keys(), key=lambda k: len(by_component[k]))
    worst_count = len(by_component[worst_component])
    
    print(f"Component with most errors: {worst_component} ({worst_count} errors)")
    print()
    print("Options:")
    print(f"  1. Disable {worst_component} temporarily to stop error flood")
    print("  2. Check adapter configuration for this component")
    print("  3. Review error messages in Management Portal")
    print()
    
    if ask_yes_no(f"Disable {worst_component} temporarily?"):
        status = director.enable_config_item(worst_component, enable=False, do_update=True)
        if status.is_ok():
            print(f"✓ Disabled {worst_component}")
            print("  Fix the component configuration, then re-enable it")
        else:
            print(f"❌ Failed to disable: {status.get_error_text()}")


def main():
    """Run interactive troubleshooter."""
    print_header("IRIS PRODUCTION INTERACTIVE TROUBLESHOOTER")
    
    print("This tool will help diagnose your production issue.")
    print()
    
    # Get production name
    prod_name = get_production_name()
    
    if not prod_name:
        print("\nCannot continue without a production name.")
        return
    
    print(f"\nWorking with production: {prod_name}")
    
    # Ask about the issue
    print_section("What issue are you experiencing?")
    print("1. Production won't start")
    print("2. Production is in TROUBLED/error state")
    print("3. Production not processing messages")
    print("4. Production has error messages")
    print("5. Other / not sure")
    
    while True:
        choice = input("\nSelect issue (1-5): ").strip()
        
        if choice == '1':
            troubleshoot_wont_start(prod_name)
            break
        elif choice == '2':
            troubleshoot_troubled(prod_name)
            break
        elif choice == '3':
            troubleshoot_no_messages(prod_name)
            break
        elif choice == '4':
            troubleshoot_errors(prod_name)
            break
        elif choice == '5':
            print("\nRun the comprehensive diagnostic:")
            print(f"  python diagnose_production.py --production {prod_name}")
            break
        else:
            print("Please enter a number between 1 and 5")
    
    print()
    print_header("TROUBLESHOOTING COMPLETE")
    print("For more tools, see:")
    print("  • diagnose_production.py - Full diagnostic scan")
    print("  • monitor_production.py - Continuous monitoring")
    print("  • PRODUCTION_MANAGEMENT_GUIDE.md - Complete documentation")
    print()


if __name__ == '__main__':
    main()
