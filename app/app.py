import streamlit as st

# Set page configuration - this MUST be the first Streamlit command
st.set_page_config(
    page_title="VoxPopuli Research Platform",
    page_icon="🗣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import other modules AFTER page config
import bcrypt
import pandas as pd
from user_app import user_app
from researcher_app import researcher_app
# from register_app import register_page
import dbs


# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4b7bec;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #718093;
        text-align: center;
        margin-bottom: 2rem;
    }
    .credits {
        font-size: 1rem;
        color: #718093;
        text-align: center;
        margin-bottom: 3rem;
    }   
    .login-container {
        max-width: 600px;
        margin: 0 auto;
        padding: 2rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton button {
        width: 100%;
    }
    .role-button {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

db_name = "VoxPopuli" # change to your database name

tables_dict = {
    "Users": dbs.UsersTable(),
    "Projects": dbs.ProjectsTable(),
    "Chats": dbs.ChatsTable(),
    "UserProjects": dbs.UserProjectsTable(),
    "ChatsProjects": dbs.ChatProjectsTable(),
    "ChatsBlacklist": dbs.ChatsBlacklistTable(),
}

users, projects, chats, user_projects, chats_projects, chats_blacklist = (
    tables_dict["Users"],
    tables_dict["Projects"],
    tables_dict["Chats"],
    tables_dict["UserProjects"],
    tables_dict["ChatsProjects"],
    tables_dict["ChatsBlacklist"],
)

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user"] = None
    st.session_state["registration_mode"] = False
    st.session_state["registration_success"] = False
    st.session_state["registered_role"] = None
    # st.session_state["debug_mode"] = False

# Main app

if not st.session_state["logged_in"]:
    # Login header
    st.markdown("<h1 class='main-header'>Welcome to VoxPopuli 🗣️</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Collaborative Research Platform for Voice and Opinion Analysis</p>",
                unsafe_allow_html=True)
    st.markdown("<p class='credits'>By: Amit Cohen, Eren Fishbein, Roey Fabian, Ron Sharabi</p>",
            unsafe_allow_html=True)

    # Create two columns for layout
    col1, spacer, col2 = st.columns([0.8, 0.2, 1])

    # Column 1: Login Form
    with col1:
        # st.markdown("<div class='login-container'>", unsafe_allow_html=True)

        # Role selection and login
        role = st.selectbox("Select Role", ["User", "Researcher"], key="role_select")

        # Set default user and password to blank when first entering the site
        userid = st.text_input("Username", key="userid_input", value="")
        password = st.text_input("Password", type="password", key="password_input", value="")

        # Login button
        if st.button("Login", key="login_button"):
            if not userid or not password:
                st.error("Please enter both Username and password.")
            else:
                # Find user by user - using case-insensitive comparison
                user_data = users.get_user_by_id(userid)


                if user_data:
                    # Get the stored hash from the database
                    stored_hashed_password = user_data['HashedPassword']
                    user_role = user_data['Role']
                    # Check if role matches
                    if role != user_role:
                        st.error(f"This user is registered as a {user_role}, not a {role}.")
                    else:
                        try:
                            # Check if the provided password matches the hashed password
                            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                                # Login successful for both user and researcher roles
                                st.session_state["logged_in"] = True
                                st.session_state["role"] = user_role
                                st.session_state["user"] = user_data['UserID']
                                st.session_state['password'] = password
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid password.")
                        except Exception as e:
                            st.error(f"Login error: {str(e)}")
                else:
                    st.error("User not found. Please check your username or register.")

        # st.markdown("</div>", unsafe_allow_html=True)

    # Column 2: Platform Information
    with col2:
        st.markdown("### About VoxPopuli")
        st.markdown("""
        VoxPopuli is a platform for collaborative research projects focusing on:
        - Opinion analysis
        - Voice and language processing
        - Sentiment analysis
        - User behavior studies

        Join our community to contribute to important research initiatives.
        """)

        st.markdown("### Features")
        st.markdown("""
        - Participate in research conversations
        - Donate your chat data for research
        - Track your contributions
        - Connect with researchers
        - Generate insights from collective opinions
        """)

else:
    # Redirect to the appropriate app based on role
    if st.session_state["role"] == "User":
        user_app(st.session_state["user"], tables_dict, st.session_state['password'])
    elif st.session_state["role"] == "Researcher":
        researcher_app(st.session_state["user"], tables_dict)

    # Optional logout button in sidebar
    if st.sidebar.button("Logout", key="main_logout"):
        st.session_state["logged_in"] = False
        st.session_state["role"] = None
        st.session_state["user"] = None
        st.rerun()