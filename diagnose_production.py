#!/usr/bin/env python3
"""
IRIS Interoperability Production Diagnostic & Remediation Tool

This script diagnoses and fixes stopped IRIS Interoperability productions
using Python and the IRIS DB-API.

Prerequisites:
    pip install intersystems-irispython

Usage:
    python diagnose_production.py --host localhost --port 1972 --namespace USER
    python diagnose_production.py --auto-fix  # Automatically restart if stopped
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

try:
    import iris.dbapi as iris_dbapi
except ImportError:
    print("ERROR: intersystems-irispython not installed")
    print("Install with: pip install intersystems-irispython")
    sys.exit(1)


class ProductionDiagnostics:
    """IRIS Interoperability Production diagnostic and remediation tool."""
    
    def __init__(self, hostname: str, port: int, namespace: str, 
                 username: str, password: str):
        """Initialize connection to IRIS."""
        self.hostname = hostname
        self.port = port
        self.namespace = namespace
        self.username = username
        self.password = password
        self.conn = None
        self.cursor = None
        
    def connect(self) -> bool:
        """Establish connection to IRIS."""
        try:
            self.conn = iris_dbapi.connect(
                hostname=self.hostname,
                port=self.port,
                namespace=self.namespace,
                username=self.username,
                password=self.password
            )
            self.cursor = self.conn.cursor()
            print(f"✓ Connected to IRIS at {self.hostname}:{self.port}/{self.namespace}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def close(self):
        """Close IRIS connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_production_status(self) -> Optional[Dict[str, Any]]:
        """Get current production status and details."""
        try:
            # Get production state
            self.cursor.execute("""
                SELECT Ens_Config.Production_EnumerateGetStatus(?)
            """, [1])
            result = self.cursor.fetchone()
            
            if not result or not result[0]:
                print("✗ No production found or production not configured")
                return None
            
            # Parse the status result
            status_data = result[0]
            
            # Get production name
            self.cursor.execute("""
                SELECT Ens_Config.Production_ProductionName()
            """)
            prod_name_result = self.cursor.fetchone()
            prod_name = prod_name_result[0] if prod_name_result else "Unknown"
            
            # Get running state
            self.cursor.execute("""
                SELECT Ens_Director.IsProductionRunning()
            """)
            is_running_result = self.cursor.fetchone()
            is_running = bool(is_running_result[0]) if is_running_result else False
            
            status = {
                "name": prod_name,
                "running": is_running,
                "status": "RUNNING" if is_running else "STOPPED"
            }
            
            return status
            
        except Exception as e:
            print(f"✗ Error getting production status: {e}")
            return None
    
    def get_component_status(self) -> List[Dict[str, Any]]:
        """Get status of all production components."""
        components = []
        try:
            # Query all production items (Services, Processes, Operations)
            self.cursor.execute("""
                SELECT ConfigName, ClassName, Enabled, Status
                FROM Ens_Config.Item
                ORDER BY ConfigName
            """)
            
            for row in self.cursor.fetchall():
                components.append({
                    "name": row[0],
                    "class": row[1],
                    "enabled": bool(row[2]),
                    "status": row[3] if row[3] else "Unknown"
                })
                
        except Exception as e:
            print(f"✗ Error getting component status: {e}")
        
        return components
    
    def get_queue_depths(self) -> Dict[str, int]:
        """Get message queue depths for each component."""
        queues = {}
        try:
            self.cursor.execute("""
                SELECT TargetConfigName, COUNT(*) as QueueDepth
                FROM Ens_MessageHeader
                WHERE Status = 'Queued'
                GROUP BY TargetConfigName
                ORDER BY COUNT(*) DESC
            """)
            
            for row in self.cursor.fetchall():
                queues[row[0]] = row[1]
                
        except Exception as e:
            print(f"⚠ Warning: Could not get queue depths: {e}")
        
        return queues
    
    def get_recent_errors(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent error log entries."""
        errors = []
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            self.cursor.execute("""
                SELECT TOP ? 
                    TimeLogged, ConfigName, Text, Type
                FROM Ens_Util.Log
                WHERE Type IN ('Error', 'Alert', 'Assert')
                    AND TimeLogged > ?
                ORDER BY TimeLogged DESC
            """, [limit, cutoff.strftime("%Y-%m-%d %H:%M:%S")])
            
            for row in self.cursor.fetchall():
                errors.append({
                    "time": row[0],
                    "component": row[1],
                    "message": row[2],
                    "type": row[3]
                })
                
        except Exception as e:
            print(f"⚠ Warning: Could not retrieve error logs: {e}")
        
        return errors
    
    def get_suspended_messages(self) -> List[Dict[str, Any]]:
        """Get suspended messages that are blocking processing."""
        suspended = []
        try:
            self.cursor.execute("""
                SELECT TOP 50
                    %ID, SessionId, TimeCreated, SourceConfigName, 
                    TargetConfigName, Status, MessageBodyClassName
                FROM Ens_MessageHeader
                WHERE Status IN ('Suspended', 'Error', 'Aborted')
                ORDER BY TimeCreated DESC
            """)
            
            for row in self.cursor.fetchall():
                suspended.append({
                    "id": row[0],
                    "session": row[1],
                    "time": row[2],
                    "source": row[3],
                    "target": row[4],
                    "status": row[5],
                    "type": row[6]
                })
                
        except Exception as e:
            print(f"⚠ Warning: Could not retrieve suspended messages: {e}")
        
        return suspended
    
    def start_production(self, production_name: Optional[str] = None) -> bool:
        """Start the production."""
        try:
            if not production_name:
                # Get the configured production name
                self.cursor.execute("""
                    SELECT Ens_Config.Production_ProductionName()
                """)
                result = self.cursor.fetchone()
                if not result or not result[0]:
                    print("✗ No production configured")
                    return False
                production_name = result[0]
            
            print(f"Starting production: {production_name}")
            
            # Start the production using Ens.Director
            self.cursor.execute("""
                SELECT Ens_Director.StartProduction(?)
            """, [production_name])
            
            result = self.cursor.fetchone()
            status = result[0] if result else None
            
            if status and status.startswith("1"):  # Success code
                print(f"✓ Production started successfully")
                return True
            else:
                print(f"✗ Failed to start production: {status}")
                return False
                
        except Exception as e:
            print(f"✗ Error starting production: {e}")
            return False
    
    def stop_production(self, timeout: int = 30, force: bool = False) -> bool:
        """Stop the production gracefully or forcefully."""
        try:
            print(f"Stopping production (timeout={timeout}s, force={force})")
            
            # Stop using Ens.Director
            self.cursor.execute("""
                SELECT Ens_Director.StopProduction(?, ?)
            """, [timeout, 1 if force else 0])
            
            result = self.cursor.fetchone()
            status = result[0] if result else None
            
            if status and status.startswith("1"):
                print(f"✓ Production stopped successfully")
                return True
            else:
                print(f"✗ Failed to stop production: {status}")
                return False
                
        except Exception as e:
            print(f"✗ Error stopping production: {e}")
            return False
    
    def restart_production(self) -> bool:
        """Restart the production (stop then start)."""
        print("Restarting production...")
        
        # Stop with 30 second timeout
        if not self.stop_production(timeout=30, force=False):
            print("⚠ Graceful stop failed, trying force stop...")
            if not self.stop_production(timeout=10, force=True):
                return False
        
        # Wait a moment for cleanup
        import time
        time.sleep(2)
        
        # Start
        return self.start_production()
    
    def recover_production(self) -> bool:
        """Recover a faulted/stuck production."""
        try:
            print("Attempting production recovery...")
            
            self.cursor.execute("""
                SELECT Ens_Director.RecoverProduction()
            """)
            
            result = self.cursor.fetchone()
            status = result[0] if result else None
            
            if status and status.startswith("1"):
                print(f"✓ Production recovered")
                return True
            else:
                print(f"✗ Recovery failed: {status}")
                return False
                
        except Exception as e:
            print(f"✗ Error recovering production: {e}")
            return False
    
    def print_diagnostic_report(self):
        """Print comprehensive diagnostic report."""
        print("\n" + "="*70)
        print("IRIS INTEROPERABILITY PRODUCTION DIAGNOSTIC REPORT")
        print("="*70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: {self.hostname}:{self.port}/{self.namespace}")
        print()
        
        # 1. Production Status
        print("─" * 70)
        print("1. PRODUCTION STATUS")
        print("─" * 70)
        status = self.get_production_status()
        if status:
            print(f"Name: {status['name']}")
            print(f"State: {status['status']}")
            print(f"Running: {'Yes' if status['running'] else 'No'}")
            
            if not status['running']:
                print("\n⚠ WARNING: Production is STOPPED")
                print("   This is likely why messages are not processing.")
        else:
            print("✗ Could not determine production status")
        print()
        
        # 2. Component Status
        print("─" * 70)
        print("2. COMPONENT STATUS")
        print("─" * 70)
        components = self.get_component_status()
        if components:
            running = sum(1 for c in components if c['enabled'])
            disabled = len(components) - running
            print(f"Total components: {len(components)}")
            print(f"Enabled: {running}, Disabled: {disabled}")
            print()
            
            for comp in components[:10]:  # Show first 10
                enabled_str = "✓" if comp['enabled'] else "✗"
                print(f"  {enabled_str} {comp['name']:<40} [{comp['status']}]")
            
            if len(components) > 10:
                print(f"  ... and {len(components) - 10} more")
        else:
            print("No components found")
        print()
        
        # 3. Queue Depths
        print("─" * 70)
        print("3. MESSAGE QUEUES")
        print("─" * 70)
        queues = self.get_queue_depths()
        if queues:
            print(f"Components with queued messages: {len(queues)}")
            print()
            for comp, depth in list(queues.items())[:10]:
                print(f"  {comp:<40} {depth:>6} messages")
            
            total_queued = sum(queues.values())
            if total_queued > 0:
                print(f"\n⚠ Total queued messages: {total_queued}")
        else:
            print("✓ No messages in queue")
        print()
        
        # 4. Suspended Messages
        print("─" * 70)
        print("4. SUSPENDED/ERROR MESSAGES")
        print("─" * 70)
        suspended = self.get_suspended_messages()
        if suspended:
            print(f"⚠ Found {len(suspended)} suspended/error messages")
            print()
            for msg in suspended[:5]:
                print(f"  Session {msg['session']}: {msg['source']} → {msg['target']}")
                print(f"    Status: {msg['status']}, Time: {msg['time']}")
                print()
        else:
            print("✓ No suspended messages")
        print()
        
        # 5. Recent Errors
        print("─" * 70)
        print("5. RECENT ERRORS (last 24 hours)")
        print("─" * 70)
        errors = self.get_recent_errors()
        if errors:
            print(f"⚠ Found {len(errors)} errors")
            print()
            for err in errors[:5]:
                print(f"  [{err['type']}] {err['time']}")
                print(f"    Component: {err['component']}")
                print(f"    Message: {err['message'][:100]}")
                print()
        else:
            print("✓ No recent errors")
        print()
        
        # 6. Recommendations
        print("─" * 70)
        print("6. RECOMMENDATIONS")
        print("─" * 70)
        
        recommendations = []
        
        if status and not status['running']:
            recommendations.append(
                "▶ Production is stopped. Run with --auto-fix to restart automatically, "
                "or call start_production() manually."
            )
        
        if queues and sum(queues.values()) > 100:
            recommendations.append(
                f"▶ High queue depth ({sum(queues.values())} messages). Check for slow "
                "or failing operations."
            )
        
        if suspended and len(suspended) > 10:
            recommendations.append(
                f"▶ {len(suspended)} suspended messages found. Review and resume or "
                "discard using IRIS Management Portal."
            )
        
        if errors and len(errors) > 20:
            recommendations.append(
                f"▶ {len(errors)} errors in 24h. Check component configuration and "
                "connectivity."
            )
        
        if not recommendations:
            recommendations.append("✓ No immediate issues detected.")
        
        for rec in recommendations:
            print(f"{rec}")
        
        print()
        print("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="IRIS Interoperability Production Diagnostic Tool"
    )
    parser.add_argument("--host", default="localhost", 
                       help="IRIS hostname (default: localhost)")
    parser.add_argument("--port", type=int, default=1972,
                       help="IRIS SuperServer port (default: 1972)")
    parser.add_argument("--namespace", default="USER",
                       help="IRIS namespace (default: USER)")
    parser.add_argument("--username", default="_SYSTEM",
                       help="IRIS username (default: _SYSTEM)")
    parser.add_argument("--password", default="SYS",
                       help="IRIS password (default: SYS)")
    parser.add_argument("--auto-fix", action="store_true",
                       help="Automatically restart production if stopped")
    
    args = parser.parse_args()
    
    # Create diagnostics instance
    diag = ProductionDiagnostics(
        hostname=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    # Connect
    if not diag.connect():
        return 1
    
    try:
        # Run diagnostics
        diag.print_diagnostic_report()
        
        # Auto-fix if requested
        if args.auto_fix:
            status = diag.get_production_status()
            if status and not status['running']:
                print("\n" + "="*70)
                print("AUTO-FIX: Attempting to restart production...")
                print("="*70)
                
                if diag.restart_production():
                    print("\n✓ Production restarted successfully")
                    print("  Wait a few moments and check message processing.")
                else:
                    print("\n✗ Failed to restart production")
                    print("  Manual intervention required via Management Portal.")
                    return 1
        
        return 0
        
    finally:
        diag.close()


if __name__ == "__main__":
    sys.exit(main())
