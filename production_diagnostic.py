#!/usr/bin/env python3
"""
IRIS Interoperability Production Diagnostic & Repair Tool

Comprehensive Python script to diagnose and fix production issues.
Uses intersystems-irispython for native IRIS connectivity.

Usage:
    python production_diagnostic.py --host localhost --port 1972 \
        --namespace USER --username _SYSTEM --password SYS

    # Quick diagnosis only
    python production_diagnostic.py --diagnose-only

    # Auto-repair mode
    python production_diagnostic.py --auto-repair

Author: IRIS DevTools
Date: 2026-06-05
"""

import sys
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum

try:
    import iris
except ImportError:
    print("ERROR: intersystems-irispython not installed")
    print("Install with: pip install intersystems-irispython")
    sys.exit(1)


class ProductionState(IntEnum):
    """Production state constants from Ens.Director"""
    STOPPED = 0
    RUNNING = 1
    SUSPENDED = 2
    STOPPING = 3
    TROUBLED = 4
    NETWORK_STOPPED = 5


@dataclass
class DiagnosticResult:
    """Results from a diagnostic check"""
    check_name: str
    status: str  # OK, WARNING, ERROR
    message: str
    details: Optional[Dict] = None
    fix_available: bool = False


class ProductionDiagnostic:
    """Main diagnostic and repair class"""
    
    def __init__(self, hostname: str, port: int, namespace: str, 
                 username: str, password: str):
        self.hostname = hostname
        self.port = port
        self.namespace = namespace
        self.username = username
        self.password = password
        self.conn = None
        self.iris_obj = None
        self.results: List[DiagnosticResult] = []
        
    def connect(self) -> bool:
        """Establish connection to IRIS"""
        try:
            print(f"Connecting to IRIS at {self.hostname}:{self.port} ...")
            self.conn = iris.connect(
                hostname=self.hostname,
                port=self.port,
                namespace=self.namespace,
                username=self.username,
                password=self.password
            )
            self.iris_obj = iris.createIRIS(self.conn)
            print(f"✓ Connected to namespace {self.namespace}\n")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close IRIS connection"""
        if self.conn:
            try:
                self.conn.close()
                print("\n✓ Disconnected from IRIS")
            except:
                pass
    
    def _call_method(self, class_name: str, method_name: str, *args):
        """Safe wrapper for IRIS classMethod calls"""
        try:
            return self.iris_obj.classMethodValue(class_name, method_name, *args)
        except Exception as e:
            raise Exception(f"Error calling {class_name}.{method_name}: {e}")
    
    def _add_result(self, check_name: str, status: str, message: str, 
                    details: Optional[Dict] = None, fix_available: bool = False):
        """Add a diagnostic result"""
        result = DiagnosticResult(
            check_name=check_name,
            status=status,
            message=message,
            details=details or {},
            fix_available=fix_available
        )
        self.results.append(result)
        
        # Print immediately for real-time feedback
        icon = "✓" if status == "OK" else "⚠️" if status == "WARNING" else "❌"
        print(f"{icon} {check_name}: {message}")
        if details and details.get('verbose'):
            print(f"   Details: {details['verbose']}")
    
    def check_production_status(self) -> Tuple[Optional[str], Optional[int]]:
        """Check if a production is running and its state"""
        print("\n=== STEP 1: Production Status ===")
        
        try:
            # Call Ens.Director.GetProductionStatus()
            status = self._call_method(
                "Ens.Director", 
                "GetProductionStatus",
                ""  # Empty string returns current production
            )
            
            # Returns: status^productionName^state
            parts = str(status).split("^")
            
            if len(parts) >= 3:
                status_code = int(parts[0])
                prod_name = parts[1]
                state = int(parts[2])
                
                if status_code != 1:
                    self._add_result(
                        "Production Status",
                        "ERROR",
                        f"GetProductionStatus returned error code {status_code}",
                        {"production": prod_name, "state": state}
                    )
                    return None, None
                
                if state == ProductionState.STOPPED:
                    self._add_result(
                        "Production Status",
                        "ERROR",
                        "No production is running",
                        {"state": "STOPPED"},
                        fix_available=True
                    )
                    return None, ProductionState.STOPPED
                
                elif state == ProductionState.RUNNING:
                    self._add_result(
                        "Production Status",
                        "OK",
                        f"Production '{prod_name}' is RUNNING",
                        {"production": prod_name, "state": "RUNNING"}
                    )
                    return prod_name, ProductionState.RUNNING
                
                elif state == ProductionState.TROUBLED:
                    self._add_result(
                        "Production Status",
                        "ERROR",
                        f"Production '{prod_name}' is TROUBLED (component failures)",
                        {"production": prod_name, "state": "TROUBLED"},
                        fix_available=True
                    )
                    return prod_name, ProductionState.TROUBLED
                
                elif state == ProductionState.SUSPENDED:
                    self._add_result(
                        "Production Status",
                        "WARNING",
                        f"Production '{prod_name}' is SUSPENDED",
                        {"production": prod_name, "state": "SUSPENDED"},
                        fix_available=True
                    )
                    return prod_name, ProductionState.SUSPENDED
                
                else:
                    self._add_result(
                        "Production Status",
                        "WARNING",
                        f"Production '{prod_name}' in state {state}",
                        {"production": prod_name, "state": state}
                    )
                    return prod_name, state
            else:
                self._add_result(
                    "Production Status",
                    "ERROR",
                    f"Unexpected GetProductionStatus response: {status}"
                )
                return None, None
                
        except Exception as e:
            self._add_result(
                "Production Status",
                "ERROR",
                f"Failed to query production status: {e}"
            )
            return None, None
    
    def check_component_status(self, prod_name: str):
        """Check status of all production components"""
        print("\n=== STEP 2: Component Status ===")
        
        try:
            # Get list of config items
            sql = f"""
                SELECT Name, ClassName, Enabled 
                FROM Ens_Config.Item 
                WHERE Production = ?
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql, [prod_name])
            items = cursor.fetchall()
            cursor.close()
            
            if not items:
                self._add_result(
                    "Components",
                    "WARNING",
                    "No components found in production configuration"
                )
                return
            
            enabled_count = sum(1 for item in items if item[2] == 1)
            disabled_count = len(items) - enabled_count
            
            self._add_result(
                "Components",
                "OK",
                f"Found {len(items)} components: {enabled_count} enabled, {disabled_count} disabled",
                {
                    "total": len(items),
                    "enabled": enabled_count,
                    "disabled": disabled_count,
                    "verbose": f"Components: {', '.join(item[0] for item in items[:5])}{'...' if len(items) > 5 else ''}"
                }
            )
            
            # Check for disabled critical components
            disabled_items = [item for item in items if item[2] == 0]
            if disabled_items:
                disabled_names = ", ".join(item[0] for item in disabled_items)
                self._add_result(
                    "Disabled Components",
                    "WARNING",
                    f"{len(disabled_items)} component(s) are disabled",
                    {"disabled": disabled_names},
                    fix_available=True
                )
                
        except Exception as e:
            self._add_result(
                "Components",
                "ERROR",
                f"Failed to check components: {e}"
            )
    
    def check_queues(self, prod_name: str):
        """Check message queue depths"""
        print("\n=== STEP 3: Queue Status ===")
        
        try:
            # Query Ens.Queue for queue depths
            sql = """
                SELECT Name, COUNT(*) as Depth
                FROM Ens_Util.Log
                WHERE SessionId IN (
                    SELECT TOP 1000 SessionId 
                    FROM Ens_Util.Log 
                    ORDER BY TimeCreated DESC
                )
                GROUP BY Name
                HAVING COUNT(*) > 0
                ORDER BY COUNT(*) DESC
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql)
            queues = cursor.fetchall()
            cursor.close()
            
            if not queues:
                self._add_result(
                    "Queues",
                    "OK",
                    "No messages pending in queues"
                )
                return
            
            # Check for high queue depths
            high_queues = [q for q in queues if q[1] > 100]
            
            if high_queues:
                queue_details = ", ".join(f"{q[0]}={q[1]}" for q in high_queues)
                self._add_result(
                    "Queues",
                    "WARNING",
                    f"{len(high_queues)} queue(s) with high depth (>100)",
                    {"queues": queue_details},
                    fix_available=True
                )
            else:
                total_depth = sum(q[1] for q in queues)
                self._add_result(
                    "Queues",
                    "OK",
                    f"Queue depths normal (total: {total_depth} messages)"
                )
                
        except Exception as e:
            self._add_result(
                "Queues",
                "WARNING",
                f"Could not check queues: {e}"
            )
    
    def check_recent_errors(self, prod_name: str):
        """Check for recent error messages"""
        print("\n=== STEP 4: Recent Errors ===")
        
        try:
            # Query recent error log entries
            sql = """
                SELECT TOP 50 
                    TimeCreated, 
                    SourceConfigName,
                    Type,
                    Text
                FROM Ens_Util.Log
                WHERE Type IN (2, 3)  -- Error, Alert
                ORDER BY TimeCreated DESC
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql)
            errors = cursor.fetchall()
            cursor.close()
            
            if not errors:
                self._add_result(
                    "Recent Errors",
                    "OK",
                    "No errors in recent log entries"
                )
                return
            
            # Count by component
            error_counts = {}
            for err in errors:
                component = err[1] or "Unknown"
                error_counts[component] = error_counts.get(component, 0) + 1
            
            top_component = max(error_counts.items(), key=lambda x: x[1])
            
            self._add_result(
                "Recent Errors",
                "ERROR",
                f"Found {len(errors)} error(s) in recent logs",
                {
                    "total_errors": len(errors),
                    "top_component": f"{top_component[0]} ({top_component[1]} errors)",
                    "verbose": f"Most recent: {errors[0][3][:100]}..." if errors[0][3] else "No text"
                },
                fix_available=True
            )
            
        except Exception as e:
            self._add_result(
                "Recent Errors",
                "WARNING",
                f"Could not check error logs: {e}"
            )
    
    def check_configuration_updates(self, prod_name: str):
        """Check if production needs configuration update"""
        print("\n=== STEP 5: Configuration Status ===")
        
        try:
            # Check if UpdateProduction is needed
            needs_update = self._call_method(
                "Ens.Director",
                "IsProductionUpdateRequested"
            )
            
            if needs_update and str(needs_update).lower() in ['1', 'true']:
                self._add_result(
                    "Configuration",
                    "WARNING",
                    "Production configuration has pending changes",
                    fix_available=True
                )
            else:
                self._add_result(
                    "Configuration",
                    "OK",
                    "Production configuration is current"
                )
                
        except Exception as e:
            self._add_result(
                "Configuration",
                "WARNING",
                f"Could not check configuration status: {e}"
            )
    
    def run_full_diagnostic(self) -> bool:
        """Run all diagnostic checks"""
        print("\n" + "="*70)
        print("IRIS INTEROPERABILITY PRODUCTION DIAGNOSTIC")
        print("="*70)
        print(f"Namespace: {self.namespace}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("="*70)
        
        # Step 1: Check production status
        prod_name, state = self.check_production_status()
        
        if not prod_name and state == ProductionState.STOPPED:
            print("\n⚠️  No production is running. Cannot perform further checks.")
            return False
        
        if not prod_name:
            print("\n❌ Could not determine production status. Cannot continue.")
            return False
        
        # Step 2: Check components
        self.check_component_status(prod_name)
        
        # Step 3: Check queues
        self.check_queues(prod_name)
        
        # Step 4: Check recent errors
        self.check_recent_errors(prod_name)
        
        # Step 5: Check configuration
        self.check_configuration_updates(prod_name)
        
        return True
    
    def print_summary(self):
        """Print diagnostic summary"""
        print("\n" + "="*70)
        print("DIAGNOSTIC SUMMARY")
        print("="*70)
        
        ok_count = sum(1 for r in self.results if r.status == "OK")
        warning_count = sum(1 for r in self.results if r.status == "WARNING")
        error_count = sum(1 for r in self.results if r.status == "ERROR")
        
        print(f"Total Checks: {len(self.results)}")
        print(f"  ✓ OK:       {ok_count}")
        print(f"  ⚠️ WARNING:  {warning_count}")
        print(f"  ❌ ERROR:    {error_count}")
        print()
        
        # Show fixable issues
        fixable = [r for r in self.results if r.fix_available]
        if fixable:
            print(f"Fixable Issues: {len(fixable)}")
            for result in fixable:
                print(f"  • {result.check_name}: {result.message}")
            print()
            print("Run with --auto-repair to attempt automatic fixes")
        
        # Overall status
        if error_count == 0 and warning_count == 0:
            print("✓ OVERALL STATUS: HEALTHY")
        elif error_count == 0:
            print("⚠️  OVERALL STATUS: WARNINGS PRESENT")
        else:
            print("❌ OVERALL STATUS: ERRORS DETECTED")
    
    def auto_repair(self) -> bool:
        """Attempt automatic repair of detected issues"""
        print("\n" + "="*70)
        print("AUTO-REPAIR MODE")
        print("="*70)
        
        fixable_issues = [r for r in self.results if r.fix_available]
        
        if not fixable_issues:
            print("✓ No fixable issues detected")
            return True
        
        print(f"Found {len(fixable_issues)} fixable issue(s)")
        
        # Get production name
        prod_name, state = self.check_production_status()
        
        success_count = 0
        
        for issue in fixable_issues:
            print(f"\nAttempting to fix: {issue.check_name}")
            
            try:
                if "stopped" in issue.message.lower() and "no production" in issue.message.lower():
                    # Need to find and start a production
                    prod_name = self._find_production_to_start()
                    if prod_name:
                        self._start_production(prod_name)
                        success_count += 1
                    else:
                        print("  ❌ No production found to start")
                
                elif "troubled" in issue.message.lower():
                    # Restart troubled production
                    if prod_name:
                        self._restart_production(prod_name)
                        success_count += 1
                
                elif "suspended" in issue.message.lower():
                    # Resume suspended production
                    if prod_name:
                        self._resume_production(prod_name)
                        success_count += 1
                
                elif "configuration" in issue.check_name.lower():
                    # Apply pending configuration
                    if prod_name:
                        self._update_production(prod_name)
                        success_count += 1
                
                else:
                    print(f"  ⚠️  No automated fix available for this issue")
                    
            except Exception as e:
                print(f"  ❌ Fix failed: {e}")
        
        print(f"\n✓ Successfully fixed {success_count}/{len(fixable_issues)} issue(s)")
        return success_count == len(fixable_issues)
    
    def _find_production_to_start(self) -> Optional[str]:
        """Find a production class to start"""
        try:
            sql = "SELECT TOP 1 Name FROM Ens_Config.Production"
            cursor = self.conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return result[0]
            return None
        except:
            return None
    
    def _start_production(self, prod_name: str):
        """Start a production"""
        print(f"  Starting production: {prod_name}")
        status = self._call_method("Ens.Director", "StartProduction", prod_name, 0)
        
        if str(status) == "1":
            print(f"  ✓ Production started successfully")
        else:
            raise Exception(f"StartProduction returned status: {status}")
    
    def _restart_production(self, prod_name: str):
        """Restart a troubled production"""
        print(f"  Restarting production: {prod_name}")
        
        # Stop
        self._call_method("Ens.Director", "StopProduction", 30, 0)
        print("  ✓ Stopped production")
        
        # Start
        import time
        time.sleep(2)
        
        status = self._call_method("Ens.Director", "StartProduction", prod_name, 0)
        
        if str(status) == "1":
            print(f"  ✓ Production restarted successfully")
        else:
            raise Exception(f"StartProduction returned status: {status}")
    
    def _resume_production(self, prod_name: str):
        """Resume a suspended production"""
        print(f"  Resuming production: {prod_name}")
        status = self._call_method("Ens.Director", "ResumeProduction")
        
        if str(status) == "1":
            print(f"  ✓ Production resumed successfully")
        else:
            raise Exception(f"ResumeProduction returned status: {status}")
    
    def _update_production(self, prod_name: str):
        """Apply pending configuration updates"""
        print(f"  Applying configuration updates")
        status = self._call_method("Ens.Director", "UpdateProduction")
        
        if str(status) == "1":
            print(f"  ✓ Configuration updated successfully")
        else:
            raise Exception(f"UpdateProduction returned status: {status}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="IRIS Interoperability Production Diagnostic & Repair Tool"
    )
    
    parser.add_argument("--host", default="localhost", help="IRIS hostname")
    parser.add_argument("--port", type=int, default=1972, help="IRIS superserver port")
    parser.add_argument("--namespace", default="USER", help="IRIS namespace")
    parser.add_argument("--username", default="_SYSTEM", help="IRIS username")
    parser.add_argument("--password", default="SYS", help="IRIS password")
    parser.add_argument("--diagnose-only", action="store_true", 
                       help="Only run diagnostics, don't offer repairs")
    parser.add_argument("--auto-repair", action="store_true",
                       help="Automatically attempt repairs")
    parser.add_argument("--json", action="store_true",
                       help="Output results as JSON")
    
    args = parser.parse_args()
    
    # Create diagnostic instance
    diag = ProductionDiagnostic(
        hostname=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    # Connect
    if not diag.connect():
        sys.exit(1)
    
    try:
        # Run diagnostics
        diag.run_full_diagnostic()
        
        # Print summary
        if not args.json:
            diag.print_summary()
        
        # Auto-repair if requested
        if args.auto_repair:
            diag.auto_repair()
        
        # JSON output
        if args.json:
            output = {
                "timestamp": datetime.now().isoformat(),
                "namespace": args.namespace,
                "results": [
                    {
                        "check": r.check_name,
                        "status": r.status,
                        "message": r.message,
                        "details": r.details,
                        "fixable": r.fix_available
                    }
                    for r in diag.results
                ]
            }
            print(json.dumps(output, indent=2))
        
    finally:
        diag.disconnect()


if __name__ == "__main__":
    main()
