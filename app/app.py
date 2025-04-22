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


# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["email"] = None
    st.session_state["registration_mode"] = False
    st.session_state["registration_success"] = False
    st.session_state["registered_role"] = None
    # st.session_state["debug_mode"] = False


# # Debug function to display dataframe
# def display_debug_info():
#     with st.expander("Debug Information"):
#         st.write("Current Users in Database:")
#         st.dataframe(dbs.get_users_df(), use_container_width=True)
#         st.write(f"Number of users: {len(dbs.get_users_df())}")

#         # Display role information for each user
#         st.write("User Roles:")
#         for idx, row in dbs.get_users_df().iterrows():
#             st.write(f"- {row['Email']} ({row['Role']})")

#         # Show specific columns with specific formats
#         st.write("User Emails:")
#         for email in dbs.get_users_df()['Email']:
#             st.write(f"- {email} (type: {type(email)})")

#         # Show projects and their lead researchers
#         st.write("Projects and Lead Researchers:")
#         projects_df = dbs.get_projects_df()
#         for idx, row in projects_df.iterrows():
#             researcher_id = row['LeadResearcher']
#             researcher = dbs.get_users_df()[dbs.get_users_df()['UserID'] == researcher_id]
#             researcher_email = researcher['Email'].iloc[0] if not researcher.empty else "Unknown"
#             st.write(f"- {row['ProjectName']} (ID: {row['ProjectID']}) - Lead: {researcher_id} ({researcher_email})")

#         # Show projects
#         st.write("Projects:")
#         st.dataframe(dbs.get_projects_df(), use_container_width=True)

#         # Show sample chats
#         st.write("Sample Chats (first 10):")
#         st.dataframe(dbs.get_chats_df().head(10), use_container_width=True)

#         # Show sample messages
#         st.write("Sample Messages (first 10):")
#         st.dataframe(dbs.get_messages_df().head(10), use_container_width=True)

#         st.write("Session State:")
#         st.write(st.session_state)


# Main app
# if st.session_state["registration_mode"]:
#     # Call the registration page function
#     register_page()
if not st.session_state["logged_in"]:
    # Login header
    st.markdown("<h1 class='main-header'>Welcome to VoxPopuli 🗣️</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Collaborative Research Platform for Voice and Opinion Analysis</p>",
                unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>By: Amit Cohen, Eren Fishbein, Roey Fabian, Ron Sharabi</p>",
            unsafe_allow_html=True)

    # Create two columns for layout
    col1, spacer, col2 = st.columns([0.8, 0.2, 1])

    # Column 1: Login Form
    with col1:
        # st.markdown("<div class='login-container'>", unsafe_allow_html=True)

        # Role selection and login
        role = st.selectbox("Select Role", ["User", "Researcher"], key="role_select")

        # Set default email and password to blank when first entering the site
        email = st.text_input("Email", key="email_input", value="")
        password = st.text_input("Password", type="password", key="password_input", value="")

        # Login button
        if st.button("Login", key="login_button"):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                # Find user by email - using case-insensitive comparison
                user_data = dbs.get_user_by_email(email)

                if user_data:
                    # Get the stored hash from the database
                    stored_hashed_password = user_data['HashedPassword']
                    user_role = user_data['Role']

                    # Check if role matches
                    if role != user_role:
                        st.error(f"This email is registered as a {user_role}, not a {role}.")
                    else:
                        try:
                            # Check if the provided password matches the hashed password
                            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                                # Login successful for both user and researcher roles
                                st.session_state["logged_in"] = True
                                st.session_state["role"] = user_role
                                st.session_state["email"] = user_data['Email']
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid password.")
                        except Exception as e:
                            st.error(f"Login error: {str(e)}")
                else:
                    st.error("User not found. Please check your email or register.")

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
        user_app(st.session_state["email"])
    elif st.session_state["role"] == "Researcher":
        researcher_app(st.session_state["email"])

    # Optional logout button in sidebar
    if st.sidebar.button("Logout", key="main_logout"):
        st.session_state["logged_in"] = False
        st.session_state["role"] = None
        st.session_state["email"] = None
        st.rerun()