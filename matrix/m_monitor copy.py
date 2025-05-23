#!/usr/bin/env python3
import asyncio
import os
import json
import argparse
import time
import httpx
from datetime import datetime, timezone
import logging
import sys
import re
from typing import Dict, List, Optional
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Matrix server configuration
SYNAPSE_URL = os.getenv("SYNAPSE_URL", "https://vox-populi.dev")
WHATSAPP_BOT_MXID = os.getenv("WHATSAPP_BOT_MXID", "@whatsappbot:vox-populi.dev")
TELEGRAM_BOT_MXID = os.getenv("TELEGRAM_BOT_MXID", "@telegrambot:vox-populi.dev")
SIGNAL_BOT_MXID = os.getenv("SIGNAL_BOT_MXID", "@signalbot:vox-populi.dev")
MONGODB_URI = os.getenv("MONGODB_URI")


class BridgeConfig:
    """Configuration for different bridge types"""

    def __init__(self, name: str, bot_mxid: str, room_indicators: List[str], message_patterns: Optional[Dict] = None, owner: str = "Unknown"):
        self.name = name
        self.bot_mxid = bot_mxid
        self.room_indicators = room_indicators  # Strings that indicate this type of bridge room
        self.message_patterns = message_patterns or {}
        self.owner = owner  # Add owner attribute

class mongo_connector():
    def __init__(self):
        self.db_connection_string = MONGODB_URI
        self.client = MongoClient(self.db_connection_string)
        self.db = None

    def get_client(self):
        return self.client
    
    def get_db(self, db_name, collection_name):
        return self.client[db_name][collection_name]

class MultiPlatformMessageMonitor:
    def __init__(self, username, password, server_url=None, platforms=None):
        self.username = username
        self.password = password
        self.access_token = None
        self.user_id = None
        self.next_batch = None
        self.bridge_rooms = {}  # Dict of room_id -> bridge_info mappings
        self.synapse_url = server_url if server_url else SYNAPSE_URL

        # Configure supported platforms
        if platforms is None:
            platforms = ['whatsapp', 'signal']

        self.bridge_configs = {}
        if 'whatsapp' in platforms:
            self.bridge_configs['whatsapp'] = BridgeConfig(
                name="WhatsApp",
                bot_mxid=WHATSAPP_BOT_MXID,
                room_indicators=["WhatsApp", "WA:"],
                message_patterns={
                    'sender_format': r"^(.*?):\s+(.*?)$"  # "Sender: Message" format
                },
                owner="WhatsApp Owner"  # Set owner for WhatsApp
            )

        if 'signal' in platforms:
            self.bridge_configs['signal'] = BridgeConfig(
                name="Signal",
                bot_mxid=SIGNAL_BOT_MXID,
                room_indicators=["Signal", "SG:", "Signal Chat"],
                message_patterns={
                    'sender_format': r"^(.*?):\s+(.*?)$"  # Similar format for Signal
                },
                owner="Signal Owner"  # Set owner for Signal
            )

        if 'telegram' in platforms:
            self.bridge_configs['telegram'] = BridgeConfig(
                name="Telegram",
                bot_mxid=TELEGRAM_BOT_MXID,
                room_indicators=["Telegram", "TG:", "Telegram Chat"],
                message_patterns={
                    'sender_format': r"^(.*?):\s+(.*?)$"  # Similar format for Telegram
                },
                owner="Telegram Owner"  # Set owner for Telegram
            )

        # Print configuration
        print(f"Using Matrix server: {self.synapse_url}")
        print(f"Username: {self.username}")
        print("Configured bridges:")
        for platform, config in self.bridge_configs.items():
            print(f"  - {config.name}: {config.bot_mxid}")

    async def login(self):
        """Log in to Matrix and obtain an access token"""
        login_url = f"{self.synapse_url}/_matrix/client/v3/login"

        # Extract domain from server URL
        domain = self.synapse_url.replace("https://", "").replace("http://", "").split(':')[0]
        print(f"Using domain: {domain}")

        payload = {
            "type": "m.login.password",
            "identifier": {
                "type": "m.id.user",
                "user": self.username
            },
            "password": self.password
        }

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                print(f"Sending login request to {login_url}")
                response = await client.post(login_url, json=payload)

                print(f"Login response status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    self.user_id = data.get("user_id")
                    print(f"Successfully logged in as {self.user_id}")
                    return True
                else:
                    print(f"Login failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
            except Exception as e:
                print(f"Exception during login: {str(e)}")
                return False

    async def find_bridge_rooms(self):
        """Find all bridge rooms for configured platforms"""
        if not self.access_token:
            print("Not logged in. Cannot find bridge rooms.")
            return False

        # Get joined rooms
        joined_rooms_url = f"{self.synapse_url}/_matrix/client/v3/joined_rooms"

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                print(f"Getting joined rooms from {joined_rooms_url}")

                response = await client.get(
                    joined_rooms_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )

                print(f"Joined rooms response: {response.status_code}")

                if response.status_code != 200:
                    print(f"Failed to get joined rooms: {response.text}")
                    return False

                rooms = response.json().get("joined_rooms", [])
                print(f"Found {len(rooms)} joined rooms. Filtering for bridge rooms...")

                # Get state for each room to identify bridge rooms
                for room_id in rooms:
                    print(f"Checking room: {room_id}")
                    await self.check_if_bridge_room(room_id, client)

                print(f"Identified {len(self.bridge_rooms)} bridge rooms")

                if not self.bridge_rooms:
                    print("No bridge rooms found. Make sure your messaging platforms are connected in Matrix.")
                    return False

                # Print found rooms grouped by platform
                platforms = {}
                for room_id, room_data in self.bridge_rooms.items():
                    platform = room_data['platform']
                    if platform not in platforms:
                        platforms[platform] = []
                    platforms[platform].append(room_data)

                for platform, rooms in platforms.items():
                    print(f"\n{platform.upper()} Rooms ({len(rooms)}):")
                    for room_data in rooms:
                        print(f"  - {room_data['name']} ({room_data['room_id']})")

                return True

            except Exception as e:
                print(f"Error finding bridge rooms: {str(e)}")
                return False

    async def check_if_bridge_room(self, room_id, client):
        """Check if a room is a bridge room and identify which platform"""
        state_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/state"

        try:
            response = await client.get(
                state_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )

            if response.status_code != 200:
                print(f"Failed to get state for room {room_id}: {response.status_code}")
                return

            state_events = response.json()
            room_name = None
            detected_platform = None

            # Get the room name first
            for event in state_events:
                if event.get("type") == "m.room.name":
                    room_name = event.get("content", {}).get("name")
                    break

            # Check each configured platform
            for platform, config in self.bridge_configs.items():
                is_bridge_room = False

                # Check if the platform's bot is in the room
                for event in state_events:
                    if (event.get("type") == "m.room.member" and
                            event.get("state_key") == config.bot_mxid and
                            event.get("content", {}).get("membership") == "join"):
                        is_bridge_room = True
                        detected_platform = platform
                        print(f"Found {config.name} bot in room {room_id}")
                        break

                # Also check room name for platform indicators
                if room_name:
                    for indicator in config.room_indicators:
                        if indicator in room_name:
                            is_bridge_room = True
                            detected_platform = platform
                            print(f"Room name '{room_name}' indicates a {config.name} room")
                            break

                if is_bridge_room:
                    break

            if detected_platform:
                self.bridge_rooms[room_id] = {
                    "room_id": room_id,
                    "name": room_name or f"Unnamed {self.bridge_configs[detected_platform].name} Chat",
                    "platform": detected_platform,
                    "bot_mxid": self.bridge_configs[detected_platform].bot_mxid,
                    "config": self.bridge_configs[detected_platform]
                }
                print(f"Added {detected_platform} room: {room_name or 'Unnamed'} ({room_id})")

        except Exception as e:
            print(f"Error checking room {room_id}: {str(e)}")

    async def monitor_messages(self):
        """Monitor for all messages in bridge rooms"""
        if not self.access_token or not self.bridge_rooms:
            print("Not logged in or no bridge rooms found. Cannot monitor messages.")
            return False

        # Initial sync to get the current state
        sync_url = f"{self.synapse_url}/_matrix/client/v3/sync"

        print(f"Starting sync with {sync_url}")

        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            try:
                # Get initial sync token
                print("Starting initial sync...")
                response = await client.get(
                    sync_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params={"timeout": 10000}  # 10 seconds timeout for initial sync
                )

                if response.status_code != 200:
                    print(f"Initial sync failed: {response.status_code} - {response.text}")
                    return False

                self.next_batch = response.json().get("next_batch")
                print(f"Initial sync complete. Token: {self.next_batch}")

                # Print a welcome message
                print("\n" + "=" * 80)
                print(f"Multi-Platform Message Monitor - Connected as {self.user_id}")

                # Show statistics by platform
                platform_counts = {}
                for room_data in self.bridge_rooms.values():
                    platform = room_data['platform']
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1

                for platform, count in platform_counts.items():
                    platform_name = self.bridge_configs[platform].name
                    print(f"Monitoring {count} {platform_name} bridge rooms")

                print("Showing ALL messages in your bridge rooms")
                print("=" * 80 + "\n")
                print("Waiting for new messages...\n")

                # Main monitoring loop
                while True:
                    try:
                        # Long polling for new events
                        response = await client.get(
                            sync_url,
                            headers={"Authorization": f"Bearer {self.access_token}"},
                            params={
                                "since": self.next_batch,
                                "timeout": 30000,  # 30 second timeout
                                "filter": json.dumps({
                                    "room": {
                                        "timeline": {"limit": 50},
                                        "include_leave": False
                                    }
                                })
                            }
                        )

                        if response.status_code != 200:
                            print(f"Sync failed: {response.status_code} - {response.text}")
                            await asyncio.sleep(5)
                            continue

                        data = response.json()
                        self.next_batch = data.get("next_batch")

                        # Process new room events
                        await self.process_sync_events(data)

                    except Exception as e:
                        print(f"Error in monitoring loop: {str(e)}")
                        await asyncio.sleep(5)

            except Exception as e:
                print(f"Fatal error in monitoring: {str(e)}")
                return False

    async def process_sync_events(self, sync_data):
        """Process events from sync response and print all messages"""
        rooms = sync_data.get("rooms", {}).get("join", {})

        for room_id, room_data in rooms.items():
            # Skip rooms that aren't bridge rooms
            if room_id not in self.bridge_rooms:
                continue

            timeline = room_data.get("timeline", {})
            events = timeline.get("events", [])

            for event in events:
                if event.get("type") == "m.room.message":
                    await self.insert_msg_to_mongo(room_id, event)

    async def print_message(self, room_id, event):
        """Format and print a message to the terminal"""
        content = event.get("content", {})
        msgtype = content.get("msgtype")
        sender = event.get("sender", "Unknown")

        # Skip non-message events or redactions
        if not msgtype or msgtype == "m.room.redaction":
            return

        # Get room info
        room_info = self.bridge_rooms[room_id]
        room_name = room_info["name"]
        platform = room_info["platform"].upper()
        bridge_config = room_info["config"]

        # Format timestamp
        ts = event.get("origin_server_ts", 0) / 1000  # Convert ms to seconds
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

        # Extract username from sender ID
        username = sender.split(":")[0][1:]  # Remove @ and domain

        # Process different message types
        if msgtype in ["m.text", "m.notice"]:
            body = content.get("body", "")

            # Special handling for bridge bot messages to extract the actual sender
            if sender == bridge_config.bot_mxid:
                # Try to detect the bridge message format "Sender: Message"
                sender_pattern = bridge_config.message_patterns.get('sender_format')
                if sender_pattern:
                    match = re.match(sender_pattern, body)
                    if match:
                        bridge_sender, message = match.groups()
                        print(f"[{time_str}] [{platform}] [{room_name}] {bridge_sender}: {message}")
                    else:
                        # If it doesn't match the expected format, display as is
                        print(f"[{time_str}] [{platform}] [{room_name}] {bridge_config.name} Bot: {body}")
                else:
                    # No pattern defined, show as bot message
                    print(f"[{time_str}] [{platform}] [{room_name}] {bridge_config.name} Bot: {body}")
            else:
                # Regular Matrix message
                print(f"[{time_str}] [{platform}] [{room_name}] {username}: {body}")

        elif msgtype == "m.image":
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(
                f"[{time_str}] [{platform}] [{room_name}] {display_name} sent an image: {content.get('body', 'Unnamed image')}")

        elif msgtype == "m.audio":
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(
                f"[{time_str}] [{platform}] [{room_name}] {display_name} sent audio: {content.get('body', 'Audio message')}")

        elif msgtype == "m.video":
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(
                f"[{time_str}] [{platform}] [{room_name}] {display_name} sent a video: {content.get('body', 'Video message')}")

        elif msgtype == "m.file":
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(f"[{time_str}] [{platform}] [{room_name}] {display_name} sent a file: {content.get('body', 'File')}")

        elif msgtype == "m.location":
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(
                f"[{time_str}] [{platform}] [{room_name}] {display_name} shared a location: {content.get('body', 'Shared a location')}")

        elif msgtype == "m.emote":
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(f"[{time_str}] [{platform}] [{room_name}] * {display_name} {content.get('body', '')}")

        else:
            # Generic fallback for other message types
            display_name = f"{username}" if sender != bridge_config.bot_mxid else f"{bridge_config.name} User"
            print(
                f"[{time_str}] [{platform}] [{room_name}] {display_name} sent a {msgtype} message: {content.get('body', 'Message')}")

    async def insert_msg_to_mongo(self, room_id, event):
        """Format and print a message to the terminal"""
        lines = []
        content = event.get("content", {})
        msgtype = content.get("msgtype")
        sender = event.get("sender", "Unknown")
        event_id = event.get("event_id")

        # Skip non-message events or redactions
        if not msgtype or msgtype == "m.room.redaction":
            return

        # Get chat info
        room_info = self.bridge_rooms[room_id]
        room_name = room_info["name"]
        platform = room_info["platform"].upper()
        bridge_config = room_info["config"]
        bridge_user = room_info.get("user", "Unknown")  # Retrieve the user using the bridge
        bridge_owner = bridge_config.owner  # Retrieve the owner of the bridge

        # Format timestamp
        ts = event.get("origin_server_ts", 0) / 1000  # Convert ms to seconds
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

        # Extract username from sender ID
        username = sender.split(":")[0][1:]  # Remove @ and domain

        # Process different message types
        if msgtype in ["m.text", "m.notice", "m.emote"]:
            body = content.get("body", "")

        elif msgtype == "m.image":
            body = 'Image'

        elif msgtype == "m.audio":
            body = 'Audio'

        elif msgtype == "m.video":
            body = 'Video'

        elif msgtype == "m.file":
            body = 'File'
        elif msgtype == "m.location":
            body = 'Location'
        else:
            body = 'Unknown'

        record = {
                "event_id": event_id,
                "bridge_user": bridge_user,  # Add the bridge user to the record
                "bridge_owner": bridge_owner,  # Add the bridge owner to the record
                "room_id": room_id,
                "room_name": room_name,
                "sender_id": username,
                "message_body": body,
                "timestamp": time_str,
                "platform": platform,
                "created_at": datetime.now(timezone.utc)
            }

        mongo_conn = mongo_connector()
        db = mongo_conn.get_db('Project1', 'Messages')
        record = db.insert_one(record)
        print(f'Message {event_id} was received')

async def main():
    parser = argparse.ArgumentParser(
        description="Monitor messages from multiple messaging platforms via Matrix bridges")
    parser.add_argument("-u", "--username", required=True, help="Matrix username")
    parser.add_argument("-p", "--password", required=True, help="Matrix password")
    parser.add_argument("--server", help=f"Matrix server URL (default: {SYNAPSE_URL})")
    parser.add_argument("--platforms", nargs='+',
                        choices=['whatsapp', 'signal', 'telegram'],
                        default=['whatsapp', 'signal'],
                        help="Platforms to monitor (default: whatsapp signal)")

    args = parser.parse_args()

    # Print script info
    print("=" * 80)
    print("Multi-Platform Message Monitor")
    print("=" * 80)
    print(f"Monitoring platforms: {', '.join(args.platforms)}")
    print("This script shows ALL messages in your bridge rooms")
    print("Press Ctrl+C to stop the script")
    print()

    # Try to connect to server
    server_url = args.server if args.server else SYNAPSE_URL

    monitor = MultiPlatformMessageMonitor(args.username, args.password, server_url, args.platforms)

    # Login to Matrix
    print("\nAttempting to log in...")
    success = await monitor.login()
    if not success:
        print("Login failed. Exiting.")
        return

    # Find bridge rooms
    print("\nSearching for bridge rooms...")
    success = await monitor.find_bridge_rooms()
    if not success:
        print("Failed to find bridge rooms. Make sure:")
        print("1. Your messaging platforms are connected to Matrix via bridges")
        print("2. You have at least one chat visible in your Matrix client")
        print("3. Your credentials and server URL are correct")
        print("4. The bridge bot MXIDs are correct in your environment variables")
        return

    # Start monitoring
    print("\nStarting message monitoring...")
    await monitor.monitor_messages()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print("\nScript ended due to an error.")