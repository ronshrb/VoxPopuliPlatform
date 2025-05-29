from flask import Flask, request, jsonify
import uuid # For RoomID, assuming it's a string like UUID

app = Flask(__name__)

# In-memory database to store users and their whitelisted rooms
# users_db = {
# "username1": {"password": "password1", "whitelisted_rooms": {"room_id1", "room_id2"}},
# "username2": {"password": "password2", "whitelisted_rooms": set()},
# }
users_db = {}

# --- Helper Function for API Response ---
def api_response(success, message, status_code=200):
    """Generates a standard API JSON response."""
    response = jsonify({"success": success, "message": message})
    response.status_code = status_code
    return response

# --- /api/user/create ---
@app.route("/api/user/create", methods=["POST"])
def create_user_handler():
    """
    Handles user creation requests.
    Expected JSON: {"username": "string", "password": "string"}
    """
    if not request.is_json:
        return api_response(False, "Invalid JSON: Request must be JSON", 400)

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return api_response(False, "Missing username or password", 400)

    if username in users_db:
        return api_response(False, f"User {username} already exists", 409) # 409 Conflict

    # Simulate user creation
    users_db[username] = {"password": password, "whitelisted_rooms": set()}
    print(f"Mock API: User '{username}' created.")
    return api_response(True, f"User {username} created successfully")

# --- /api/user/whitelist-rooms ---
@app.route("/api/user/whitelist-rooms", methods=["POST"])
def whitelist_rooms_handler():
    """
    Handles whitelisting rooms for a user.
    Expected JSON: {"username": "string", "room_ids": ["id1", "id2", ...]}
    """
    if not request.is_json:
        return api_response(False, "Invalid JSON: Request must be JSON", 400)

    data = request.get_json()
    username = data.get("username")
    room_ids = data.get("room_ids") # Assuming room_ids is a list of strings

    if not username or room_ids is None: # Check for room_ids being explicitly None
        return api_response(False, "Missing username or room_ids", 400)

    if not isinstance(room_ids, list):
        return api_response(False, "room_ids must be a list", 400)

    if username not in users_db:
        return api_response(False, f"User {username} not found", 404)

    # Simulate whitelisting rooms
    current_user = users_db[username]
    newly_whitelisted_count = 0
    for room_id in room_ids:
        if room_id not in current_user["whitelisted_rooms"]:
            current_user["whitelisted_rooms"].add(str(room_id)) # Ensure room_id is string
            newly_whitelisted_count += 1
    
    print(f"Mock API: User '{username}' whitelisted rooms: {room_ids}. Total whitelisted: {len(current_user['whitelisted_rooms'])}")
    return api_response(True, f"Added {len(room_ids)} rooms to whitelist for user {username}")

# --- /api/user/remove-rooms ---
@app.route("/api/user/remove-rooms", methods=["POST"])
def remove_rooms_handler():
    """
    Handles removing rooms from a user's whitelist.
    Expected JSON: {"username": "string", "room_ids": ["id1", "id2", ...]}
    """
    if not request.is_json:
        return api_response(False, "Invalid JSON: Request must be JSON", 400)

    data = request.get_json()
    username = data.get("username")
    room_ids = data.get("room_ids")

    if not username or room_ids is None:
        return api_response(False, "Missing username or room_ids", 400)

    if not isinstance(room_ids, list):
        return api_response(False, "room_ids must be a list", 400)

    if username not in users_db:
        return api_response(False, f"User {username} not found", 404)

    # Simulate removing rooms
    current_user = users_db[username]
    removed_count = 0
    for room_id in room_ids:
        if str(room_id) in current_user["whitelisted_rooms"]:
            current_user["whitelisted_rooms"].discard(str(room_id)) # Use discard to avoid error if not present
            removed_count +=1
            
    print(f"Mock API: User '{username}' removed rooms: {room_ids}. Total whitelisted: {len(current_user['whitelisted_rooms'])}")
    return api_response(True, f"Removed {len(room_ids)} rooms from whitelist for user {username}")

# --- /api/user/destroy ---
@app.route("/api/user/destroy", methods=["POST"])
def destroy_user_handler():
    """
    Handles destroying a user.
    Expected JSON: {"username": "string"}
    """
    if not request.is_json:
        return api_response(False, "Invalid JSON: Request must be JSON", 400)

    data = request.get_json()
    username = data.get("username")

    if not username:
        return api_response(False, "Missing username", 400)

    if username not in users_db:
        return api_response(False, f"User {username} not found", 404)

    # Simulate destroying user
    del users_db[username]
    print(f"Mock API: User '{username}' destroyed.")
    return api_response(True, f"User {username} destroyed successfully")

# --- /api/pipeline/status ---
@app.route("/api/pipeline/status", methods=["GET", "POST"]) # Allowing GET as status is often fetched via GET
def pipeline_status_handler():
    """
    Handles pipeline status requests.
    For POST, it doesn't expect a specific body for this mock.
    """
    # Simulate a pipeline status
    # In a real scenario, this would check the actual pipeline.
    # For the mock, we'll just return a generic success message.
    # The Go code's pipeline.statusHandler is not fully defined in the prompt,
    # so this is a simple mock.
    if request.method == "POST":
        # If it's a POST, you might want to check for a body or specific headers
        # if the actual API requires them, but for a simple mock, this is okay.
        print("Mock API: Pipeline status requested via POST.")
    else: # GET request
        print("Mock API: Pipeline status requested via GET.")
        
    return api_response(True, "Pipeline is operational (mocked)")


if __name__ == "__main__":
    # Run the Flask app
    # You can change the host and port as needed
    # Use `debug=True` for development, but turn it off for production
    print("Starting Python Mock API Server...")
    app.run(host="0.0.0.0", port=5001, debug=True)