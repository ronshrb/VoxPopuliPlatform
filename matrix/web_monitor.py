import asyncio
from m_monitor_copy_2 import MultiPlatformMessageMonitor

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

    async def find_bridge_rooms(self):
        """Find all bridge rooms for the configured platforms."""
        success = await self.monitor.find_bridge_rooms()
        if success:
            return {"status": "success", "message": "Bridge rooms found successfully.", "rooms": self.monitor.bridge_rooms}
        else:
            return {"status": "error", "message": "Failed to find bridge rooms."}

    async def monitor_messages(self):
        """Start monitoring messages in bridge rooms."""
        success = await self.monitor.monitor_messages()
        if success:
            return {"status": "success", "message": "Monitoring started successfully."}
        else:
            return {"status": "error", "message": "Failed to start monitoring messages."}
