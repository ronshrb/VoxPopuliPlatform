
import streamlit as st
import requests
import json
from typing import List, Dict, Optional, Tuple
import os
from dotenv import load_dotenv

load_dotenv()
SYNAPSE_URL = os.getenv("SYNAPSE_URL")
ADMIN_ACCESS_TOKEN = os.getenv("ADMIN_ACCESS_TOKEN")

class MatrixAPIClient:
    """
    Client for interacting with Matrix Synapse server and your custom Flask API
    """
    
    def __init__(self):
        self.synapse_server = SYNAPSE_URL
        self.api_server = "http://localhost:5001"
        self.session = requests.Session()
        
    def register_user_to_synapse(self, username: str, password: str) -> Tuple[bool, Dict]:
        url = f"{self.synapse_server}/_synapse/admin/v1/users/@{username}:yourdomain.com"
        
        headers = {
            'Authorization': f'Bearer {ADMIN_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        body = {
            'password': password,
            'admin': False,
            'deactivated': False
        }
        
        try:
            response = self.session.put(url, headers=headers, json=body)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}
    
    def login_to_synapse(self, username: str, password: str) -> Tuple[bool, Dict]:
        url = f"{self.synapse_server}/_matrix/client/r0/login"
        
        body = {
            'type': 'm.login.password',
            'user': username,
            'password': password
        }
        
        try:
            response = self.session.post(url, json=body)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}
    
    def create_user_in_api(self, username: str, password: str) -> Tuple[bool, Dict]:
        url = f"{self.api_server}/api/user/create"
        
        body = {
            'username': username,
            'password': password
        }
        
        try:
            response = self.session.post(url, json=body)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}
    
    def whitelist_rooms(self, username: str, room_ids: List[str]) -> Tuple[bool, Dict]:
        url = f"{self.api_server}/api/user/whitelist-rooms"
        
        body = {
            'username': username,
            'room_ids': room_ids
        }
        
        try:
            response = self.session.post(url, json=body)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}
    
    def remove_rooms_from_whitelist(self, username: str, room_ids: List[str]) -> Tuple[bool, Dict]:
        url = f"{self.api_server}/api/user/remove-rooms"
        
        body = {
            'username': username,
            'room_ids': room_ids
        }
        
        try:
            response = self.session.post(url, json=body)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}
    
    def destroy_user(self, username: str) -> Tuple[bool, Dict]:
        url = f"{self.api_server}/api/user/destroy"
        
        body = {
            'username': username
        }
        
        try:
            response = self.session.post(url, json=body)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}
    
    def get_pipeline_status(self) -> Tuple[bool, Dict]:
        url = f"{self.api_server}/api/pipeline/status"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}


def main():
    st.set_page_config(
        page_title="Matrix User Management",
        page_icon="🔐",
        layout="wide"
    )
    
    st.title("🔐 Matrix User Management System")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        synapse_server = st.text_input(
            "Synapse Server URL",
            value="https://your-matrix-server.com",
            help="URL of your Matrix Synapse server"
        )
        
        api_server = st.text_input(
            "API Server URL",
            value="http://localhost:5001",
            help="URL of your Flask API server"
        )
        
        admin_token = st.text_input(
            "Admin Token",
            type="password",
            help="Synapse admin access token"
        )
        
        if st.button("Test Connection"):
            client = MatrixAPIClient(synapse_server, api_server)
            success, data = client.get_pipeline_status()
            if success:
                st.success("✅ API Server connected successfully!")
            else:
                st.error(f"❌ Connection failed: {data.get('error', 'Unknown error')}")
    
    # Initialize client
    if synapse_server and api_server:
        client = MatrixAPIClient()
    else:
        st.warning("Please configure server URLs in the sidebar")
        return
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👤 Create User", 
        "✅ Whitelist Rooms", 
        "❌ Remove Rooms", 
        "🗑️ Destroy User",
        "📊 Pipeline Status"
    ])
    
    # Tab 1: Create User
    with tab1:
        st.header("👤 Create New User")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username", key="create_username")
            new_password = st.text_input("Password", type="password", key="create_password")
            
        with col2:
            st.info("**Process:**\n1. Register user to Synapse\n2. Login to get access token\n3. Create user in API")
        
        if st.button("Create User", type="primary"):
            if not new_username or not new_password:
                st.error("Please provide both username and password")
            elif not admin_token:
                st.error("Please provide admin token in sidebar")
            else:
                with st.spinner("Creating user..."):
                    # Step 1: Register to Synapse
                    st.info("🔄 Registering user to Synapse...")
                    success, synapse_data = client.register_user_to_synapse(new_username, new_password, admin_token)
                    
                    if success:
                        st.success("✅ User registered to Synapse")
                        
                        # Step 2: Login to get token
                        st.info("🔄 Getting access token...")
                        success, login_data = client.login_to_synapse(new_username, new_password)
                        
                        if success:
                            access_token = login_data.get('access_token', new_password)
                            st.success("✅ Access token obtained")
                            
                            # Step 3: Create in API
                            st.info("🔄 Creating user in API...")
                            success, api_data = client.create_user_in_api(new_username, access_token)
                            
                            if success:
                                st.success("✅ User created successfully in API!")
                                st.json(api_data)
                                
                                # Store user info in session state
                                if 'users' not in st.session_state:
                                    st.session_state.users = []
                                st.session_state.users.append({
                                    'username': new_username,
                                    'access_token': access_token
                                })
                            else:
                                st.error(f"❌ Failed to create user in API: {api_data}")
                        else:
                            st.error(f"❌ Failed to get access token: {login_data}")
                    else:
                        st.error(f"❌ Failed to register user to Synapse: {synapse_data}")
    
    # Tab 2: Whitelist Rooms
    with tab2:
        st.header("✅ Whitelist Rooms")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            target_username = st.text_input("Username", key="whitelist_username")
            room_ids_text = st.text_area(
                "Room IDs (one per line or comma-separated)",
                height=150,
                placeholder="!room1:example.com\n!room2:example.com\nor\n!room1:example.com, !room2:example.com",
                key="whitelist_rooms"
            )
            
        with col2:
            st.info("**Instructions:**\n- Enter one room ID per line\n- Or separate multiple IDs with commas\n- Room IDs typically start with '!'")
        
        if st.button("Whitelist Rooms", type="primary"):
            if not target_username:
                st.error("Please provide username")
            elif not room_ids_text.strip():
                st.error("Please provide room IDs")
            else:
                # Parse room IDs
                room_ids = []
                for line in room_ids_text.strip().split('\n'):
                    if ',' in line:
                        room_ids.extend([r.strip() for r in line.split(',') if r.strip()])
                    elif line.strip():
                        room_ids.append(line.strip())
                
                if room_ids:
                    with st.spinner("Whitelisting rooms..."):
                        success, data = client.whitelist_rooms(target_username, room_ids)
                        
                        if success:
                            st.success(f"✅ Successfully whitelisted {len(room_ids)} rooms")
                            st.json(data)
                        else:
                            st.error(f"❌ Failed to whitelist rooms: {data}")
                else:
                    st.error("No valid room IDs found")
    
    # Tab 3: Remove Rooms
    with tab3:
        st.header("❌ Remove Rooms from Whitelist")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            remove_username = st.text_input("Username", key="remove_username")
            remove_room_ids_text = st.text_area(
                "Room IDs to Remove (one per line or comma-separated)",
                height=150,
                placeholder="!room1:example.com\n!room2:example.com",
                key="remove_rooms"
            )
            
        with col2:
            st.warning("**Warning:**\nThis will remove the specified rooms from the user's whitelist.")
        
        if st.button("Remove Rooms", type="secondary"):
            if not remove_username:
                st.error("Please provide username")
            elif not remove_room_ids_text.strip():
                st.error("Please provide room IDs to remove")
            else:
                # Parse room IDs
                room_ids = []
                for line in remove_room_ids_text.strip().split('\n'):
                    if ',' in line:
                        room_ids.extend([r.strip() for r in line.split(',') if r.strip()])
                    elif line.strip():
                        room_ids.append(line.strip())
                
                if room_ids:
                    with st.spinner("Removing rooms from whitelist..."):
                        success, data = client.remove_rooms_from_whitelist(remove_username, room_ids)
                        
                        if success:
                            st.success(f"✅ Successfully removed {len(room_ids)} rooms from whitelist")
                            st.json(data)
                        else:
                            st.error(f"❌ Failed to remove rooms: {data}")
                else:
                    st.error("No valid room IDs found")
    
    # Tab 4: Destroy User
    with tab4:
        st.header("🗑️ Destroy User")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            destroy_username = st.text_input("Username to Destroy", key="destroy_username")
            confirm_destroy = st.checkbox("I understand this action cannot be undone")
            
        with col2:
            st.error("**⚠️ DANGER ZONE**\n\nThis will permanently delete the user and all associated data. This action cannot be undone!")
        
        if st.button("🗑️ Destroy User", type="secondary"):
            if not destroy_username:
                st.error("Please provide username to destroy")
            elif not confirm_destroy:
                st.error("Please confirm you understand this action cannot be undone")
            else:
                with st.spinner("Destroying user..."):
                    success, data = client.destroy_user(destroy_username)
                    
                    if success:
                        st.success(f"✅ User '{destroy_username}' destroyed successfully")
                        st.json(data)
                    else:
                        st.error(f"❌ Failed to destroy user: {data}")
    
    # Tab 5: Pipeline Status
    with tab5:
        st.header("📊 Pipeline Status")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Check Pipeline Status", type="primary"):
                with st.spinner("Checking pipeline status..."):
                    success, data = client.get_pipeline_status()
                    
                    if success:
                        st.success("✅ Pipeline status retrieved")
                        st.json(data)
                    else:
                        st.error(f"❌ Failed to get pipeline status: {data}")
        
        with col2:
            st.info("Click the button to check the current status of your pipeline.")
        
        # Auto-refresh option
        if st.checkbox("Auto-refresh every 30 seconds"):
            import time
            time.sleep(30)
            st.rerun()


if __name__ == "__main__":
    main()