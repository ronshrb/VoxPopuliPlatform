# import streamlit as st
# from user_app import user_app
# from researcher_app import researcher_app
# from dbs import *
#
# # Initialize session state for login
# if "logged_in" not in st.session_state:
#     st.session_state["logged_in"] = False
#     st.session_state["role"] = None
#     st.session_state["username"] = None
#
# # Main app
# st.title("Welcome to VoxPopuli 🗣️")
#
# if not st.session_state["logged_in"]:
#     # Role selection and login
#     role = st.selectbox("Select Role", ["User", "Researcher"])
#     project = st.text_input("Project ID")  # need to add later
#     username = st.text_input("Username")  # need to change to email? id?
#     password = st.text_input("Password", type="password")
#     if st.button("Login"):
#         # Add authentication logic here
#         if username and password:  # Replace with actual validation
#             st.session_state["logged_in"] = True
#             st.session_state["role"] = role
#             st.session_state["username"] = username
#             st.experimental_rerun()  # Refresh the app to show the appropriate page
#         else:
#             st.error("Invalid username or password.")
# else:
#     # Redirect to the appropriate app based on role
#     if st.session_state["role"] == "User":
#         user_app(st.session_state["username"])
#     elif st.session_state["role"] == "Researcher":
#         researcher_app(st.session_state["username"])
import streamlit as st
import bcrypt
from user_app import user_app
from researcher_app import researcher_app
from dbs import users_df  # Assuming you load users from your DB

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["email"] = None

# Main app
st.title("Welcome to VoxPopuli 🗣️")

if not st.session_state["logged_in"]:
    # Role selection and login
    role = st.selectbox("Select Role", ["User", "Researcher"])
    project = st.text_input("Project ID")  # You can add this later if needed
    email = st.text_input("Email")  # Use email or username
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Simple authentication logic with bcrypt password hashing
        user_data = users_df[users_df['Email'] == email]

        if not user_data.empty:
            # Get the stored hash from the database
            stored_hashed_password = user_data.iloc[0]['HashedPassword']
            # Check if the provided password matches the hashed password
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
                st.session_state["logged_in"] = True
                st.session_state["role"] = user_data.iloc[0]['Role']
                st.session_state["email"] = email
                st.rerun()  # Refresh the app to show the appropriate page
            else:
                st.error("Invalid username or password.")
        else:
            st.error("User not found.")
else:
    # Redirect to the appropriate app based on role
    if st.session_state["role"] == "User":
        user_app(st.session_state["email"])
    elif st.session_state["role"] == "Researcher":
        researcher_app(st.session_state["email"])

    # Optional logout button to clear session state
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["role"] = None
        st.session_state["email"] = None
        st.rerun()  # Refresh to show login screen
