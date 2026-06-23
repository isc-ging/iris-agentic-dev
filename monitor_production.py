#!/usr/bin/env python3
"""
Continuous IRIS Production Monitor

Monitors an IRIS production and alerts on:
- Production state changes (running → stopped/troubled)
- Error rate spikes
- Message flow停滞

Usage:
    python monitor_production.py --production MyApp.Productions.Main
    python monitor_production.py --production MyApp.Productions.Main --interval 30
"""

import sys
import time
import argparse
from datetime import datetime
from typing import Optional, Dict, List
from collections import deque

try:
    from intersystems_pyprod import director
except ImportError:
    print("ERROR: intersystems_pyprod not installed")
    print("Install with: pip install intersystems-pyprod")
    sys.exit(1)


class ProductionMonitor:
    """Continuous production monitoring with alerting."""
    
    STATE_RUNNING = 1
    STATE_STOPPED = 2
    STATE_SUSPENDED = 3
    STATE_TROUBLED = 4
    
    STATE_NAMES = {
        1: "RUNNING",
        2: "STOPPED",
        3: "SUSPENDED",
        4: "TROUBLED"
    }
    
    def __init__(self, production_name: str, check_interval: int = 30):
        self.production_name = production_name
        self.check_interval = check_interval
        self.last_state = None
        self.last_message_count = 0
        self.error_history = deque(maxlen=20)  # Track last 20 checks
        self.stall_threshold = 5  # Alert if no new messages after 5 checks
        self.stall_counter = 0
        
    def run_monitor(self):
        """Run continuous monitoring loop."""
        print("=" * 70)
        print("IRIS PRODUCTION CONTINUOUS MONITOR")
        print("=" * 70)
        print(f"Production: {self.production_name}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("Press Ctrl+C to stop")
        print("=" * 70)
        print()
        
        try:
            while True:
                self._check_production_health()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            self._print_summary()
    
    def _check_production_health(self):
        """Perform a single health check."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Check production state
        status, prod_name, state = director.get_production_status()
        
        if not status.is_ok():
            self._alert(timestamp, "ERROR", 
                       f"Failed to get status: {status.get_error_text()}")
            return
        
        # Check for state change
        if self.last_state is not None and state != self.last_state:
            old_state = self.STATE_NAMES.get(self.last_state, "UNKNOWN")
            new_state = self.STATE_NAMES.get(state, "UNKNOWN")
            self._alert(timestamp, "STATE_CHANGE", 
                       f"{old_state} → {new_state}")
        
        self.last_state = state
        
        # If not running, alert and return
        if state != self.STATE_RUNNING:
            state_name = self.STATE_NAMES.get(state, "UNKNOWN")
            self._alert(timestamp, "NOT_RUNNING", 
                       f"Production is {state_name}")
            return
        
        # Check message flow
        messages = director.get_host_messages(
            self.production_name,
            max_results=100
        )
        
        current_count = len(messages)
        new_messages = current_count - self.last_message_count
        
        # Check for stalled message flow
        if new_messages == 0:
            self.stall_counter += 1
            if self.stall_counter >= self.stall_threshold:
                self._alert(timestamp, "STALLED", 
                           f"No new messages for {self.stall_counter * self.check_interval}s")
        else:
            self.stall_counter = 0
        
        # Count errors
        error_count = sum(
            1 for m in messages 
            if m.get('status', '').upper() in ['ERROR', 'FAILED']
        )
        
        error_rate = (error_count / current_count * 100) if current_count > 0 else 0
        self.error_history.append(error_rate)
        
        # Alert on error spike
        if len(self.error_history) >= 5:
            avg_error_rate = sum(self.error_history) / len(self.error_history)
            if error_rate > avg_error_rate * 2 and error_rate > 10:
                self._alert(timestamp, "ERROR_SPIKE", 
                           f"Error rate: {error_rate:.1f}% (avg: {avg_error_rate:.1f}%)")
        
        # Normal status output
        rate = new_messages / self.check_interval
        print(f"[{timestamp}] ✓ RUNNING | "
              f"Messages: {current_count} (+{new_messages}, {rate:.1f}/s) | "
              f"Errors: {error_count} ({error_rate:.1f}%)")
        
        self.last_message_count = current_count
    
    def _alert(self, timestamp: str, alert_type: str, message: str):
        """Print an alert message."""
        alert_symbols = {
            "ERROR": "❌",
            "STATE_CHANGE": "⚠️",
            "NOT_RUNNING": "🛑",
            "STALLED": "⏸️",
            "ERROR_SPIKE": "🔥"
        }
        
        symbol = alert_symbols.get(alert_type, "⚠️")
        print(f"[{timestamp}] {symbol} {alert_type}: {message}")
    
    def _print_summary(self):
        """Print monitoring summary."""
        print()
        print("=" * 70)
        print("MONITORING SUMMARY")
        print("=" * 70)
        
        if self.error_history:
            avg_error_rate = sum(self.error_history) / len(self.error_history)
            max_error_rate = max(self.error_history)
            print(f"Average error rate: {avg_error_rate:.1f}%")
            print(f"Max error rate: {max_error_rate:.1f}%")
        
        final_state = self.STATE_NAMES.get(self.last_state, "UNKNOWN")
        print(f"Final state: {final_state}")
        print()


def auto_restart_monitor(production_name: str, check_interval: int = 30):
    """Monitor with automatic restart on failure."""
    
    STATE_RUNNING = 1
    STATE_STOPPED = 2
    STATE_TROUBLED = 4
    
    print("=" * 70)
    print("IRIS PRODUCTION AUTO-RESTART MONITOR")
    print("=" * 70)
    print(f"Production: {production_name}")
    print(f"Check interval: {check_interval} seconds")
    print(f"Auto-restart: ENABLED")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    try:
        while True:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Check status
            status, prod_name, state = director.get_production_status()
            
            if not status.is_ok():
                print(f"[{timestamp}] ❌ Status check failed: {status.get_error_text()}")
                time.sleep(check_interval)
                continue
            
            if state == STATE_RUNNING:
                # Get message stats
                messages = director.get_host_messages(production_name, max_results=50)
                error_count = sum(
                    1 for m in messages 
                    if m.get('status', '').upper() in ['ERROR', 'FAILED']
                )
                
                print(f"[{timestamp}] ✓ Running | "
                      f"Recent messages: {len(messages)} | "
                      f"Errors: {error_count}")
                
            elif state == STATE_STOPPED:
                print(f"[{timestamp}] 🛑 Production STOPPED - attempting restart...")
                
                status = director.start_production(production_name)
                if status.is_ok():
                    print(f"[{timestamp}] ✓ Production restarted")
                else:
                    print(f"[{timestamp}] ❌ Restart failed: {status.get_error_text()}")
                    
            elif state == STATE_TROUBLED:
                print(f"[{timestamp}] ⚠️  Production TROUBLED - attempting recovery...")
                
                # Stop and restart
                director.stop_production(timeout=10, force=False)
                time.sleep(2)
                
                status = director.start_production(production_name)
                if status.is_ok():
                    print(f"[{timestamp}] ✓ Production recovered")
                else:
                    print(f"[{timestamp}] ❌ Recovery failed: {status.get_error_text()}")
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor IRIS Interoperability production"
    )
    parser.add_argument(
        '--production',
        required=True,
        help='Production class name to monitor'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Check interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--auto-restart',
        action='store_true',
        help='Automatically restart production if it stops or fails'
    )
    
    args = parser.parse_args()
    
    if args.auto_restart:
        auto_restart_monitor(args.production, args.interval)
    else:
        monitor = ProductionMonitor(args.production, args.interval)
        monitor.run_monitor()


if __name__ == '__main__':
    main()
