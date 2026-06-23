#!/usr/bin/env python3
"""
Interactive IRIS Production Troubleshooter

A simple interactive CLI for diagnosing production issues step-by-step.
"""

import sys
from production_diagnostics import ProductionDiagnostics


def print_menu():
    """Display the main menu."""
    print("\n" + "="*70)
    print("IRIS PRODUCTION TROUBLESHOOTER")
    print("="*70)
    print("\n1. 🔍 Check production status")
    print("2. 📊 Analyze queue depths")
    print("3. ❌ View recent errors")
    print("4. 🏥 Run full diagnostic")
    print("5. ▶️  Start production")
    print("6. ⏹️  Stop production")
    print("7. 🔄 Recover production")
    print("8. 🚪 Exit")
    print("\n" + "="*70)


def get_connection_info():
    """Get connection parameters from user."""
    print("\n📡 Connection Information")
    print("-" * 70)
    
    host = input("IRIS Host [localhost]: ").strip() or "localhost"
    port = input("IRIS Web Port [52773]: ").strip() or "52773"
    namespace = input("Namespace [USER]: ").strip() or "USER"
    username = input("Username [_SYSTEM]: ").strip() or "_SYSTEM"
    password = input("Password [SYS]: ").strip() or "SYS"
    
    try:
        port = int(port)
    except ValueError:
        print("⚠️  Invalid port, using default 52773")
        port = 52773
    
    return {
        "host": host,
        "port": port,
        "namespace": namespace,
        "username": username,
        "password": password
    }


def confirm_action(message):
    """Ask user to confirm an action."""
    response = input(f"\n{message} (yes/no): ").strip().lower()
    return response in ['yes', 'y']


def main():
    """Main interactive loop."""
    print("\n" + "="*70)
    print("🔧 IRIS INTEROPERABILITY PRODUCTION TROUBLESHOOTER")
    print("="*70)
    print("\nThis tool will help you diagnose and fix production issues.")
    
    # Get connection info
    conn_info = get_connection_info()
    
    print(f"\n✅ Connecting to {conn_info['host']}:{conn_info['port']} namespace {conn_info['namespace']}")
    
    try:
        diagnostics = ProductionDiagnostics(**conn_info)
    except Exception as e:
        print(f"\n❌ Failed to create diagnostics client: {e}")
        sys.exit(1)
    
    # Main menu loop
    while True:
        print_menu()
        choice = input("Select an option (1-8): ").strip()
        
        if choice == "1":
            # Check status
            print("\n🔍 Checking production status...")
            status = diagnostics.get_production_status()
            
            if status.get("state") == "STOPPED":
                if confirm_action("Production is stopped. Would you like to start it?"):
                    diagnostics.start_production()
            elif status.get("components", {}).get("faulted", 0) > 0:
                if confirm_action("Some components are faulted. Would you like to recover?"):
                    diagnostics.recover_production()
        
        elif choice == "2":
            # Check queues
            print("\n📊 Analyzing queue depths...")
            queues = diagnostics.get_queue_depths()
            
            if queues.get("queues"):
                high_queues = [q for q in queues["queues"] if q.get("depth", 0) > 100]
                if high_queues:
                    print("\n⚠️  High queue depths detected!")
                    if confirm_action("Would you like to see the full diagnostic?"):
                        diagnostics.run_full_diagnostic()
        
        elif choice == "3":
            # Check errors
            print("\n❌ Checking recent errors...")
            hours = input("How many hours to look back? [1]: ").strip() or "1"
            try:
                hours = int(hours)
            except ValueError:
                hours = 1
            
            errors = diagnostics.get_recent_errors(hours=hours)
            
            if len(errors) > 10:
                print(f"\n⚠️  High error rate: {len(errors)} errors in last {hours} hour(s)")
                if confirm_action("Would you like to see the full diagnostic?"):
                    diagnostics.run_full_diagnostic()
        
        elif choice == "4":
            # Full diagnostic
            print("\n🏥 Running full diagnostic...")
            diagnostics.run_full_diagnostic()
            
            input("\nPress Enter to continue...")
        
        elif choice == "5":
            # Start production
            if confirm_action("⚠️  This will start the production. Continue?"):
                prod_name = input("Production name (leave blank to auto-detect): ").strip() or None
                diagnostics.start_production(prod_name)
        
        elif choice == "6":
            # Stop production
            if confirm_action("⚠️  This will stop the production. Continue?"):
                force = confirm_action("Force stop (may lose messages)?")
                timeout = 30
                if not force:
                    timeout_input = input("Timeout in seconds [30]: ").strip()
                    try:
                        timeout = int(timeout_input) if timeout_input else 30
                    except ValueError:
                        timeout = 30
                
                diagnostics.stop_production(timeout=timeout, force=force)
        
        elif choice == "7":
            # Recover production
            if confirm_action("This will attempt to recover the production. Continue?"):
                diagnostics.recover_production()
                print("\nVerifying recovery...")
                diagnostics.get_production_status()
        
        elif choice == "8":
            # Exit
            print("\n👋 Goodbye!")
            sys.exit(0)
        
        else:
            print("\n❌ Invalid option. Please select 1-8.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
