import bcrypt
import streamlit as st
import dbs
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from web_monitor import WebMonitor
import asyncio



def register_user(username, password):
    """Register a new user in the database."""
    # Check if the username already exists
    users = dbs.get_users()

    # Check if the username already exists
    if any(u['Username'].lower() == username.lower() for u in users):
        st.error("Username already exists.")
        return False

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Add the user to the database
    dbs.add_user(username, hashed_password, role="User", active=True)

    st.success(f"User {username} registered successfully.")
    return True


def plot_sentiment_distribution(project_id):
    """Generate a plot showing sentiment distribution for a project's messages."""
    # Get chats for the project
    project_chats = dbs.get_project_chats(project_id)

    if not project_chats:
        return None

    # Collect all messages from these chats
    chat_ids = [chat['ChatID'] for chat in project_chats]
    project_messages = dbs.get_messages_by_chat_ids(chat_ids)

    if not project_messages:
        return None

    # Count sentiments
    sentiment_counts = pd.DataFrame(project_messages)['Sentiment'].value_counts()

    # Create a figure
    fig, ax = plt.subplots(figsize=(8, 5))
    sentiment_counts.plot(kind='bar', ax=ax, color=['#5cb85c', '#d9534f', '#5bc0de', '#f0ad4e'])
    ax.set_title(f'Sentiment Distribution for Project {project_id}')
    ax.set_ylabel('Number of Messages')
    ax.set_xlabel('Sentiment')

    # Return the figure
    return fig


def plot_chat_activity(project_id):
    """Generate a plot showing chat activity over time for a project."""
    # Get chats for the project
    project_chats = dbs.get_project_chats(project_id)

    if not project_chats:
        return None

    # Collect all messages from these chats
    chat_ids = [chat['ChatID'] for chat in project_chats]
    project_messages = dbs.get_messages_by_chat_ids(chat_ids)

    if not project_messages:
        return None

    # Convert timestamps to datetime
    messages_df = pd.DataFrame(project_messages)
    messages_df['Timestamp'] = pd.to_datetime(messages_df['Timestamp'])

    # Group by date and count messages
    daily_activity = messages_df.groupby(messages_df['Timestamp'].dt.date).size()

    # Create a figure
    fig, ax = plt.subplots(figsize=(10, 6))
    daily_activity.plot(kind='line', ax=ax, marker='o', linestyle='-', color='#337ab7')
    ax.set_title(f'Chat Activity Over Time for Project {project_id}')
    ax.set_ylabel('Number of Messages')
    ax.set_xlabel('Date')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Return the figure
    return fig


def get_researcher_projects(researcher_id):
    """Get projects where the researcher is the lead."""
    # projects = dbs.get_projects()
    # researcher_projects = [p for p in projects if p['LeadResearcher'] == researcher_id]
    # return researcher_projects
    



def researcher_app(userid, tables_dict):
    """Main function for the Researcher Dashboard."""
    # Find user by email
    chats, users, projects, user_projects, chats_projects, chats_blacklist = (
        tables_dict["Chats"],
        tables_dict["Users"],
        tables_dict["Projects"],
        tables_dict["UserProjects"],
        tables_dict["ChatsProjects"],
        tables_dict["ChatsBlacklist"],
    )
    user_data = users.get_user_by_id(userid)

    if not user_data:
        st.error(f"User with username {userid} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="researcher_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["user"] = None
            st.rerun()
        return

    # Get user information
    # userid = user_data['UserID']
    users_projects = projects.get_projects_by_researcher(userid)

    # # Get the projects where this researcher is the lead
    # researcher_projects = get_researcher_projects(userid)
    # Page title
    st.title("Researcher Dashboard")

    if not users_projects:
        st.warning("You are not currently assigned as a lead researcher for any projects.")
        st.info("Please contact the administrator to be assigned to a project.")
        return
    
    # projects_by_name = {record['ProjectName']: record for record in users_projects}
    projects_by_id = {record['ProjectID']: record for record in users_projects}
    projects_by_name = projects_by_id

    project_names = list(projects_by_name.keys()) if projects_by_name else []


    st.sidebar.success(f"Welcome, {userid}!")

    # Sidebar: Select Project
    st.sidebar.header("Select a Project")

    # Build project_id to name mapping for selectbox
    project_id_to_name = {pid: info['ProjectName'] for pid, info in projects_by_id.items()}
    project_ids = list(project_id_to_name.keys())
    project_names = [project_id_to_name[pid] for pid in project_ids]

    # Default project selection
    if "selected_project_id" not in st.session_state:
        st.session_state["selected_project_id"] = project_ids[0]

    # Selectbox for project selection by name
    selected_project_name = st.sidebar.selectbox(
        "Project",
        project_names,
        index=project_names.index(project_id_to_name[st.session_state["selected_project_id"]]),
        key="sidebar_project_select"
    )
    # Map back to project_id
    selected_project_id = [pid for pid, name in project_id_to_name.items() if name == selected_project_name][0]
    st.session_state["selected_project_id"] = selected_project_id

    # Initialize messages_coll for the selected project
    messages_coll = dbs.MessagesColl(selected_project_id)

    # Sidebar menu
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["Project Analytics", "Chat Analysis", "User Management", "Project Creation", "Data Export"]
    )

    # Project Analytics Page (Blank)
    if menu == "Project Analytics":
        st.header("Project Analytics")
        st.markdown("This page is under construction.")
        st.dataframe(messages_coll.get_chats_info(), use_container_width=True, hide_index=True)

    # Chat Analysis Page
    elif menu == "Chat Analysis":
        st.header("Chat Analysis")
        st.markdown("Analyze chats for the selected project.")
        st.dataframe(messages_coll.get_chats_info(), use_container_width=True)

    # User Management Page
    elif menu == "User Management":
        st.header("User Management")
        st.markdown("Manage users in your project.")

        tab1, tab2 = st.tabs(["Project's Users", "Register New User"])

        with tab1:
            # Fetch users in the project
            project_users = user_projects.get_projects_users(selected_project_id)
            users_data = users.get_users_by_ids(project_users)

            # Display users in the project
            st.subheader("Users in Project")
            if not project_users:
                st.info("No users are currently registered in this project.")
            else:
                users_df = pd.DataFrame(users_data)
                st.dataframe(users_df[['UserID', 'Role', 'Creator', 'Active', 'CreatedAt']])


        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                # Form to register a new user
                st.subheader("Register a New User")
                with st.form("register_user_form"):
                    # Input fields for registration
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    server_url = "https://vox-populi.dev"
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    # Register button
                    submit_button = st.form_submit_button("Register")
                    if submit_button:
                        if not username or not password or not confirm_password:
                            st.error("Please fill in all fields.")
                        elif password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            # Run the registration process
                            with st.spinner("Registering user..."):
                                try:
                                    # Create a WebMonitor instance with consistent server URL
                                    server_url = "http://vox-populi.dev:8008"  # Use this URL consistently
                                    web_monitor = WebMonitor(
                                        username=username, 
                                        password=password,
                                        server_url=server_url
                                    )
                                    # Properly await the async register method
                                    result = asyncio.run(web_monitor.register())
                                    if result:
                                        users.add_user(
                                            user_id=username, 
                                            hashed_password=hashed_password,
                                            creator_id=userid, 
                                            role="User",
                                            active=True,
                                        )
                                        user_projects.add_user_to_project(
                                            user_id=username, 
                                            project_id=selected_project_id
                                        )
                                        st.success(f"User {username} registered successfully!")
                                        # st.info(f"When logging in, use server URL: {server_url}")
                                    else:
                                        st.error("Registration failed. Username might already exist.")
                                except Exception as e:
                                    st.error(f"Registration error: {str(e)}")
           

    # Project Creation Page (Blank)
    elif menu == "Project Creation":
        st.header("Project Creation")
        st.markdown("This page is under construction.")

    # Data Export Page
    elif menu == "Data Export":
        st.header("Data Export")
        st.markdown("Export project data.")