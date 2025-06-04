#!/usr/bin/env python3
# MultiPlatformMessageMonitor: Matrix bridge monitor for WhatsApp, Signal, Telegram
# Handles login, room management, message monitoring, and MongoDB integration
# Author: [Your Name]
# Date: [Date]

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
from io import BytesIO
import qrcode

# from matrix import m_monitor

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Matrix server configuration
SYNAPSE_URL = os.getenv("SYNAPSE_URL")
WHATSAPP_BOT_MXID = os.getenv("WHATSAPP_BOT_MXID")
TELEGRAM_BOT_MXID = os.getenv("TELEGRAM_BOT_MXID")
SIGNAL_BOT_MXID = os.getenv("SIGNAL_BOT_MXID")
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_ACCESS_TOKEN = os.getenv("ADMIN_ACCESS_TOKEN")


class BridgeConfig:
    """
    Configuration for different bridge types (WhatsApp, Signal, Telegram).
    Stores bot MXID, room indicators, and message parsing patterns.
    """

    def __init__(self, name: str, bot_mxid: str, room_indicators: List[str], message_patterns: Optional[Dict] = None):
        self.name = name
        self.bot_mxid = bot_mxid
        self.room_indicators = room_indicators  # Strings that indicate this type of bridge room
        self.message_patterns = message_patterns or {}

class mongo_connector():
    """
    MongoDB connector utility for accessing collections.
    """
    def __init__(self):
        self.db_connection_string = MONGODB_URI
        self.client = MongoClient(self.db_connection_string)
        self.db = None

    def get_client(self):
        # Return MongoDB client instance
        return self.client
    
    def get_db(self, db_name, collection_name):
        # Return a collection handle for the given db and collection
        return self.client[db_name][collection_name]

class MultiPlatformMessageMonitor:
    """
    Main monitor class for Matrix bridge rooms and messages.
    Handles login, room listing, joining/leaving, message monitoring, and MongoDB logging.
    """

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
                }
            )

        if 'signal' in platforms:
            self.bridge_configs['signal'] = BridgeConfig(
                name="Signal",
                bot_mxid=SIGNAL_BOT_MXID,
                room_indicators=["Signal", "SG:", "Signal Chat"],
                message_patterns={
                    'sender_format': r"^(.*?):\s+(.*?)$"  # Similar format for Signal
                }
            )

        if 'telegram' in platforms:
            self.bridge_configs['telegram'] = BridgeConfig(
                name="Telegram",
                bot_mxid=TELEGRAM_BOT_MXID,
                room_indicators=["Telegram", "TG:", "Telegram Chat"],
                message_patterns={
                    'sender_format': r"^(.*?):\s+(.*?)$"  # Similar format for Telegram
                }
            )

        # Print configuration
        print(f"Using Matrix server: {self.synapse_url}")
        print(f"Username: {self.username}")
        print("Configured bridges:")
        for platform, config in self.bridge_configs.items():
            print(f"  - {config.name}: {config.bot_mxid}")
            
    async def register(self, username, password):
        """
        Register a new user on the Matrix server using admin access token.
        """
        headers = {
            "Authorization": f"Bearer {ADMIN_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        # Remove port number from the domain
        domain = self.synapse_url.split("//")[1].split(":")[0]
        register_url = f"{self.synapse_url}/_synapse/admin/v2/users/@{username}:{domain}"

        payload = {
            "password": password,
            "displayname": username,
            "admin": False,
            "deactivated": False
        }

        async with httpx.AsyncClient(verify=True, timeout=30.0) as client:
            try:
                logger.info(f"Sending registration request to {register_url}")
                response = await client.put(register_url, headers=headers, json=payload)

                logger.info(f"Registration response status: {response.status_code}")
                if response.text:
                    logger.info(f"Response body: {response.text[:500]}")

                if response.status_code in [200, 201]:
                    logger.info(f"Successfully registered user: {username}")
                    return response.json() if response.text else {}
                else:
                    logger.error(f"Registration failed: {response.status_code} - {response.text}")
                    return None
            except httpx.HTTPError as http_err:
                logger.error(f"HTTP error during registration: {http_err}")
                return None
            except Exception as e:
                logger.error(f"Exception during registration: {str(e)}")
                return None
            
    async def login(self):
        """
        Log in to Matrix and obtain an access token for API calls.
        """
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
        """
        Find all joined rooms that are bridge rooms for configured platforms.
        """
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
        """
        Check if a room is a bridge room and identify which platform it belongs to.
        """
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
        """
        Monitor for all messages in bridge rooms using Matrix sync API.
        """
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
        """
        Process events from sync response and print all messages for joined bridge rooms.
        """
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
        """
        Format and print a message to the terminal, handling bridge bot formatting.
        """
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

    async def generate_qr(self, platform='whatsapp'):
        """
        Send a message to the bridge bot to create a room, then retrieve and return the QR code.
        If a direct chat with the bot exists, leave it first.
        """
        if not self.access_token:
            print("Not logged in. Cannot generate QR code.")
            return None

        # Select bot MXID and login command based on platform
        if platform == 'signal':
            bot_mxid = SIGNAL_BOT_MXID
            login_command = "login qr"
            qr_prefix = "sgnl://"
        elif platform == 'whatsapp':
            bot_mxid = WHATSAPP_BOT_MXID
            login_command = "login qr"
            qr_prefix = "whatsapp://"
        elif platform == 'telegram':
            bot_mxid = TELEGRAM_BOT_MXID
            login_command = "/login"
            qr_prefix = "tg://"
        else:
            print(f"Unsupported platform: {platform}")
            return None

        create_room_url = f"{self.synapse_url}/_matrix/client/v3/createRoom"
        message_url_template = f"{self.synapse_url}/_matrix/client/v3/rooms/{{room_id}}/send/m.room.message"
        # Step 0: Check for existing direct chat with the bot and leave it
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            joined_rooms_url = f"{self.synapse_url}/_matrix/client/v3/joined_rooms"
            response = await client.get(
                joined_rooms_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if response.status_code == 200:
                room_ids = response.json().get("joined_rooms", [])
                for room_id in room_ids:
                    member_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/state/m.room.member/{bot_mxid}"
                    member_resp = await client.get(
                        member_url,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    if member_resp.status_code == 200:
                        state_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/state/m.room.create"
                        state_resp = await client.get(
                            state_url,
                            headers={"Authorization": f"Bearer {self.access_token}"}
                        )
                        if state_resp.status_code == 200 and state_resp.json().get("is_direct", False):
                            print(f"Leaving existing direct chat with {platform} bot: {room_id}")
                            await self._leave_room(client, room_id)
            room_id = None
            try:
                # Step 1: Create a direct chat with the bot
                print(f"Creating a direct chat with the {platform} bot: {bot_mxid}")
                create_room_payload = {
                    "is_direct": True,
                    "invite": [bot_mxid],
                    "preset": "trusted_private_chat"
                }
                create_room_response = await client.post(
                    create_room_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=create_room_payload
                )

                if create_room_response.status_code != 200:
                    print(f"Failed to create a direct chat: {create_room_response.status_code} - {create_room_response.text}")
                    return None

                room_id = create_room_response.json().get("room_id")
                print(f"Direct chat created with {platform} bot. Room ID: {room_id}")

                # Step 2: Send the starting message to the bot
                print(f"Requesting QR code from the {platform} bot...")
                message_url = message_url_template.format(room_id=room_id)
                login_message_payload = {
                    "msgtype": "m.text",
                    "body": "Hello"
                }
                login_message_response = await client.post(
                    message_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=login_message_payload
                )

                if login_message_response.status_code != 200:
                    print(f"Failed to send initial message: {login_message_response.status_code} - {login_message_response.text}")
                    return None
                
                print("Waiting for the bot to respond...")
                await asyncio.sleep(5)  

                # Step 3: Send the login command to the bot
                print(f"Sending '{login_command}' to the {platform} bot...")
                login_message_payload = {
                    "msgtype": "m.text",
                    "body": login_command
                }
                login_message_response = await client.post(
                    message_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=login_message_payload
                )

                if login_message_response.status_code != 200:
                    print(f"Failed to send '{login_command}' message: {login_message_response.status_code} - {login_message_response.text}")
                    return None

                print("Waiting for QR code message...")
                await asyncio.sleep(10)  # Wait for the QR code message to arrive

                # Step 4: Retrieve the QR code from the room's messages
                room_events_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/messages"
                response = await client.get(
                    room_events_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params={"limit": 10, "dir": "b"}  # Fetch the last 10 messages
                )
                print("retriving for QR code message...")
                if response.status_code != 200:
                    print(f"Failed to fetch room messages: {response.status_code} - {response.text}")
                    return None

                events = response.json().get("chunk", [])
                for event in events:
                    content = event.get("content", {})
                    msgtype = content.get("msgtype")
                    sender = event.get("sender", "")
                    body = content.get("body", "")

                    # WhatsApp: If the body looks like a QR payload (3-4 base64 segments separated by commas), use it directly
                    if (
                        platform == 'whatsapp' and
                        sender == bot_mxid and
                        msgtype == "m.image"
                        # re.match(r"^[A-Za-z0-9+/=]+,[A-Za-z0-9+/=]+,[A-Za-z0-9+/=]+(,[A-Za-z0-9+/=]+)?$", body.strip())
                    ):
                        try:
                            qr = qrcode.QRCode()
                            qr.add_data(body.strip())
                            qr.make(fit=True)
                            img = qr.make_image(fill="black", back_color="white")
                            print("WhatsApp QR code generated from string payload.")
                            return img
                        except Exception as e:
                            print(f"Failed to generate WhatsApp QR code from string: {str(e)}")
                            return None

                    # Signal/Telegram: QR is a link in the body
                    if sender == bot_mxid and msgtype == "m.image":
                        qr_link = body
                        try:
                            qr = qrcode.QRCode()
                            qr.add_data(qr_link)
                            qr.make(fit=True)
                            img = qr.make_image(fill="black", back_color="white")
                            print("QR code successfully generated.")
                            return img
                        except Exception as e:
                            print(f"Failed to generate QR code: {str(e)}")
                            return None

                print("QR code message not found.")
                return None

            except Exception as e:
                print(f"Error during QR code generation: {str(e)}")
                return None
            finally:
                if room_id:
                    await self._leave_room(client, room_id)
    async def _leave_room(self, client, room_id):
        """
        Leave the Matrix room with the given room_id.
        """
        try:
            leave_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/leave"
            response = await client.post(
                leave_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if response.status_code == 200:
                print(f"Successfully left the room {room_id}")
            else:
                print(f"Failed to leave the room {room_id}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Exception while leaving the room {room_id}: {str(e)}")
            
    async def insert_msg_to_mongo(self, room_id, event):
        """
        Insert a message event into MongoDB for archiving and analytics.
        """
        lines = []
        content = event.get("content", {})
        msgtype = content.get("msgtype")
        sender = event.get("sender", "Unknown")
        event_id = event.get("event_id")
        bridge_user= self.user_id.split(':')[0][1:]  # Remove @ and domain

        # Skip non-message events or redactions
        if not msgtype or msgtype == "m.room.redaction":
            return

        # Get chat info
        room_info = self.bridge_rooms[room_id]
        room_name = room_info["name"]
        # bridge_user = room_info["config"]["user_id"]
        platform = room_info["platform"].upper()
        bridge_config = room_info["config"]

        # Format timestamp
        ts = event.get("origin_server_ts", 0) / 1000  # Convert ms to seconds
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

        # Extract username from sender ID
        username = sender.split(":")[0][1:]  # Remove @ and domain
        if room_info["bot_mxid"] == sender:
                return

        # Process different message types
        elif msgtype in ["m.text", "m.notice"]:
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
        elif msgtype == "m.emote":
            body = 'Emote'
        else:
            body = 'Unknown'

        record = {
                "event_id": event_id,
                "bridge_user": bridge_user , # Add the user_id of the monitor
                "room_id": room_id.split(':')[0],  # Remove @ and domain
                "room_name": room_name,
                "sender_id": username,
                # "message_type": msgtype,
                "message_body": body,
                "timestamp": time_str,
                "platform": platform,
                "created_at": datetime.now(timezone.utc)
            }

        mongo_conn = mongo_connector()
        db = mongo_conn.get_db('VoxPopuli', 'PRJ001')
        db.insert_one(record)
        print(f'Message {event_id} was recieved')

    async def detect_room_platform(self, room_id, client, invite_state=None):
        """
        Detect the platform of a room by checking for the presence of bridge bot MXIDs as members,
        or by checking the invite event's sender if provided.
        """
        # If invite_state is provided (for invites), check sender of invite events
        if invite_state:
            for event in invite_state:
                sender = event.get("sender")
                if sender:
                    for plat, config in self.bridge_configs.items():
                        if sender == config.bot_mxid:
                            return plat
        # Fallback: check for bot as member (works for joined rooms)
        for plat, config in self.bridge_configs.items():
            member_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/state/m.room.member/{config.bot_mxid}"
            member_resp = await client.get(
                member_url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if member_resp.status_code == 200:
                return plat
        return None

    async def list_rooms(self, room_type="joined", group=True, chats_blacklist=[]):
        """
        List rooms of a given type: 'joined' or 'invited'.
        If group=True, return only group rooms. Adds platform info.
        Filters out blacklisted rooms.
        """
        if not self.access_token:
            print(f"Not logged in. Cannot list {room_type} rooms.")
            return []

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                if room_type == "invited":
                    # Invited rooms (pending invites)
                    invites_url = f"{self.synapse_url}/_matrix/client/v3/sync"
                    response = await client.get(
                        invites_url,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        params={"timeout": 10000}
                    )
                    if response.status_code != 200:
                        print(f"Failed to fetch invites: {response.status_code} - {response.text}")
                        return []
                    data = response.json()
                    rooms = data.get("rooms", {}).get("invite", {})
                    result = []
                    for room_id, room_data in rooms.items():
                        if room_id in chats_blacklist:
                            continue
                        room_name = None
                        invite_state = room_data.get("invite_state", {}).get("events", [])
                        for event in invite_state:
                            if event.get("type") == "m.room.name":
                                room_name = event.get("content", {}).get("name")
                                break
                        platform = await self.detect_room_platform(room_id, client, invite_state=invite_state)
                        if group:
                            is_group = await self.is_group_room(room_name)
                            if not is_group:
                                continue
                        result.append({"ChatID": room_id, "Chat Name": room_name, "Platform": platform, 'UserID': self.username, "Donated": False})
                    print("Pending invites:")
                    for invite in result:
                        print(f"  - {invite['ChatID']} ({invite['Chat Name'] or 'Unnamed'}) [Platform: {invite['Platform'] or 'unknown'}]")
                    return result
                else:
                    # Joined rooms
                    joined_rooms_url = f"{self.synapse_url}/_matrix/client/v3/joined_rooms"
                    response = await client.get(
                        joined_rooms_url,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    if response.status_code != 200:
                        print(f"Failed to fetch joined rooms: {response.status_code} - {response.text}")
                        return []
                    room_ids = response.json().get("joined_rooms", [])
                    result = []
                    for room_id in room_ids:
                        if room_id in chats_blacklist:
                            continue
                        name_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/state/m.room.name"
                        name_resp = await client.get(
                            name_url,
                            headers={"Authorization": f"Bearer {self.access_token}"}
                        )
                        if name_resp.status_code == 200:
                            room_name = name_resp.json().get("name")
                        else:
                            room_name = None
                        if group:
                            is_group = await self.is_group_room(room_name)
                            if not is_group:
                                continue
                        platform = await self.detect_room_platform(room_id, client)
                        result.append({"ChatID": room_id, "Chat Name": room_name, "Platform": platform, 'UserID': self.username, "Donated": True})
                    print("Joined rooms:")
                    for room in result:
                        print(f"  - {room['ChatID']} ({room['Chat Name'] or 'Unnamed'}) [Platform: {room['Platform'] or 'unknown'}]")
                    return result
            except Exception as e:
                print(f"Error while listing {room_type} rooms: {str(e)}")
                return []


    async def rejoin_signal_bot_room(self):
        """
        Rejoin the Signal bot's room if it is missing for the current user.
        """
        if not self.access_token:
            print("Not logged in. Cannot rejoin Signal bot room.")
            return False

        # Replace with the known alias or room ID of the Signal bot's room
        signal_room_alias = f"#{self.username}_signal:vox-populi.dev"

        join_url = f"{self.synapse_url}/_matrix/client/v3/join/{signal_room_alias}"

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                print(f"Attempting to rejoin Signal bot room: {signal_room_alias}")
                response = await client.post(
                    join_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )

                if response.status_code == 200:
                    print(f"Successfully rejoined Signal bot room: {signal_room_alias}")
                    return True
                else:
                    print(f"Failed to rejoin Signal bot room: {response.status_code} - {response.text}")
                    return False

            except Exception as e:
                print(f"Error while rejoining Signal bot room: {str(e)}")
                return False


    async def message_bridge_bot(self, platform):
        """
        Send a direct message to the bridge bot (Signal, WhatsApp, or Telegram),
        wait 10 seconds, then send 'login qr' or equivalent command.
        """
        if not self.access_token:
            print(f"Not logged in. Cannot message {platform} bot.")
            return False

        # Select bot MXID and greeting based on platform
        if platform == 'signal':
            bot_mxid = SIGNAL_BOT_MXID
            greeting = "Hello, Signal bot!"
            login_command = "login qr"
        elif platform == 'whatsapp':
            bot_mxid = WHATSAPP_BOT_MXID
            greeting = "Hello, WhatsApp bot!"
            login_command = "login qr"
        elif platform == 'telegram':
            bot_mxid = TELEGRAM_BOT_MXID
            greeting = "Hello, Telegram bot!"
            login_command = "/login"  # Telegram bridges often use /login
        else:
            print(f"Unsupported platform: {platform}")
            return False

        create_room_url = f"{self.synapse_url}/_matrix/client/v3/createRoom"
        message_url_template = f"{self.synapse_url}/_matrix/client/v3/rooms/{{room_id}}/send/m.room.message"

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                # Step 1: Create a direct chat with the bridge bot
                print(f"Creating a direct chat with the {platform} bot: {bot_mxid}")
                create_room_payload = {
                    "is_direct": True,
                    "invite": [bot_mxid],
                    "preset": "trusted_private_chat"
                }
                create_room_response = await client.post(
                    create_room_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=create_room_payload
                )

                if create_room_response.status_code != 200:
                    print(f"Failed to create a direct chat: {create_room_response.status_code} - {create_room_response.text}")
                    return False

                room_id = create_room_response.json().get("room_id")
                print(f"Direct chat created with {platform} bot. Room ID: {room_id}")

                # Step 2: Send an initial message to the bot
                print(f"Sending initial message to the {platform} bot...")
                message_url = message_url_template.format(room_id=room_id)
                initial_message_payload = {
                    "msgtype": "m.text",
                    "body": greeting
                }
                initial_message_response = await client.post(
                    message_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=initial_message_payload
                )

                if initial_message_response.status_code != 200:
                    print(f"Failed to send initial message to {platform} bot: {initial_message_response.status_code} - {initial_message_response.text}")
                    return False

                print("Initial message sent. Waiting for 10 seconds...")
                await asyncio.sleep(10)  # Wait for 10 seconds

                # Step 3: Send the login command to the bot
                print(f"Sending '{login_command}' to the {platform} bot...")
                login_message_payload = {
                    "msgtype": "m.text",
                    "body": login_command
                }
                login_message_response = await client.post(
                    message_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=login_message_payload
                )

                if login_message_response.status_code == 200:
                    print(f"Message '{login_command}' sent to {platform} bot successfully.")
                    return True
                else:
                    print(f"Failed to send '{login_command}' to {platform} bot: {login_message_response.status_code} - {login_message_response.text}")
                    return False

            except Exception as e:
                print(f"Error while messaging {platform} bot: {str(e)}")
                return False

    async def is_group_room(self, room_name):
        """
        Check if a room is a group (not a direct chat).
        Uses platform-specific heuristics for Signal and WhatsApp.
        """
        try:
            # if not room_name or roosm_name.strip() == "":
            #     return False
            if not room_name:
                return None
            if 'Signal' in room_name:
                return False
            if '(WA)' in room_name or 'WhatsApp' in room_name:
                return False
            else:
                return True
        except Exception as e:
            print(f"Error checking if room {room_name} is group: {str(e)}")
            return True
        # return True
        

    async def approve_room(self, room_id):
        """
        Accept (join) a pending invite to a room.
        """
        if not self.access_token:
            print("Not logged in. Cannot approve room.")
            return False
        join_url = f"{self.synapse_url}/_matrix/client/v3/join/{room_id}"
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                response = await client.post(
                    join_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                if response.status_code == 200:
                    print(f"Successfully approved (joined) room: {room_id}")
                    return True
                else:
                    print(f"Failed to approve room {room_id}: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"Error while approving room {room_id}: {str(e)}")
                return False

    async def disable_room(self, room_id):
        """
        Leave (disable) a room by sending a leave request to Matrix.
        """
        if not self.access_token:
            print("Not logged in. Cannot disable room.")
            return False
        leave_url = f"{self.synapse_url}/_matrix/client/v3/rooms/{room_id}/leave"
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                response = await client.post(
                    leave_url,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                if response.status_code == 200:
                    print(f"Successfully disabled (left) room: {room_id}")
                    return True
                else:
                    print(f"Failed to disable room {room_id}: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"Error while disabling room {room_id}: {str(e)}")
                return False

    async def delete_user(self):
        """
        Delete a user from the Matrix server using the Synapse Admin API.
        Requires admin access token. If username is None, deletes self.username.
        """
        if not ADMIN_ACCESS_TOKEN:
            print("Admin access token not set. Cannot delete user.")
            return False
        user = self.username
        # Remove port if present in domain
        domain = self.synapse_url.split('//')[1].split(':')[0]
        user_id = f"@{user}:{domain}"
        delete_url = f"{self.synapse_url}/_synapse/admin/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {ADMIN_ACCESS_TOKEN}"}
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            try:
                response = await client.delete(delete_url, headers=headers)
                if response.status_code in [200, 204]:
                    print(f"Successfully deleted user: {user_id}")
                    return True
                else:
                    print(f"Failed to delete user {user_id}: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"Error while deleting user {user_id}: {str(e)}")
                return False



# async def main():
#     parser = argparse.ArgumentParser(
#         description="Monitor messages from multiple messaging platforms via Matrix bridges")
#     parser.add_argument("-u", "--username", required=True, help="Matrix username")
#     parser.add_argument("-p", "--password", required=True, help="Matrix password")
#     parser.add_argument("--server", help=f"Matrix server URL (default: {SYNAPSE_URL})")
#     parser.add_argument("--platforms", nargs='+',
#                         choices=['whatsapp', 'signal', 'telegram'],
#                         default=['whatsapp', 'signal'],
#                         help="Platforms to monitor (default: whatsapp signal)")
#     parser.add_argument("--register", action="store_true", help="Register a new user before logging in")
#     parser.add_argument("--list-invites", action="store_true", help="List pending invites and exit")
#     parser.add_argument("--list-joined", action="store_true", help="List joined rooms and exit")
#     parser.add_argument("--qr",
#                         choices=['whatsapp', 'signal', 'telegram'],
#                         help="Get QR code for login")


#     args = parser.parse_args()

#     # Print script info
#     print("=" * 80)
#     print("Multi-Platform Message Monitor")
#     print("=" * 80)
#     print(f"Monitoring platforms: {', '.join(args.platforms)}")
#     print("This script shows ALL messages in your bridge rooms")
#     print("Press Ctrl+C to stop the script")
#     print()

#     # Try to connect to server
#     server_url = args.server if args.server else SYNAPSE_URL

#     monitor = MultiPlatformMessageMonitor(args.username, args.password, server_url, args.platforms)

#     # Register user if requested
#     if args.register:
#         print("\nAttempting to register user...")
#         registration_data = await monitor.register(args.username, args.password)
#         if not registration_data:
#             print("Registration failed. Exiting.")
#             return

#     # Login to Matrix
#     print("\nAttempting to log in...")
#     success = await monitor.login()
#     if not success:
#         print("Login failed. Exiting.")
#         return

#     # platforms_mapping = {
#     #     'whatsapp': WHATSAPP_BOT_MXID,
#     #     'signal': SIGNAL_BOT_MXID,
#     #     'telegram': TELEGRAM_BOT_MXID
#     # }
#     if args.qr:
#         print("\nGenerating QR code...")
#         await monitor.message_bridge_bot(args.qr)


#     # # Accept pending invites
#     # print("\nAccepting pending invites...")
#     # await monitor.accept_invites()
#     if args.list_invites:
#             print("\nListing pending invites...")
#             invites = await monitor.list_pending_invites()
#             print(invites)
#             return
    
#     if args.list_joined:
#         print("\nListing joined rooms...")
#         joined = await monitor.list_joined_rooms()
#         print(joined)
#         return

#     # # Find bridge rooms
#     # print("\nSearching for bridge rooms...")
#     # success = await monitor.find_bridge_rooms()
#     # if not success:
#     #     print("Failed to find bridge rooms. Make sure:")
#     #     print("1. Your messaging platforms are connected to Matrix via bridges")
#     #     print("2. You have at least one chat visible in your Matrix client")
#     #     print("3. Your credentials and server URL are correct")
#     #     print("4. The bridge bot MXIDs are correct in your environment variables")
#     #     return

#     # # Start monitoring
#     print("\nStarting message monitoring...")
#     await monitor.monitor_messages()


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\nMonitor stopped by user.")
#     except Exception as e:
#         print(f"Fatal error: {str(e)}")
#         print("\nScript ended due to an error.")