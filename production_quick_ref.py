#!/usr/bin/env python3
"""
Quick Production Management Examples

Copy and paste these into your Python scripts or interactive sessions.
"""

from intersystems_pyprod import director

# ============================================================================
# BASIC CHECKS
# ============================================================================

def check_status():
    """Check if production is running."""
    status, prod_name, state = director.get_production_status()
    
    states = {1: "RUNNING", 2: "STOPPED", 3: "SUSPENDED", 4: "TROUBLED"}
    print(f"Production: {prod_name or '(none)'}")
    print(f"State: {states.get(state, 'UNKNOWN')}")


def list_productions():
    """List all productions in namespace."""
    status, names, details = director.list_all_productions()
    
    print(f"Found {len(names)} production(s):")
    for name in names:
        last_start = details.get(name, {}).get('last_start_time', 'never')
        print(f"  • {name}")
        print(f"    Last started: {last_start}")


# ============================================================================
# START / STOP / RESTART
# ============================================================================

def start_production(prod_name):
    """Start a production."""
    status = director.start_production(prod_name)
    
    if status.is_ok():
        print(f"✓ Started: {prod_name}")
    else:
        print(f"❌ Failed: {status.get_error_text()}")


def stop_production_gracefully():
    """Stop production gracefully (wait for in-flight messages)."""
    status = director.stop_production(timeout=30, force=False)
    
    if status.is_ok():
        print("✓ Production stopped")
    else:
        print(f"⚠️  {status.get_error_text()}")


def restart_production(prod_name):
    """Restart a production (stop then start)."""
    print("Stopping production...")
    director.stop_production(timeout=30, force=False)
    
    import time
    time.sleep(2)
    
    print(f"Starting {prod_name}...")
    status = director.start_production(prod_name)
    
    if status.is_ok():
        print("✓ Production restarted")
    else:
        print(f"❌ Start failed: {status.get_error_text()}")


# ============================================================================
# CONFIGURATION UPDATES
# ============================================================================

def update_production_config():
    """Apply config changes without downtime."""
    status, needs_update = director.production_needs_update()
    
    if needs_update:
        print("Applying configuration changes...")
        status = director.update_production()
        
        if status.is_ok():
            print("✓ Configuration updated (no downtime)")
        else:
            print(f"❌ Update failed: {status.get_error_text()}")
    else:
        print("No configuration changes to apply")


def disable_component(component_name):
    """Disable a production component."""
    status = director.enable_config_item(component_name, enable=False, do_update=True)
    
    if status.is_ok():
        print(f"✓ Disabled: {component_name}")
    else:
        print(f"❌ Failed: {status.get_error_text()}")


def enable_component(component_name):
    """Enable a production component."""
    status = director.enable_config_item(component_name, enable=True, do_update=True)
    
    if status.is_ok():
        print(f"✓ Enabled: {component_name}")
    else:
        print(f"❌ Failed: {status.get_error_text()}")


# ============================================================================
# MESSAGE INSPECTION
# ============================================================================

def show_recent_messages(component_name, max_count=20):
    """Show recent messages for a component."""
    messages = director.get_host_messages(component_name, max_results=max_count)
    
    print(f"Recent messages for {component_name}:")
    print(f"Total: {len(messages)}")
    print()
    
    for msg in messages[:10]:  # Show first 10
        print(f"  {msg.get('time_created')}")
        print(f"    {msg.get('source')} → {msg.get('target')}")
        print(f"    Status: {msg.get('status')}")
        print(f"    Type: {msg.get('body_class')}")
        print()


def show_error_messages(component_name, max_count=50):
    """Show only error messages."""
    messages = director.get_host_messages(component_name, max_results=max_count)
    
    errors = [
        m for m in messages 
        if m.get('status', '').upper() in ['ERROR', 'FAILED']
    ]
    
    print(f"Errors for {component_name}:")
    print(f"Total errors: {len(errors)} out of {len(messages)} messages")
    print()
    
    for err in errors:
        print(f"  {err.get('time_created')}")
        print(f"    {err.get('source')} → {err.get('target')}")
        print(f"    Session: {err.get('session_id')}")
        print(f"    Type: {err.get('body_class')}")
        print()


def get_message_stats(production_name):
    """Get message statistics."""
    messages = director.get_host_messages(production_name, max_results=100)
    
    total = len(messages)
    if total == 0:
        print("No messages found")
        return
    
    success = sum(
        1 for m in messages 
        if m.get('status', '').upper() in ['OK', 'SUCCESS', 'COMPLETED']
    )
    errors = sum(
        1 for m in messages 
        if m.get('status', '').upper() in ['ERROR', 'FAILED']
    )
    
    print(f"Message Statistics (last {total} messages):")
    print(f"  ✓ Successful: {success} ({success/total*100:.1f}%)")
    print(f"  ❌ Errors: {errors} ({errors/total*100:.1f}%)")
    
    if messages:
        latest = messages[0]
        print(f"  Most recent: {latest.get('time_created')}")


# ============================================================================
# DIAGNOSTIC WORKFLOWS
# ============================================================================

def quick_health_check(production_name):
    """Quick health check for a production."""
    print("=" * 60)
    print("PRODUCTION HEALTH CHECK")
    print("=" * 60)
    print()
    
    # Check state
    status, prod_name, state = director.get_production_status()
    states = {1: "RUNNING", 2: "STOPPED", 3: "SUSPENDED", 4: "TROUBLED"}
    state_name = states.get(state, "UNKNOWN")
    
    print(f"Production: {prod_name or '(none)'}")
    print(f"State: {state_name}")
    print()
    
    if state != 1:  # Not running
        print(f"⚠️  Production is not running ({state_name})")
        return
    
    # Check messages
    messages = director.get_host_messages(production_name, max_results=100)
    
    if not messages:
        print("⚠️  No messages found (may be newly started)")
        return
    
    # Calculate stats
    total = len(messages)
    errors = sum(
        1 for m in messages 
        if m.get('status', '').upper() in ['ERROR', 'FAILED']
    )
    
    print(f"Recent messages: {total}")
    print(f"  Success: {total - errors}")
    print(f"  Errors: {errors}")
    
    if errors > 0:
        print()
        print("Recent errors:")
        error_messages = [
            m for m in messages 
            if m.get('status', '').upper() in ['ERROR', 'FAILED']
        ]
        for err in error_messages[:3]:
            print(f"  • {err.get('source')} at {err.get('time_created')}")
    
    print()
    print("✓ Health check complete")


def recover_troubled_production(production_name):
    """Attempt to recover a troubled production."""
    print(f"Recovering troubled production: {production_name}")
    print()
    
    # Check current state
    status, prod_name, state = director.get_production_status()
    
    if state != 4:  # Not troubled
        print(f"Production is not troubled (state: {state})")
        return
    
    print("Attempting recovery (stop + start)...")
    
    # Stop
    status = director.stop_production(timeout=30, force=False)
    if not status.is_ok():
        print(f"⚠️  Stop: {status.get_error_text()}")
    else:
        print("✓ Stopped")
    
    # Wait
    import time
    time.sleep(2)
    
    # Start
    status = director.start_production(production_name)
    if not status.is_ok():
        print(f"❌ Start failed: {status.get_error_text()}")
        return
    
    print("✓ Started")
    
    # Verify
    status, prod_name, state = director.get_production_status()
    if state == 1:
        print("✓ Production recovered successfully")
    else:
        print(f"⚠️  Production in state: {state}")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == '__main__':
    print("IRIS Production Management - Quick Reference")
    print()
    print("Copy the functions you need into your script or run them directly.")
    print()
    print("Examples:")
    print()
    print("  # Check production status")
    print("  check_status()")
    print()
    print("  # List all productions")
    print("  list_productions()")
    print()
    print("  # Start a production")
    print('  start_production("MyApp.Productions.Main")')
    print()
    print("  # Quick health check")
    print('  quick_health_check("MyApp.Productions.Main")')
    print()
    print("  # View recent messages")
    print('  show_recent_messages("MyBusinessService", 20)')
    print()
    print("  # Show only errors")
    print('  show_error_messages("MyBusinessService", 50)')
    print()
    print("  # Get message statistics")
    print('  get_message_stats("MyApp.Productions.Main")')
    print()
    print("  # Disable a problematic component")
    print('  disable_component("BrokenService")')
    print()
    print("  # Apply config changes")
    print("  update_production_config()")
    print()
    print("  # Recover a troubled production")
    print('  recover_troubled_production("MyApp.Productions.Main")')
