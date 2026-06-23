#!/usr/bin/env python3
"""
IRIS Interoperability Production - Common Fixes

Quick fix script for common production issues.
Usage:
    python fix_production.py --action start --production MyApp.Production
    python fix_production.py --action stop
    python fix_production.py --action recover
    python fix_production.py --action enable --component MyService
"""

import sys
import argparse
import time
import iris.dbapi as iris_dbapi


class ProductionFixer:
    """Apply common fixes to IRIS Interoperability productions"""
    
    def __init__(self, host, port, namespace, username, password):
        self.host = host
        self.port = port
        self.namespace = namespace
        self.username = username
        self.password = password
        self.conn = None
        
    def connect(self):
        """Establish connection to IRIS"""
        print(f"Connecting to IRIS at {self.host}:{self.port}/{self.namespace}...")
        try:
            self.conn = iris_dbapi.connect(
                hostname=self.host,
                port=self.port,
                namespace=self.namespace,
                username=self.username,
                password=self.password
            )
            print("✓ Connected\n")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def start_production(self, production_name):
        """Start a production"""
        print(f"Starting production: {production_name}")
        cur = self.conn.cursor()
        
        try:
            # Check if already running
            cur.execute("SELECT ##class(Ens.Director).IsProductionRunning()")
            if cur.fetchone()[0]:
                cur.execute("SELECT ##class(Ens.Director).GetActiveProductionName()")
                active = cur.fetchone()[0]
                print(f"⚠ Production already running: {active}")
                return False
            
            # Start the production
            query = f"SELECT ##class(Ens.Director).StartProduction('{production_name}')"
            cur.execute(query)
            result = cur.fetchone()[0]
            
            if result == 1:
                print("✓ Production started successfully")
                
                # Wait a moment and verify
                time.sleep(2)
                cur.execute("SELECT ##class(Ens.Director).IsProductionRunning()")
                if cur.fetchone()[0]:
                    print("✓ Confirmed running")
                    return True
                else:
                    print("✗ Production start reported success but not running")
                    return False
            else:
                print(f"✗ Failed to start production (code: {result})")
                return False
                
        except Exception as e:
            print(f"✗ Error starting production: {e}")
            return False
        finally:
            cur.close()
    
    def stop_production(self, timeout=30, force=False):
        """Stop the running production"""
        print(f"Stopping production (timeout={timeout}s, force={force})...")
        cur = self.conn.cursor()
        
        try:
            # Check if running
            cur.execute("SELECT ##class(Ens.Director).IsProductionRunning()")
            if not cur.fetchone()[0]:
                print("⚠ No production is running")
                return True
            
            # Get production name
            cur.execute("SELECT ##class(Ens.Director).GetActiveProductionName()")
            prod_name = cur.fetchone()[0]
            print(f"  Stopping: {prod_name}")
            
            # Stop with timeout
            query = f"SELECT ##class(Ens.Director).StopProduction({timeout}, {1 if force else 0})"
            cur.execute(query)
            result = cur.fetchone()[0]
            
            if result == 1:
                print("✓ Production stopped successfully")
                return True
            else:
                print(f"✗ Failed to stop production (code: {result})")
                if not force:
                    print("\nTry with --force flag if production is stuck")
                return False
                
        except Exception as e:
            print(f"✗ Error stopping production: {e}")
            return False
        finally:
            cur.close()
    
    def restart_production(self, production_name, timeout=30):
        """Restart production (stop + start)"""
        print(f"Restarting production: {production_name}\n")
        
        if not self.stop_production(timeout=timeout):
            print("\n✗ Stop failed, aborting restart")
            return False
        
        print("")
        time.sleep(2)
        
        return self.start_production(production_name)
    
    def recover_production(self):
        """Recover a stuck/faulted production"""
        print("Attempting production recovery...")
        cur = self.conn.cursor()
        
        try:
            query = "SELECT ##class(Ens.Director).RecoverProduction()"
            cur.execute(query)
            result = cur.fetchone()[0]
            
            if result == 1:
                print("✓ Production recovered")
                return True
            else:
                print(f"✗ Recovery failed (code: {result})")
                return False
                
        except Exception as e:
            print(f"✗ Error during recovery: {e}")
            return False
        finally:
            cur.close()
    
    def update_production(self):
        """Apply production configuration updates (hot reload)"""
        print("Applying production configuration updates...")
        cur = self.conn.cursor()
        
        try:
            # Check if update needed
            cur.execute("SELECT ##class(Ens.Director).IsProductionUpdateNeeded()")
            if not cur.fetchone()[0]:
                print("⚠ No update needed - configuration is current")
                return True
            
            # Apply update
            query = "SELECT ##class(Ens.Director).UpdateProduction()"
            cur.execute(query)
            result = cur.fetchone()[0]
            
            if result == 1:
                print("✓ Configuration updated successfully")
                return True
            else:
                print(f"✗ Update failed (code: {result})")
                return False
                
        except Exception as e:
            print(f"✗ Error updating production: {e}")
            return False
        finally:
            cur.close()
    
    def enable_component(self, component_name):
        """Enable a disabled production component"""
        print(f"Enabling component: {component_name}")
        cur = self.conn.cursor()
        
        try:
            query = f"SELECT ##class(Ens.Director).EnableConfigItem('{component_name}')"
            cur.execute(query)
            result = cur.fetchone()[0]
            
            if result == 1:
                print("✓ Component enabled")
                
                # Apply the change
                print("  Applying update...")
                return self.update_production()
            else:
                print(f"✗ Failed to enable component (code: {result})")
                return False
                
        except Exception as e:
            print(f"✗ Error enabling component: {e}")
            return False
        finally:
            cur.close()
    
    def disable_component(self, component_name):
        """Disable a production component"""
        print(f"Disabling component: {component_name}")
        cur = self.conn.cursor()
        
        try:
            query = f"SELECT ##class(Ens.Director).DisableConfigItem('{component_name}')"
            cur.execute(query)
            result = cur.fetchone()[0]
            
            if result == 1:
                print("✓ Component disabled")
                
                # Apply the change
                print("  Applying update...")
                return self.update_production()
            else:
                print(f"✗ Failed to disable component (code: {result})")
                return False
                
        except Exception as e:
            print(f"✗ Error disabling component: {e}")
            return False
        finally:
            cur.close()
    
    def purge_queues(self, component_name=None):
        """Purge message queues"""
        if component_name:
            print(f"Purging queues for component: {component_name}")
        else:
            print("Purging all production message queues")
        
        cur = self.conn.cursor()
        
        try:
            if component_name:
                query = """
                    DELETE FROM Ens.MessageHeader
                    WHERE Status IN ('Queued', 'Delivered')
                        AND TargetConfigName = ?
                """
                cur.execute(query, [component_name])
            else:
                query = """
                    DELETE FROM Ens.MessageHeader
                    WHERE Status IN ('Queued', 'Delivered')
                """
                cur.execute(query)
            
            self.conn.commit()
            print(f"✓ Queues purged")
            return True
            
        except Exception as e:
            print(f"✗ Error purging queues: {e}")
            self.conn.rollback()
            return False
        finally:
            cur.close()


def main():
    parser = argparse.ArgumentParser(
        description='Apply fixes to IRIS Interoperability productions'
    )
    parser.add_argument('--host', default='localhost', help='IRIS host')
    parser.add_argument('--port', type=int, default=1972, help='IRIS superserver port')
    parser.add_argument('--namespace', default='USER', help='IRIS namespace')
    parser.add_argument('--username', default='_SYSTEM', help='IRIS username')
    parser.add_argument('--password', default='SYS', help='IRIS password')
    
    parser.add_argument('--action', required=True,
                       choices=['start', 'stop', 'restart', 'recover', 'update',
                               'enable', 'disable', 'purge'],
                       help='Action to perform')
    
    parser.add_argument('--production', help='Production class name (for start/restart)')
    parser.add_argument('--component', help='Component name (for enable/disable/purge)')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout for stop (seconds)')
    parser.add_argument('--force', action='store_true', help='Force stop (drops in-flight messages)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.action in ['start', 'restart'] and not args.production:
        parser.error(f"--production required for action '{args.action}'")
    
    if args.action in ['enable', 'disable'] and not args.component:
        parser.error(f"--component required for action '{args.action}'")
    
    fixer = ProductionFixer(
        host=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    if not fixer.connect():
        sys.exit(1)
    
    try:
        success = False
        
        if args.action == 'start':
            success = fixer.start_production(args.production)
        elif args.action == 'stop':
            success = fixer.stop_production(timeout=args.timeout, force=args.force)
        elif args.action == 'restart':
            success = fixer.restart_production(args.production, timeout=args.timeout)
        elif args.action == 'recover':
            success = fixer.recover_production()
        elif args.action == 'update':
            success = fixer.update_production()
        elif args.action == 'enable':
            success = fixer.enable_component(args.component)
        elif args.action == 'disable':
            success = fixer.disable_component(args.component)
        elif args.action == 'purge':
            success = fixer.purge_queues(args.component)
        
        sys.exit(0 if success else 1)
        
    finally:
        if fixer.conn:
            fixer.conn.close()


if __name__ == '__main__':
    main()
