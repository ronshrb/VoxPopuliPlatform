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
    projects = dbs.get_projects()
    researcher_projects = [p for p in projects if p['LeadResearcher'] == researcher_id]
    return researcher_projects


def researcher_app(email):
    """Main function for the Researcher Dashboard."""
    # Find user by email
    user_data = dbs.get_user_by_email(email)

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
    username = user_data['Username']
    userid = user_data['UserID']

    # Get the projects where this researcher is the lead
    researcher_projects = get_researcher_projects(userid)

    # Page title
    st.title("Researcher Dashboard")
    st.sidebar.success(f"Welcome, {username}!")

    if not researcher_projects:
        st.warning("You are not currently assigned as a lead researcher for any projects.")
        st.info("Please contact the administrator to be assigned to a project.")
        return

    # Sidebar with options
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["Project Selection", "Project Overview", "Chat Analysis", "User Management", "Data Export"]
    )
    st.sidebar.success(f"Welcome, {username}!")
    # Get researcher's projects for selection
    project_options = [p['ProjectName'] for p in researcher_projects]
    projects_dict = {p['ProjectName']: p['ProjectID'] for p in researcher_projects}

    # Project Selection Screen
    if menu == "Project Selection":
        st.header("Your Research Projects")
        st.markdown("Select a project to manage:")

        # Create project cards
        cols = st.columns(min(3, len(project_options)))

        for i, project_name in enumerate(project_options):
            project_id = projects_dict[project_name]
            project_details = next(p for p in researcher_projects if p['ProjectID'] == project_id)

            with cols[i % len(cols)]:
                st.markdown(f"""
                <div style="
                    padding: 20px;
                    border-radius: 10px;
                    border: 1px solid #ddd;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <h3>{project_name}</h3>
                    <p><strong>Status:</strong> {project_details['Status']}</p>
                    <p><strong>Started:</strong> {project_details['StartDate']}</p>
                </div>
                """, unsafe_allow_html=True)

                # Count project chats
                project_chats = dbs.get_project_chats(project_id)

                # Summary metrics
                st.metric("Chats", len(project_chats))

                # Button to open project
                if st.button(f"Open {project_name}", key=f"open_{project_id}"):
                    st.session_state["selected_project"] = project_id
                    st.session_state["selected_project_name"] = project_name
                    st.rerun()

    # Store selected project in session state
    if "selected_project" not in st.session_state and menu != "Project Selection":
        st.session_state["selected_project"] = projects_dict[project_options[0]]
        st.session_state["selected_project_name"] = project_options[0]

    # Project Overview Screen
    elif menu == "Project Overview":
        if "selected_project" not in st.session_state:
            st.warning("Please select a project first")
            st.rerun()

        project_id = st.session_state["selected_project"]
        project_name = st.session_state["selected_project_name"]

        # Allow changing projects
        new_project = st.selectbox(
            "Select Project",
            project_options,
            index=project_options.index(project_name),
            key="change_project"
        )

        if new_project != project_name:
            st.session_state["selected_project"] = projects_dict[new_project]
            st.session_state["selected_project_name"] = new_project
            st.rerun()

        selected_project = next(p for p in researcher_projects if p['ProjectID'] == project_id)

        # Display project info
        st.header(f"Dashboard for {project_name}")

        # Project details
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Project ID:** {project_id}")
            st.markdown(f"**Status:** {selected_project['Status']}")
            st.markdown(f"**Start Date:** {selected_project['StartDate']}")

        with col2:
            st.markdown(f"**Lead Researcher:** {username} (You)")

            # Count project chats
            project_chats = dbs.get_project_chats(project_id)
            st.markdown(f"**Number of Chats:** {len(project_chats)}")

            # Count unique users
            unique_users = len(set(chat['UserID'] for chat in project_chats))
            st.markdown(f"**Number of Users:** {unique_users}")

        st.markdown("---")

        # Analytics section
        st.subheader("Project Analytics")

        # Display sentiment distribution
        st.markdown("#### Sentiment Analysis")
        sentiment_fig = plot_sentiment_distribution(project_id)
        if sentiment_fig:
            st.pyplot(sentiment_fig)
        else:
            st.info("No sentiment data available for this project.")

        # Display chat activity
        st.markdown("#### Chat Activity Over Time")
        activity_fig = plot_chat_activity(project_id)
        if activity_fig:
            st.pyplot(activity_fig)
        else:
            st.info("No activity data available for this project.")

    # Additional menu options (Chat Analysis, User Management, Data Export) can be updated similarly
    elif menu == "User Management":
        st.header("User Management")
        st.markdown("Manage users in your project.")

        # Get the selected project
        project_id = st.session_state["selected_project"]
        project_name = st.session_state["selected_project_name"]

        # Fetch users in the project
        project_users = [user for user in dbs.get_users() if user['ProjectID'] == project_id]

        # Display users in the project
        st.subheader(f"Users in Project: {project_name}")
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
                            active=active,
                            project_id=project_id
                        )
                        st.success(f"User {username} registered successfully!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error registering user: {str(e)}")