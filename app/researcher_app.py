import pandas as pd
import bcrypt
import streamlit as st
import dbs
import matplotlib.pyplot as plt
import io
import base64
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta


def register_user(username, email, password):
    # Check if the username already exists
    users_df = dbs.get_users_df()

    # Check if the username already exists
    if username in users_df['Username'].values:
        st.error("Username already exists.")
        return False

    # Check if the email already exists
    if email in users_df['Email'].values:
        st.error("Email already in use.")
        return False

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Generate a new user ID
    if len(users_df) == 0:
        new_user_id = "user1"
    else:
        # Extract the numeric part of the last user ID and increment it
        last_id = users_df['UserID'].iloc[-1]
        numeric_part = int(''.join(filter(str.isdigit, last_id)))
        new_user_id = f"user{numeric_part + 1}"

    # Add new user to the DataFrame
    new_user = {
        'UserID': new_user_id,
        'Email': email,
        'Username': username,
        'HashedPassword': hashed_password,
        'Role': 'User',  # Default role is User
        'Active?': True,
        'Registration Date': datetime.now().strftime('%Y-%m-%d')
    }

    # Add user to database
    dbs.add_user(new_user)

    st.success(f"User {username} registered successfully.")
    return True


def plot_sentiment_distribution(project_id):
    """Generate a plot showing sentiment distribution for a project's messages."""
    # Get chats for the project
    project_chats = dbs.get_project_chats(project_id)

    if project_chats.empty:
        return None

    # Collect all messages from these chats
    messages_df = dbs.get_messages_df()
    project_messages = messages_df[messages_df['ChatID'].isin(project_chats['ChatID'])]

    if project_messages.empty:
        return None

    # Count sentiments
    sentiment_counts = project_messages['Sentiment'].value_counts()

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

    if project_chats.empty:
        return None

    # Collect all messages from these chats
    messages_df = dbs.get_messages_df()
    project_messages = messages_df[messages_df['ChatID'].isin(project_chats['ChatID'])]

    if project_messages.empty:
        return None

    # Convert timestamp to datetime
    project_messages['Timestamp'] = pd.to_datetime(project_messages['Timestamp'])

    # Group by date and count messages
    daily_activity = project_messages.groupby(project_messages['Timestamp'].dt.date).size()

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
    projects_df = dbs.get_projects_df()
    researcher_projects = projects_df[projects_df['LeadResearcher'] == researcher_id]
    return researcher_projects


def researcher_app(email):
    # Find user by email
    user_matches = dbs.get_user_by_email(email)

    if user_matches.empty:
        st.error(f"User with email {email} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="researcher_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["email"] = None
            st.rerun()
        return

    # Get user information
    username = user_matches['Username'].values[0]
    userid = user_matches['UserID'].values[0]

    # Get all users and other dataframes we'll need
    users_df = dbs.get_users_df()

    # Get the projects where this researcher is the lead
    researcher_projects = get_researcher_projects(userid)

    # Page title
    st.title("Researcher Dashboard")
    st.success(f"Welcome, {username}!")

    if researcher_projects.empty:
        st.warning("You are not currently assigned as a lead researcher for any projects.")
        st.info("Please contact the administrator to be assigned to a project.")
        return

    # Sidebar with options
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["Project Selection", "Project Overview", "Chat Analysis", "User Management", "Data Export"]
    )

    # Get researcher's projects for selection
    project_options = researcher_projects['ProjectName'].tolist()
    projects_dict = dict(zip(researcher_projects['ProjectName'], researcher_projects['ProjectID']))

    # Project Selection Screen
    if menu == "Project Selection":
        st.header("Your Research Projects")
        st.markdown("Select a project to manage:")

        # Create project cards
        cols = st.columns(min(3, len(project_options)))

        for i, project_name in enumerate(project_options):
            project_id = projects_dict[project_name]
            project_details = researcher_projects[researcher_projects['ProjectID'] == project_id]

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
                    <p><strong>Status:</strong> {project_details['Status'].values[0]}</p>
                    <p><strong>Started:</strong> {project_details['StartDate'].values[0]}</p>
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

        selected_project = researcher_projects[researcher_projects['ProjectID'] == project_id]

        # Display project info
        st.header(f"Dashboard for {project_name}")

        # Project details
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Project ID:** {project_id}")
            st.markdown(f"**Status:** {selected_project['Status'].values[0]}")
            st.markdown(f"**Start Date:** {selected_project['StartDate'].values[0]}")

        with col2:
            st.markdown(f"**Lead Researcher:** {username} (You)")

            # Count project chats
            project_chats = dbs.get_project_chats(project_id)
            st.markdown(f"**Number of Chats:** {len(project_chats)}")

            # Count unique users
            unique_users = project_chats['UserID'].nunique()
            st.markdown(f"**Number of Users:** {unique_users}")

        st.markdown("---")

        # Analytics section
        st.subheader("Project Analytics")

        # Chat topic distribution
        st.markdown("#### Chat Topic Distribution")
        topic_distribution = {}
        for chat_name in project_chats['ChatName']:
            topic = chat_name.replace("Chat about ", "")
            if topic in topic_distribution:
                topic_distribution[topic] += 1
            else:
                topic_distribution[topic] = 1

        # Create a DataFrame for the chart
        topic_df = pd.DataFrame({
            'Topic': topic_distribution.keys(),
            'Count': topic_distribution.values()
        }).sort_values('Count', ascending=False)

        # Display chart
        st.bar_chart(topic_df.set_index('Topic'))

        # Donated vs Non-donated chats
        donated_counts = project_chats['Donated?'].value_counts()

        st.markdown("#### Donation Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Donated Chats", donated_counts.get(True, 0))
        with col2:
            st.metric("Non-donated Chats", donated_counts.get(False, 0))

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

    elif menu == "Chat Analysis":
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
            key="change_project_chat"
        )

        if new_project != project_name:
            st.session_state["selected_project"] = projects_dict[new_project]
            st.session_state["selected_project_name"] = new_project
            st.rerun()

        st.header(f"Chat Analysis: {project_name}")

        # Get chats for this project
        project_chats = dbs.get_project_chats(project_id)

        if not project_chats.empty:
            # Chat filters
            st.subheader("Filter Chats")

            col1, col2 = st.columns(2)
            with col1:
                donated_filter = st.selectbox(
                    "Donation Status",
                    ["All", "Donated", "Not Donated"],
                    key="chat_donated_filter"
                )

            with col2:
                search_term = st.text_input("Search by Chat Name", key="chat_search")

            # Apply filters
            filtered_chats = project_chats

            if donated_filter == "Donated":
                filtered_chats = filtered_chats[filtered_chats['Donated?'] == True]
            elif donated_filter == "Not Donated":
                filtered_chats = filtered_chats[filtered_chats['Donated?'] == False]

            if search_term:
                filtered_chats = filtered_chats[filtered_chats['ChatName'].str.contains(search_term, case=False)]

            # Display filtered chats
            st.subheader(f"Chats ({len(filtered_chats)})")

            if not filtered_chats.empty:
                for _, chat in filtered_chats.iterrows():
                    with st.expander(f"{chat['ChatName']} ({chat['ChatID']})"):
                        st.markdown(f"**Description:** {chat['ChatDescription']}")
                        st.markdown(f"**User ID:** {chat['UserID']}")
                        st.markdown(f"**Messages:** {chat['Total Messages']}")
                        st.markdown(f"**Started:** {chat['Start Date']}")
                        st.markdown(f"**Last Updated:** {chat['Last Updated']}")
                        st.markdown(f"**Donated:** {'Yes' if chat['Donated?'] else 'No'}")

                        # Get chat messages
                        chat_messages = dbs.get_chat_messages(chat['ChatID'])

                        if not chat_messages.empty:
                            st.markdown("#### Chat Messages")
                            for _, msg in chat_messages.iterrows():
                                st.markdown(f"**{msg['Timestamp']}** - {msg['Message']} _{msg['Sentiment']}_")
                        else:
                            st.info("No messages found for this chat.")
            else:
                st.info("No chats match your filter criteria.")
        else:
            st.info(f"No chats found for project {project_name}.")

    elif menu == "User Management":
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
            key="change_project_users"
        )

        if new_project != project_name:
            st.session_state["selected_project"] = projects_dict[new_project]
            st.session_state["selected_project_name"] = new_project
            st.rerun()

        st.header(f"User Management: {project_name}")

        # Get users involved in this project
        project_chats = dbs.get_project_chats(project_id)
        project_user_ids = project_chats['UserID'].unique() if not project_chats.empty else []
        project_users = users_df[users_df['UserID'].isin(project_user_ids)]

        # User statistics for this project
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Project Users", len(project_users))
        with col2:
            st.metric("Active Users", project_users['Active?'].sum() if not project_users.empty else 0)

        # User registration over time (for this project's users)
        if 'Registration Date' in users_df.columns and not project_users.empty:
            st.subheader("User Registration Over Time")
            project_users['Registration Date'] = pd.to_datetime(project_users['Registration Date'])
            registrations_by_day = project_users.groupby(project_users['Registration Date'].dt.date).size()

            # Plot registration trend
            fig, ax = plt.subplots(figsize=(10, 6))
            registrations_by_day.plot(kind='line', ax=ax, marker='o', linestyle='-', color='green')
            ax.set_title(f'User Registrations Over Time for {project_name}')
            ax.set_ylabel('Number of New Users')
            ax.set_xlabel('Date')
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)

        # Register new user section
        st.subheader("Register New User for This Project")
        with st.form(key="register_user_form"):
            username_input = st.text_input("Username", key="reg_username")
            email_input = st.text_input("Email", key="reg_email")
            password_input = st.text_input("Password", type="password", key="reg_password")
            submit_button = st.form_submit_button(label="Register User")

            if submit_button:
                if username_input and email_input and password_input:
                    if register_user(username_input, email_input, password_input):
                        st.success(f"User {username_input} has been registered.")

                        # After registering, create a welcome chat for this user in the current project
                        # This helps associate the user with this project immediately
                        users_df = dbs.get_users_df()  # Get updated user list
                        new_user = users_df[users_df['Email'] == email_input]

                        if not new_user.empty:
                            new_user_id = new_user['UserID'].values[0]

                            # Create a welcome chat
                            new_chat = {
                                'UserID': new_user_id,
                                'ChatID': f"chat{len(dbs.get_chats_df()) + 1}",
                                'ChatName': f"Welcome to {project_name}",
                                'ChatDescription': f"Initial chat for {project_name} project",
                                'Total Messages': 0,
                                'Donated?': False,
                                'Start Date': datetime.now().strftime('%Y-%m-%d'),
                                'Last Updated': datetime.now().strftime('%Y-%m-%d'),
                                'Project ID': project_id
                            }
                            dbs.add_chat(new_chat)
                else:
                    st.error("Please fill out all fields.")

        # Project user search
        st.subheader("Project Users")
        search_query = st.text_input("Search by Username or Email", key="user_search")

        if search_query:
            # Search by username or email within project users
            matching_users = project_users[
                project_users['Username'].str.contains(search_query, case=False) |
                project_users['Email'].str.contains(search_query, case=False)
                ]

            if not matching_users.empty:
                st.dataframe(
                    matching_users[['UserID', 'Username', 'Email', 'Role', 'Active?', 'Registration Date']],
                    use_container_width=True
                )
            else:
                st.info("No users found matching your search criteria.")
        else:
            # Show all project users
            if not project_users.empty:
                st.dataframe(
                    project_users[['UserID', 'Username', 'Email', 'Role', 'Active?', 'Registration Date']],
                    use_container_width=True
                )
            else:
                st.info("No users are currently part of this project.")

    elif menu == "Data Export":
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
            key="change_project_export"
        )

        if new_project != project_name:
            st.session_state["selected_project"] = projects_dict[new_project]
            st.session_state["selected_project_name"] = new_project
            st.rerun()

        st.header(f"Data Export: {project_name}")

        # Get project data
        project_chats = dbs.get_project_chats(project_id)

        st.subheader("Export Options")

        export_format = st.radio("Export Format", ["CSV", "Excel"], horizontal=True)

        export_content = st.multiselect(
            "Export Content",
            ["Chats", "Users", "Messages", "All"],
            default=["All"]
        )

        if st.button("Export Data"):
            # Prepare data for export
            export_data = {}

            if "All" in export_content or "Chats" in export_content:
                export_data["chats"] = project_chats

            if "All" in export_content or "Users" in export_content:
                if not project_chats.empty:
                    # Get users involved in this project
                    project_users = users_df[users_df['UserID'].isin(project_chats['UserID'])]
                    export_data["users"] = project_users[
                        ['UserID', 'Username', 'Email', 'Role', 'Registration Date']]

            if "All" in export_content or "Messages" in export_content:
                if not project_chats.empty:
                    # Get messages from this project's chats
                    messages_df = dbs.get_messages_df()
                    project_messages = messages_df[messages_df['ChatID'].isin(project_chats['ChatID'])]
                    export_data["messages"] = project_messages

            # Perform export
            if export_format == "CSV":
                # Create a zip file in memory
                import io
                import zipfile

                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, 'w') as zip_file:
                    for name, df in export_data.items():
                        if not df.empty:
                            csv_buffer = io.StringIO()
                            df.to_csv(csv_buffer, index=False)
                            zip_file.writestr(f"{project_id}_{name}.csv", csv_buffer.getvalue())

                buffer.seek(0)

                # Create download button
                st.download_button(
                    label="Download ZIP with CSVs",
                    data=buffer,
                    file_name=f"{project_id}_export.zip",
                    mime="application/zip"
                )

                st.success("Data ready for download!")

            elif export_format == "Excel":
                # Create Excel file in memory with multiple sheets
                import io

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    for name, df in export_data.items():
                        if not df.empty:
                            df.to_excel(writer, sheet_name=name, index=False)

                buffer.seek(0)

                # Create download button
                st.download_button(
                    label="Download Excel File",
                    data=buffer,
                    file_name=f"{project_id}_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.success("Data ready for download!")

        # Additional data insights
        st.subheader("Data Insights")

        # Preview project data
        if st.checkbox("Preview Project Data"):
            tab1, tab2, tab3 = st.tabs(["Chats", "Users", "Messages"])

            with tab1:
                st.dataframe(project_chats, use_container_width=True)

            with tab2:
                if not project_chats.empty:
                    project_users = users_df[users_df['UserID'].isin(project_chats['UserID'])]
                    st.dataframe(project_users[['UserID', 'Username', 'Email', 'Role']], use_container_width=True)
                else:
                    st.info("No users found for this project.")

            with tab3:
                if not project_chats.empty:
                    messages_df = dbs.get_messages_df()
                    project_messages = messages_df[messages_df['ChatID'].isin(project_chats['ChatID'])]
                    if not project_messages.empty:
                        st.dataframe(project_messages, use_container_width=True)
                    else:
                        st.info("No messages found for this project.")
                else:
                    st.info("No messages found for this project.")
