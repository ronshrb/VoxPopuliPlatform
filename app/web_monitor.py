import asyncio
from m_monitor import MultiPlatformMessageMonitor
import streamlit as st
from PIL import Image
from io import BytesIO

class WebMonitor:
    """Wrapper class for MultiPlatformMessageMonitor to integrate with a web app."""

    def __init__(self, username, password, server_url=None, platforms=None):
        self.username = username
        self.password = password
        self.server_url = server_url
        self.platforms = platforms or ["signal"]
        self.monitor = MultiPlatformMessageMonitor(
            username=self.username,
            password=self.password,
            server_url=self.server_url,
            platforms=self.platforms
        )

    async def login(self):
        print(f"WebMonitor: Logging in using user {self.username}")
        """Log in to the Matrix server."""
        success = await self.monitor.login()
        if success:
            return {"status": "success", "message": "Logged in successfully."}
        else:
            return {"status": "error", "message": "Login failed. Check your credentials."}

    async def register(self):
        """Register a new user on the Matrix server."""
        registration_data = await self.monitor.register(self.username, self.password)
        if registration_data:
            return {"status": "success", "message": "Registration successful.", "data": registration_data}
        else:
            return {"status": "error", "message": "Registration failed. Username might already exist."}
    
    async def handle_registration(self, username, password, server_url):
        """Function to handle user registration"""
        # Initialize the WebMonitor instance
        web_monitor = WebMonitor(username=username, password=password, server_url=server_url)
        # Call the register method
        result = asyncio.run(web_monitor.register(username, password))
        # result = await web_monitor.register()
        return result

    async def generate_qr_code(self):
        """Generate a QR code by messaging the Signal bot."""
        try:
            success = await self.monitor.message_signal_bot()
            if success:
                return {"status": "success", "message": "QR code generation triggered successfully."}
            else:
                return {"status": "error", "message": "Failed to generate QR code."}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {str(e)}"}

    async def accept_invites(self):
        """Accept pending invites from the Signal bot."""
        success = await self.monitor.accept_invites()
        if success:
            return {"status": "success", "message": "Invites accepted successfully."}
        else:
            return {"status": "error", "message": "Failed to accept invites."}


    async def generate_qr_code_and_display(self, platform='whatsapp'):
        """Generate a QR code for the selected platform and display it in the web app."""
        try:
            qr_image = await self.monitor.generate_qr(platform=platform)
            if qr_image:
                buffer = BytesIO()
                qr_image.save(buffer, format="PNG")
                buffer.seek(0)
                return buffer
            else:
                st.error(f"Failed to generate QR code for {platform}.")
                return {"status": "error", "message": f"Failed to generate QR code for {platform}."}
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            return {"status": "error", "message": f"An error occurred: {str(e)}"}

    async def register_and_display_status(self):
        """Register a new account and display the status."""
        try:
            registration_data = await self.monitor.register(self.username, self.password)
            if registration_data:
                st.success("Registration successful! You can now log in.")
                return {"status": "success", "message": "Registration successful."}
            else:
                st.error("Registration failed. Username might already exist.")
                return {"status": "error", "message": "Registration failed."}
        except Exception as e:
            st.error(f"An error occurred during registration: {str(e)}")
            return {"status": "error", "message": f"An error occurred: {str(e)}"}

    async def login_and_display_status(self):
        """Log in to an account and display the status."""
        try:
            success = await self.monitor.login()
            if success:
                st.success("Login successful!")
                return {"status": "success", "message": "Login successful."}
            else:
                st.error("Login failed. Check your credentials.")
                return {"status": "error", "message": "Login failed."}
        except Exception as e:
            st.error(f"An error occurred during login: {str(e)}")
            return {"status": "error", "message": f"An error occurred: {str(e)}"}
    
    async def get_joined_chats(self, group=False, chats_blacklist=[]):
        """Return a list of joined rooms/chats with platform info."""
        print(f"WebMonitor: Get joined chats for user {self.username}") 
        try:
            joined = await self.monitor.list_rooms(room_type="joined", group=group, chats_blacklist=chats_blacklist)
            return {"status": "success", "joined_chats": joined}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get joined chats: {str(e)}"}

    async def get_invited_chats(self, group=False, chats_blacklist=[]):
        print(f"WebMonitor: Get invited chats for user {self.username}") 
        """Return a list of invited (pending) rooms/chats with platform info."""
        try:
            invites = await self.monitor.list_rooms(room_type="invited", group=group, chats_blacklist=chats_blacklist)
            return {"status": "success", "invited_chats": invites}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get invited chats: {str(e)}"}
    
    async def approve_room(self, room_id):
        """Approve (join/accept) a pending invite to a room."""
        try:
            result = await self.monitor.approve_room(room_id)
            if result:
                return {"status": "success", "message": f"Room {room_id} approved (joined) successfully."}
            else:
                return {"status": "error", "message": f"Failed to approve (join) room {room_id}."}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {str(e)}"}

    async def disable_room(self, room_id):
        """Disable (leave) a room."""
        try:
            result = await self.monitor.disable_room(room_id)
            if result:
                return {"status": "success", "message": f"Room {room_id} disabled (left) successfully."}
            else:
                return {"status": "error", "message": f"Failed to disable (leave) room {room_id}."}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {str(e)}"}
    
    async def get_room_stats(self, room_ids):
        """Get stats for a list of room_ids (number of members in each room)."""
        try:
            stats = await self.monitor.get_room_stats(room_ids)
            return {"status": "success", "room_stats": stats}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get room stats: {str(e)}"}
    
    async def change_password(self, new_password):
        """Change the password for the current user via the Matrix API."""
        try:
            result = await self.monitor.change_password(new_password)
            if result:
                return {"status": "success", "message": "Password changed successfully."}
            else:
                return {"status": "error", "message": "Failed to change password."}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {str(e)}"}
    
    async def send_message_to_telegram_bot(self, message):
        """Send a message to the Telegram bot via the Matrix bridge."""
        try:
            result = await self.monitor.send_message_to_telegram_bot(message)
            if result:
                return {"status": "success", "message": "Message sent to Telegram bot."}
            else:
                return {"status": "error", "message": "Failed to send message to Telegram bot."}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {str(e)}"}

    async def delete_user(self):
        """
        Wrapper to delete a user from the Matrix server using the Synapse Admin API.
        """
        try:
            result = await self.monitor.delete_user()
            if result:
                return {"status": "success", "message": "User deleted successfully."}
            else:
                return {"status": "error", "message": "Failed to delete user."}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {str(e)}"}
        

    async def get_last_telegram_bot_message(self):
        """
        Retrieve the last message sent by the Telegram bot in a direct chat.
        
        Returns:
            dict: A dictionary containing status and either the message text or an error message
        """
        try:
            # Call the underlying monitor method to get the last bot message
            bot_message = await self.monitor.get_last_telegram_bot_message()
            
            if bot_message:
                return {
                    "status": "success", 
                    "message": "Successfully retrieved bot message.",
                    "bot_message": bot_message
                }
            else:
                return {
                    "status": "error", 
                    "message": "No message from Telegram bot found or no direct chat exists."
                }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to retrieve Telegram bot message: {str(e)}"
            }
