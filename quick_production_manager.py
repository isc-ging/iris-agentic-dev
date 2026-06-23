#!/usr/bin/env python3
"""
Quick Production Manager - Simple Interactive Tool

Common production management tasks in an easy-to-use menu.

Usage:
    python quick_production_manager.py
"""

import sys

try:
    import iris
except ImportError:
    print("ERROR: intersystems-irispython not installed")
    print("Install with: pip install intersystems-irispython")
    sys.exit(1)


class QuickProductionManager:
    """Simple interactive production manager"""
    
    def __init__(self):
        self.conn = None
        self.iris_obj = None
        self.namespace = None
        
    def connect(self):
        """Connect to IRIS with user input"""
        print("="*60)
        print("IRIS CONNECTION")
        print("="*60)
        
        hostname = input("Hostname [localhost]: ").strip() or "localhost"
        port = input("Port [1972]: ").strip() or "1972"
        namespace = input("Namespace [USER]: ").strip() or "USER"
        username = input("Username [_SYSTEM]: ").strip() or "_SYSTEM"
        password = input("Password [SYS]: ").strip() or "SYS"
        
        try:
            self.conn = iris.connect(
                hostname=hostname,
                port=int(port),
                namespace=namespace,
                username=username,
                password=password
            )
            self.iris_obj = iris.createIRIS(self.conn)
            self.namespace = namespace
            
            print(f"\n✓ Connected to {namespace} on {hostname}:{port}\n")
            return True
            
        except Exception as e:
            print(f"\n❌ Connection failed: {e}\n")
            return False
    
    def get_production_status(self):
        """Get current production status"""
        try:
            status = self.iris_obj.classMethodValue(
                "Ens.Director", 
                "GetProductionStatus", 
                ""
            )
            
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
                
                state_name = states.get(state, f"UNKNOWN({state})")
                
                return prod_name, state, state_name
            
            return None, None, None
            
        except Exception as e:
            print(f"Error checking status: {e}")
            return None, None, None
    
    def list_productions(self):
        """List all available productions"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT Name FROM Ens_Config.Production")
            prods = cursor.fetchall()
            cursor.close()
            return [p[0] for p in prods]
        except:
            return []
    
    def show_status(self):
        """Show production status"""
        print("\n" + "="*60)
        print("PRODUCTION STATUS")
        print("="*60)
        
        prod_name, state, state_name = self.get_production_status()
        
        if not prod_name and state == 0:
            print("Status: No production running")
            
            # List available productions
            prods = self.list_productions()
            if prods:
                print(f"\nAvailable productions ({len(prods)}):")
                for p in prods:
                    print(f"  • {p}")
        else:
            print(f"Production: {prod_name}")
            print(f"Status: {state_name}")
            
            if state == 4:
                print("\n⚠️  TROUBLED state indicates component failures")
                print("   Check error logs or restart production")
        
        print()
    
    def start_production(self):
        """Start a production"""
        print("\n" + "="*60)
        print("START PRODUCTION")
        print("="*60)
        
        # Check if one is already running
        prod_name, state, state_name = self.get_production_status()
        
        if state == 1:
            print(f"⚠️  Production '{prod_name}' is already RUNNING")
            return
        
        # List available productions
        prods = self.list_productions()
        
        if not prods:
            print("No productions found in this namespace")
            return
        
        print("\nAvailable productions:")
        for idx, p in enumerate(prods, 1):
            print(f"  {idx}. {p}")
        
        choice = input(f"\nSelect production (1-{len(prods)}) or [Enter] to cancel: ").strip()
        
        if not choice:
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(prods):
                prod_to_start = prods[idx]
                
                print(f"\nStarting {prod_to_start}...")
                
                result = self.iris_obj.classMethodValue(
                    "Ens.Director",
                    "StartProduction",
                    prod_to_start,
                    0
                )
                
                if str(result) == "1":
                    print(f"✓ Production started successfully")
                    
                    # Verify
                    _, new_state, new_state_name = self.get_production_status()
                    if new_state == 1:
                        print(f"✓ Status: {new_state_name}")
                    elif new_state == 4:
                        print(f"⚠️  Status: {new_state_name} (component failures)")
                else:
                    print(f"❌ Failed to start (code: {result})")
            else:
                print("Invalid selection")
                
        except ValueError:
            print("Invalid input")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def stop_production(self):
        """Stop the running production"""
        print("\n" + "="*60)
        print("STOP PRODUCTION")
        print("="*60)
        
        prod_name, state, state_name = self.get_production_status()
        
        if state == 0:
            print("No production is running")
            return
        
        print(f"Current production: {prod_name}")
        print(f"Status: {state_name}")
        
        confirm = input("\nStop this production? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("Cancelled")
            return
        
        try:
            print("\nStopping production (graceful, 30s timeout)...")
            
            self.iris_obj.classMethodValue(
                "Ens.Director",
                "StopProduction",
                30,  # timeout
                0    # force=0 (graceful)
            )
            
            print("✓ Production stopped")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def restart_production(self):
        """Restart the running production"""
        print("\n" + "="*60)
        print("RESTART PRODUCTION")
        print("="*60)
        
        prod_name, state, state_name = self.get_production_status()
        
        if state == 0:
            print("No production is running")
            return
        
        print(f"Current production: {prod_name}")
        print(f"Status: {state_name}")
        
        confirm = input("\nRestart this production? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("Cancelled")
            return
        
        try:
            print("\n1/2 Stopping production...")
            self.iris_obj.classMethodValue("Ens.Director", "StopProduction", 30, 0)
            print("  ✓ Stopped")
            
            import time
            time.sleep(2)
            
            print("2/2 Starting production...")
            result = self.iris_obj.classMethodValue(
                "Ens.Director",
                "StartProduction",
                prod_name,
                0
            )
            
            if str(result) == "1":
                print("  ✓ Started")
                
                # Check final state
                _, new_state, new_state_name = self.get_production_status()
                print(f"\n✓ Production restarted: {new_state_name}")
                
                if new_state == 4:
                    print("\n⚠️  Production is TROUBLED - check component errors")
            else:
                print(f"  ❌ Failed to start (code: {result})")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def check_errors(self):
        """Show recent errors"""
        print("\n" + "="*60)
        print("RECENT ERRORS")
        print("="*60)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT TOP 20
                    TimeCreated,
                    SourceConfigName,
                    Text
                FROM Ens_Util.Log
                WHERE Type IN (2, 3)
                ORDER BY TimeCreated DESC
            """)
            
            errors = cursor.fetchall()
            cursor.close()
            
            if not errors:
                print("✓ No recent errors found")
                return
            
            print(f"\nFound {len(errors)} error(s):\n")
            
            for idx, err in enumerate(errors[:10], 1):
                time_created = err[0]
                source = err[1] or "Unknown"
                text = err[2] or "No message"
                
                print(f"{idx}. [{time_created}] {source}")
                print(f"   {text[:100]}{'...' if len(text) > 100 else ''}")
                print()
            
            if len(errors) > 10:
                print(f"... and {len(errors) - 10} more")
                
        except Exception as e:
            print(f"❌ Error querying logs: {e}")
    
    def check_queues(self):
        """Show queue depths"""
        print("\n" + "="*60)
        print("QUEUE DEPTHS")
        print("="*60)
        
        try:
            cursor = self.conn.cursor()
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
                HAVING COUNT(*) > 5
                ORDER BY COUNT(*) DESC
            """)
            
            queues = cursor.fetchall()
            cursor.close()
            
            if not queues:
                print("✓ No significant queues")
                return
            
            print()
            for q in queues:
                component = q[0]
                depth = q[1]
                status = "⚠️  HIGH" if depth > 100 else "OK"
                print(f"  {component}: {depth} messages [{status}]")
            
        except Exception as e:
            print(f"❌ Error querying queues: {e}")
    
    def run_menu(self):
        """Main menu loop"""
        while True:
            print("\n" + "="*60)
            print("QUICK PRODUCTION MANAGER")
            print("="*60)
            print("1. Show production status")
            print("2. Start production")
            print("3. Stop production")
            print("4. Restart production")
            print("5. Check recent errors")
            print("6. Check queue depths")
            print("7. Reconnect to different namespace")
            print("0. Exit")
            print()
            
            choice = input("Select option: ").strip()
            
            if choice == '1':
                self.show_status()
            elif choice == '2':
                self.start_production()
            elif choice == '3':
                self.stop_production()
            elif choice == '4':
                self.restart_production()
            elif choice == '5':
                self.check_errors()
            elif choice == '6':
                self.check_queues()
            elif choice == '7':
                self.disconnect()
                if not self.connect():
                    break
            elif choice == '0':
                print("\nExiting...")
                break
            else:
                print("Invalid option")
            
            input("\nPress Enter to continue...")
    
    def disconnect(self):
        """Close connection"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass


def main():
    """Entry point"""
    print("\n" + "="*60)
    print("IRIS INTEROPERABILITY - QUICK PRODUCTION MANAGER")
    print("="*60)
    print()
    
    manager = QuickProductionManager()
    
    if manager.connect():
        try:
            manager.run_menu()
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            manager.disconnect()
    else:
        print("Failed to connect. Exiting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
