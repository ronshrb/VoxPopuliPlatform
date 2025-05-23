import bcrypt
import streamlit as st
import dbs
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime



def register_user(username, email, password):
    """Register a new user in the database."""
    # Check if the username already exists
    users = dbs.get_users()

    # Check if the username already exists
    if any(u['Username'].lower() == username.lower() for u in users):
        st.error("Username already exists.")
        return False

    # Check if the email already exists
    if any(u['Email'].lower() == email.lower() for u in users):
        st.error("Email already in use.")
        return False

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Add the user to the database
    dbs.add_user(email, username, hashed_password, role="User", active=True)

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
    



def researcher_app(email, users, projects):
    """Main function for the Researcher Dashboard."""
    # Find user by email
    user_data = users.get_user_by_email(email)

    if not user_data:
        st.error(f"User with email {email} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="researcher_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["email"] = None
            st.rerun()
        return

    # Get user information
    userid = user_data['UserID']
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

    # Default project selection
    if "selected_project" not in st.session_state:  # taking the first one by default
        st.session_state["selected_project"] = projects_by_name[project_names[0]]
        st.session_state["selected_project_name"] = project_names[0]

    # Allow changing projects
    selected_project_name = st.sidebar.selectbox(
        "Project",
        project_names,
        index=project_names.index(st.session_state["selected_project_name"]),
        key="sidebar_project_select"
    )

    # Update session state if the project changes
    if selected_project_name != st.session_state["selected_project_name"]:
        st.session_state["selected_project"] = projects_by_name[selected_project_name]
        st.session_state["selected_project_name"] = selected_project_name
        st.rerun()

    # Display selected project information in the sidebar
    selected_project_id = st.session_state["selected_project"]['ProjectID']
    # selected_project = next(p for p in projects_by_name.keys() if projects_by_name[p] == selected_project_id)
    messages_coll = dbs.MessagesColl(selected_project_id)
    st.sidebar.markdown("### Project Information")
    st.sidebar.markdown(f"**Project Name:** {selected_project_name}")
    st.sidebar.markdown(f"**Project ID:** {selected_project_id}")
    # st.sidebar.markdown(f"**Status:** {selected_project['Status']}")
    # st.sidebar.markdown(f"**Start Date:** {selected_project['StartDate']}")")

    # Sidebar menu
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["Project Analytics", "Chat Analysis", "User Management", "Project Creation", "Data Export"]
    )

    # Project Analytics Page (Blank)
    if menu == "Project Analytics":
        st.header("Project Analytics")
        st.markdown("This page is under construction.")

    # Chat Analysis Page
    elif menu == "Chat Analysis":
        st.header("Chat Analysis")
        st.markdown("Analyze chats for the selected project.")
        st.dataframe(messages_coll.get_chats_info(), use_container_width=True)

    # User Management Page
    elif menu == "User Management":
        st.header("User Management")
        st.markdown("Manage users in your project.")

        # Fetch users in the project
        project_users = dbs.get_users()

        # Display users in the project
        st.subheader(f"Users in Project: {selected_project_name}")
        if not project_users:
            st.info("No users are currently registered in this project.")
        else:
            users_df = pd.DataFrame(project_users)
            st.dataframe(users_df[['UserID', 'Username', 'Email', 'Role', 'Active', 'CreatedAt']])

        st.markdown("---")

        # Form to register a new user
        st.subheader("Register a New User")
        with st.form("register_user_form"):
            username = st.text_input("Username", key="new_user_username")
            email = st.text_input("Email", key="new_user_email")
            password = st.text_input("Password", type="password", key="new_user_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="new_user_confirm_password")
            role = st.selectbox("Role", ["User", "Researcher"], key="new_user_role")
            active = st.checkbox("Active", value=True, key="new_user_active")

            submit_button = st.form_submit_button("Register User")

            if submit_button:
                if not username or not email or not password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    # Hash the password
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                    # Add the user to the database
                    try:
                        dbs.add_user(
                            email=email,
                            username=username,
                            hashed_password=hashed_password,
                            role=role,
                            active=active
                        )
                        st.success(f"User {username} registered successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error registering user: {str(e)}")

    # Project Creation Page (Blank)
    elif menu == "Project Creation":
        st.header("Project Creation")
        st.markdown("This page is under construction.")

    # Data Export Page
    elif menu == "Data Export":
        st.header("Data Export")
        st.markdown("Export project data.")