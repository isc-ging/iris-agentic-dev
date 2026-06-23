#!/usr/bin/env python3
"""
IRIS Interoperability Production Recovery Script

Automated recovery actions for common production issues.

Requirements:
    pip install intersystems-pyprod intersystems-iris-driver

Usage:
    # Diagnose and suggest actions
    python recover_production.py --action diagnose

    # Start a stopped production
    python recover_production.py --action start --production "MyApp.Production"

    # Recover a troubled production
    python recover_production.py --action recover

    # Stop and restart production (last resort)
    python recover_production.py --action restart --production "MyApp.Production"

    # Hot-apply configuration changes
    python recover_production.py --action update

    # Enable a disabled component
    python recover_production.py --action enable-component --component "MyService"
"""

import argparse
import os
import sys
import time
from typing import Optional

try:
    from intersystems_pyprod import director
    import iris
except ImportError as e:
    print(f"ERROR: Missing required package: {e}")
    print("Install with: pip install intersystems-pyprod intersystems-iris-driver")
    sys.exit(1)


class ProductionRecovery:
    """Automated production recovery actions"""
    
    STATE_NAMES = {1: "RUNNING", 2: "STOPPED", 3: "SUSPENDED", 4: "TROUBLED"}
    
    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.conn: Optional[iris.IRISConnection] = None
    
    def connect(self):
        """Establish IRIS connection"""
        print(f"🔗 Connecting to {self.params['host']}:{self.params['port']}/{self.params['namespace']}...")
        try:
            self.conn = iris.connect(
                hostname=self.params['host'],
                port=int(self.params['port']),
                namespace=self.params['namespace'],
                username=self.params['username'],
                password=self.params['password']
            )
            print("✅ Connected\n")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)
    
    def get_status(self):
        """Get current production status"""
        status, prod_name, state = director.get_production_status()
        state_name = self.STATE_NAMES.get(state, "UNKNOWN")
        return status, prod_name, state, state_name
    
    def diagnose(self):
        """Quick diagnosis"""
        print("="*70)
        print("QUICK DIAGNOSIS")
        print("="*70 + "\n")
        
        status, prod_name, state, state_name = self.get_status()
        
        print(f"📊 Current State: {state_name}")
        print(f"📦 Production: {prod_name or '(none)'}\n")
        
        if state == 2:  # STOPPED
            print("❌ ISSUE: Production is stopped")
            print("💡 ACTION: Run with --action start --production <YourProductionName>")
            print(f"   Example: python {sys.argv[0]} --action start --production 'MyApp.Production'")
        
        elif state == 4:  # TROUBLED
            print("❌ ISSUE: Production is in error state")
            print("💡 ACTION: Run with --action recover")
            print(f"   Example: python {sys.argv[0]} --action recover")
        
        elif state == 3:  # SUSPENDED
            print("⚠️  ISSUE: Production is suspended")
            print("💡 ACTION: Check Management Portal for suspension reason, then manually resume")
        
        elif state == 1:  # RUNNING
            print("✅ Production is running")
            
            # Check if update needed
            needs_update = director.update_production_needs_update()
            if needs_update:
                print("\n⚠️  Configuration changes detected")
                print("💡 ACTION: Run with --action update to apply changes")
                print(f"   Example: python {sys.argv[0]} --action update")
            else:
                print("\n💚 No configuration updates needed")
                print("\nIf messages aren't processing, check:")
                print("   1. Individual component status (disabled adapters?)")
                print("   2. Queue backlogs (message viewer)")
                print("   3. Recent errors (logs)")
                print(f"\n   Run full diagnostics: python diagnose_production.py")
    
    def start_production(self, prod_name: str):
        """Start a stopped production"""
        print("="*70)
        print(f"STARTING PRODUCTION: {prod_name}")
        print("="*70 + "\n")
        
        status, current_prod, state, state_name = self.get_status()
        
        if state == 1:
            print(f"⚠️  Production '{current_prod}' is already running")
            return
        
        print(f"▶️  Starting {prod_name}...")
        try:
            result = director.start_production(prod_name)
            
            # Wait a moment for startup
            time.sleep(2)
            
            # Verify
            status, new_prod, new_state, new_state_name = self.get_status()
            
            if new_state == 1:
                print(f"✅ SUCCESS: Production started")
                print(f"   State: {new_state_name}")
                print(f"   Production: {new_prod}")
            else:
                print(f"⚠️  Production state: {new_state_name}")
                print("   Check Management Portal for startup errors")
        
        except Exception as e:
            print(f"❌ FAILED: {e}")
            sys.exit(1)
    
    def recover_production(self):
        """Recover a troubled production"""
        print("="*70)
        print("RECOVERING PRODUCTION")
        print("="*70 + "\n")
        
        status, prod_name, state, state_name = self.get_status()
        
        if state != 4:
            print(f"ℹ️  Production is {state_name}, not TROUBLED")
            print("   Recovery is only needed for TROUBLED productions")
            return
        
        print(f"🔧 Attempting to recover {prod_name}...")
        try:
            # Note: director.recover_production() may not exist in all versions
            # Fallback to ObjectScript call
            iris_obj = iris.createIRIS()
            result = iris_obj.classMethodValue("Ens.Director", "RecoverProduction")
            
            time.sleep(2)
            
            status, new_prod, new_state, new_state_name = self.get_status()
            
            if new_state == 1:
                print(f"✅ SUCCESS: Production recovered and running")
            else:
                print(f"⚠️  Current state: {new_state_name}")
                print("   Manual intervention may be required via Management Portal")
        
        except Exception as e:
            print(f"❌ FAILED: {e}")
            print("\nTry manual recovery:")
            print("   1. Open Management Portal")
            print("   2. Go to Interoperability > Configure > Production")
            print("   3. Click 'Recover' button")
            sys.exit(1)
    
    def update_production(self):
        """Hot-apply configuration changes"""
        print("="*70)
        print("UPDATING PRODUCTION CONFIGURATION")
        print("="*70 + "\n")
        
        status, prod_name, state, state_name = self.get_status()
        
        if state != 1:
            print(f"⚠️  Production is {state_name}, not RUNNING")
            print("   Update only works on running productions")
            return
        
        # Check if update needed
        needs_update = director.update_production_needs_update()
        
        if not needs_update:
            print("✅ No configuration changes detected - nothing to update")
            return
        
        print(f"🔄 Applying configuration changes to {prod_name}...")
        try:
            result = director.update_production()
            
            print("✅ SUCCESS: Configuration updated")
            print("   Changes applied with zero downtime")
            print("   No messages were lost")
        
        except Exception as e:
            print(f"❌ FAILED: {e}")
            sys.exit(1)
    
    def restart_production(self, prod_name: str):
        """Stop and restart production (LAST RESORT)"""
        print("="*70)
        print("⚠️  RESTARTING PRODUCTION (LAST RESORT)")
        print("="*70 + "\n")
        
        print("⚠️  WARNING: Restart will:")
        print("   - Drop in-flight messages")
        print("   - Cause temporary service interruption")
        print("   - Prefer 'update' over 'restart' when possible")
        
        response = input("\nAre you sure you want to restart? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Restart cancelled")
            return
        
        status, current_prod, state, state_name = self.get_status()
        
        # Stop if running
        if state == 1:
            print(f"\n⏹️  Stopping {current_prod}...")
            try:
                director.stop_production(timeout=30, force=False)
                print("✅ Stopped gracefully")
                time.sleep(2)
            except Exception as e:
                print(f"⚠️  Graceful stop failed: {e}")
                print("   Trying force stop...")
                try:
                    director.stop_production(timeout=5, force=True)
                    print("✅ Force stopped")
                    time.sleep(2)
                except Exception as e2:
                    print(f"❌ Force stop failed: {e2}")
                    sys.exit(1)
        
        # Start
        print(f"\n▶️  Starting {prod_name}...")
        try:
            director.start_production(prod_name)
            time.sleep(2)
            
            status, new_prod, new_state, new_state_name = self.get_status()
            
            if new_state == 1:
                print(f"✅ SUCCESS: Production restarted")
                print(f"   State: {new_state_name}")
                print(f"   Production: {new_prod}")
            else:
                print(f"⚠️  Production state: {new_state_name}")
        
        except Exception as e:
            print(f"❌ FAILED: {e}")
            sys.exit(1)
    
    def enable_component(self, component_name: str):
        """Enable a disabled component"""
        print("="*70)
        print(f"ENABLING COMPONENT: {component_name}")
        print("="*70 + "\n")
        
        status, prod_name, state, state_name = self.get_status()
        
        if state != 1:
            print(f"⚠️  Production is {state_name}, not RUNNING")
            print("   Component can only be enabled on running production")
            return
        
        print(f"✅ Enabling {component_name} and applying change...")
        try:
            result = director.enable_config_item(component_name, enable=True, do_update=True)
            print(f"✅ SUCCESS: {component_name} enabled")
            print("   Change applied immediately (no restart)")
        
        except Exception as e:
            print(f"❌ FAILED: {e}")
            print(f"   Component '{component_name}' may not exist")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Recover IRIS Interoperability Production")
    parser.add_argument("--action", required=True,
                       choices=["diagnose", "start", "recover", "update", "restart", "enable-component"],
                       help="Recovery action to perform")
    parser.add_argument("--production", help="Production class name (for start/restart)")
    parser.add_argument("--component", help="Component name (for enable-component)")
    parser.add_argument("--host", default=os.getenv("IRIS_HOST", "localhost"))
    parser.add_argument("--port", default=os.getenv("IRIS_PORT", "1972"))
    parser.add_argument("--namespace", default=os.getenv("IRIS_NAMESPACE", "USER"))
    parser.add_argument("--username", default=os.getenv("IRIS_USERNAME", "_SYSTEM"))
    parser.add_argument("--password", default=os.getenv("IRIS_PASSWORD", "SYS"))
    
    args = parser.parse_args()
    
    # Validate action-specific parameters
    if args.action in ["start", "restart"] and not args.production:
        parser.error(f"--production is required for action '{args.action}'")
    if args.action == "enable-component" and not args.component:
        parser.error("--component is required for action 'enable-component'")
    
    connection_params = {
        "host": args.host,
        "port": args.port,
        "namespace": args.namespace,
        "username": args.username,
        "password": args.password
    }
    
    recovery = ProductionRecovery(connection_params)
    recovery.connect()
    
    try:
        with recovery.conn:
            if args.action == "diagnose":
                recovery.diagnose()
            elif args.action == "start":
                recovery.start_production(args.production)
            elif args.action == "recover":
                recovery.recover_production()
            elif args.action == "update":
                recovery.update_production()
            elif args.action == "restart":
                recovery.restart_production(args.production)
            elif args.action == "enable-component":
                recovery.enable_component(args.component)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
