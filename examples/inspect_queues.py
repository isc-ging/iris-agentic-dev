#!/usr/bin/env python3
"""
IRIS Interoperability Message Queue Inspector

This script inspects message queues, shows stuck messages, and helps trace message flow.

Usage:
    # Show all queued messages
    python inspect_queues.py --host localhost --port 52773 --namespace USER

    # Show messages for a specific component
    python inspect_queues.py --component BusinessProcess.OrderHandler

    # Show message details including body
    python inspect_queues.py --details

    # Trace a specific message session
    python inspect_queues.py --session 12345

Requirements:
    pip install requests
"""

import argparse
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import sys


class IRISMessageInspector:
    """Inspect IRIS Interoperability message queues and trace message flow."""
    
    def __init__(self, host: str, port: int, namespace: str, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.namespace = namespace
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def _query_sql(self, query: str) -> Dict:
        """Execute SQL query via Atelier REST API."""
        url = f"{self.base_url}/api/atelier/v1/{self.namespace}/action/query"
        
        payload = {
            "query": query,
            "parameters": []
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_queue_summary(self, component: Optional[str] = None) -> List[Dict]:
        """Get summary of message queues."""
        print("🔍 Inspecting message queues...\n")
        
        where_clause = ""
        if component:
            where_clause = f"AND TargetConfigName = '{component}'"
        
        query = f"""
            SELECT 
                TargetConfigName,
                COUNT(*) AS QueueDepth,
                MIN(TimeCreated) AS OldestMessage,
                MAX(TimeCreated) AS NewestMessage,
                AVG(DATEDIFF(second, TimeCreated, GETDATE())) AS AvgAgeSeconds
            FROM Ens.MessageHeader
            WHERE Status = 'Queued'
            {where_clause}
            GROUP BY TargetConfigName
            ORDER BY QueueDepth DESC
        """
        
        result = self._query_sql(query)
        
        if result["status"] == "error":
            print(f"❌ Error querying queues: {result.get('message')}")
            return []
        
        queues = []
        for row in result["data"].get("result", {}).get("content", []):
            queues.append({
                "component": row.get("TargetConfigName"),
                "depth": row.get("QueueDepth", 0),
                "oldest": row.get("OldestMessage"),
                "newest": row.get("NewestMessage"),
                "avg_age": row.get("AvgAgeSeconds", 0)
            })
        
        return queues
    
    def get_queued_messages(self, component: Optional[str] = None, 
                           limit: int = 50, include_body: bool = False) -> List[Dict]:
        """Get detailed list of queued messages."""
        where_clause = ""
        if component:
            where_clause = f"AND TargetConfigName = '{component}'"
        
        query = f"""
            SELECT TOP {limit}
                ID,
                SessionId,
                SourceConfigName,
                TargetConfigName,
                TimeCreated,
                TimeProcessed,
                Status,
                MessageBodyClassName,
                MessageBodyId,
                Priority,
                ReturnQueueName
            FROM Ens.MessageHeader
            WHERE Status = 'Queued'
            {where_clause}
            ORDER BY Priority DESC, TimeCreated ASC
        """
        
        result = self._query_sql(query)
        
        if result["status"] == "error":
            print(f"❌ Error querying messages: {result.get('message')}")
            return []
        
        messages = []
        for row in result["data"].get("result", {}).get("content", []):
            msg = {
                "id": row.get("ID"),
                "session": row.get("SessionId"),
                "source": row.get("SourceConfigName"),
                "target": row.get("TargetConfigName"),
                "created": row.get("TimeCreated"),
                "status": row.get("Status"),
                "body_class": row.get("MessageBodyClassName"),
                "body_id": row.get("MessageBodyId"),
                "priority": row.get("Priority", 0)
            }
            
            # Optionally fetch message body
            if include_body and msg["body_id"]:
                body = self.get_message_body(msg["body_class"], msg["body_id"])
                msg["body"] = body
            
            messages.append(msg)
        
        return messages
    
    def get_message_body(self, body_class: str, body_id: str) -> Optional[str]:
        """Get message body content."""
        # This is a simplified version - actual implementation depends on body class
        query = f"""
            SELECT TOP 1 *
            FROM {body_class}
            WHERE ID = {body_id}
        """
        
        result = self._query_sql(query)
        
        if result["status"] == "error":
            return f"Error fetching body: {result.get('message')}"
        
        content = result["data"].get("result", {}).get("content", [])
        if content:
            return json.dumps(content[0], indent=2)
        
        return None
    
    def trace_session(self, session_id: str) -> List[Dict]:
        """Trace all messages in a session."""
        print(f"🔍 Tracing session {session_id}...\n")
        
        query = f"""
            SELECT 
                ID,
                TimeCreated,
                TimeProcessed,
                SourceConfigName,
                TargetConfigName,
                Status,
                MessageBodyClassName,
                ReturnCode,
                ErrorStatus,
                Description
            FROM Ens.MessageHeader
            WHERE SessionId = {session_id}
            ORDER BY TimeCreated ASC
        """
        
        result = self._query_sql(query)
        
        if result["status"] == "error":
            print(f"❌ Error tracing session: {result.get('message')}")
            return []
        
        messages = []
        for row in result["data"].get("result", {}).get("content", []):
            messages.append({
                "id": row.get("ID"),
                "created": row.get("TimeCreated"),
                "processed": row.get("TimeProcessed"),
                "source": row.get("SourceConfigName"),
                "target": row.get("TargetConfigName"),
                "status": row.get("Status"),
                "body_class": row.get("MessageBodyClassName"),
                "return_code": row.get("ReturnCode"),
                "error_status": row.get("ErrorStatus"),
                "description": row.get("Description")
            })
        
        return messages
    
    def get_stuck_messages(self, hours: int = 1) -> List[Dict]:
        """Find messages stuck in queue for more than specified hours."""
        query = f"""
            SELECT TOP 50
                ID,
                SessionId,
                SourceConfigName,
                TargetConfigName,
                TimeCreated,
                Status,
                MessageBodyClassName,
                DATEDIFF(minute, TimeCreated, GETDATE()) AS AgeMinutes
            FROM Ens.MessageHeader
            WHERE Status = 'Queued'
            AND DATEDIFF(hour, TimeCreated, GETDATE()) >= {hours}
            ORDER BY TimeCreated ASC
        """
        
        result = self._query_sql(query)
        
        if result["status"] == "error":
            print(f"❌ Error finding stuck messages: {result.get('message')}")
            return []
        
        messages = []
        for row in result["data"].get("result", {}).get("content", []):
            messages.append({
                "id": row.get("ID"),
                "session": row.get("SessionId"),
                "source": row.get("SourceConfigName"),
                "target": row.get("TargetConfigName"),
                "created": row.get("TimeCreated"),
                "status": row.get("Status"),
                "body_class": row.get("MessageBodyClassName"),
                "age_minutes": row.get("AgeMinutes", 0)
            })
        
        return messages
    
    def display_queue_summary(self, queues: List[Dict]):
        """Display queue summary in a readable format."""
        if not queues:
            print("✅ No messages in queues\n")
            return
        
        total = sum(q["depth"] for q in queues)
        print(f"📊 Queue Summary: {total} total messages across {len(queues)} component(s)\n")
        
        print(f"{'Component':<40} {'Depth':>8} {'Oldest Message':>20} {'Avg Age (min)':>15}")
        print("-" * 90)
        
        for q in queues:
            avg_age_min = int(q["avg_age"] / 60) if q["avg_age"] else 0
            print(f"{q['component']:<40} {q['depth']:>8} {q['oldest']:>20} {avg_age_min:>15}")
        
        print()
    
    def display_messages(self, messages: List[Dict], include_body: bool = False):
        """Display message details."""
        if not messages:
            print("✅ No messages found\n")
            return
        
        print(f"📬 Found {len(messages)} message(s)\n")
        
        for i, msg in enumerate(messages, 1):
            print(f"Message {i}:")
            print(f"  ID: {msg['id']}")
            print(f"  Session: {msg['session']}")
            print(f"  Source: {msg['source']}")
            print(f"  Target: {msg['target']}")
            print(f"  Created: {msg['created']}")
            print(f"  Status: {msg['status']}")
            print(f"  Priority: {msg.get('priority', 'N/A')}")
            print(f"  Body Class: {msg['body_class']}")
            
            if include_body and msg.get('body'):
                print(f"  Body:")
                print("  " + "\n  ".join(msg['body'].split('\n')))
            
            print()
    
    def display_session_trace(self, messages: List[Dict]):
        """Display session trace in a readable format."""
        if not messages:
            print("❌ No messages found for this session\n")
            return
        
        print(f"📊 Session Trace: {len(messages)} message(s)\n")
        
        for i, msg in enumerate(messages, 1):
            status_icon = "✅" if msg['status'] == 'Completed' else "⏳" if msg['status'] == 'Queued' else "❌"
            
            print(f"{i}. {status_icon} [{msg['created']}]")
            print(f"   {msg['source']} → {msg['target']}")
            print(f"   Status: {msg['status']}")
            
            if msg.get('error_status'):
                print(f"   ❌ Error: {msg['error_status']}")
            
            if msg.get('description'):
                print(f"   Description: {msg['description']}")
            
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect IRIS Interoperability message queues"
    )
    parser.add_argument("--host", default="localhost", help="IRIS host (default: localhost)")
    parser.add_argument("--port", type=int, default=52773, help="IRIS web port (default: 52773)")
    parser.add_argument("--namespace", default="USER", help="IRIS namespace (default: USER)")
    parser.add_argument("--username", default="_SYSTEM", help="IRIS username (default: _SYSTEM)")
    parser.add_argument("--password", default="SYS", help="IRIS password (default: SYS)")
    parser.add_argument("--component", help="Filter by component name")
    parser.add_argument("--session", help="Trace a specific session ID")
    parser.add_argument("--details", action="store_true", help="Include message body details")
    parser.add_argument("--stuck", type=int, metavar="HOURS", help="Show messages stuck for N hours")
    parser.add_argument("--limit", type=int, default=50, help="Max messages to retrieve (default: 50)")
    
    args = parser.parse_args()
    
    # Create inspector instance
    inspector = IRISMessageInspector(
        host=args.host,
        port=args.port,
        namespace=args.namespace,
        username=args.username,
        password=args.password
    )
    
    print("\n" + "="*60)
    print("🔍 IRIS Message Queue Inspector")
    print("="*60 + "\n")
    
    # Session trace mode
    if args.session:
        messages = inspector.trace_session(args.session)
        inspector.display_session_trace(messages)
        sys.exit(0)
    
    # Stuck messages mode
    if args.stuck is not None:
        messages = inspector.get_stuck_messages(hours=args.stuck)
        print(f"⚠️  Messages stuck in queue for {args.stuck}+ hours:\n")
        inspector.display_messages(messages)
        sys.exit(0)
    
    # Default mode: show queue summary and messages
    queues = inspector.get_queue_summary(component=args.component)
    inspector.display_queue_summary(queues)
    
    if queues:
        messages = inspector.get_queued_messages(
            component=args.component,
            limit=args.limit,
            include_body=args.details
        )
        inspector.display_messages(messages, include_body=args.details)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
