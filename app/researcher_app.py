import bcrypt
import streamlit as st
import dbs
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from web_monitor import WebMonitor
import asyncio
import requests
import os
import re


server = os.getenv("SERVER")

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



def researcher_app(userid, tables_dict):
    """Main function for the Researcher Dashboard."""
    # tables
    chats, users, projects, user_projects, chats_projects, chats_blacklist, messages = (
        tables_dict["Chats"],
        tables_dict["Users"],
        tables_dict["Projects"],
        tables_dict["UserProjects"],
        tables_dict["ChatsProjects"],
        tables_dict["ChatsBlacklist"],
        tables_dict["MessagesTable"]
    )
    user_data = users.get_user_by_id(userid)

    # Check if user data exists
    if not user_data:
        st.error(f"User with username {userid} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="researcher_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["user"] = None
            st.rerun()
        return

    # # Get user information
    # users_projects = projects.get_projects_by_researcher(userid)

    # # Get the projects where this researcher is the lead
    # researcher_projects = get_researcher_projects(userid)
    # Page title
    st.title("Researcher Dashboard")

    # if not users_projects:
    #     st.warning("You are not currently assigned as a lead researcher for any projects.")
    #     st.info("Please contact the administrator to be assigned to a project.")
    #     return
    
    # projects_by_name = {record['ProjectName']: record for record in users_projects}
    # projects_by_id = {record['ProjectID']: record for record in users_projects}
    # projects_by_name = projects_by_id

    # project_names = list(projects_by_name.keys()) if projects_by_name else []


    st.sidebar.success(f"Welcome, {userid}!")

    # # Sidebar: Select Project
    # st.sidebar.header("Select a Project")

    # Build project_id to name mapping for selectbox
    # project_id_to_name = {pid: info['ProjectName'] for pid, info in projects_by_id.items()}
    # project_ids = list(project_id_to_name.keys())
    # project_names = [project_id_to_name[pid] for pid in project_ids]

    # Default project selection
    # if "selected_project_id" not in st.session_state:
    #     st.session_state["selected_project_id"] = project_ids[0]

    # # Selectbox for project selection by name
    # selected_project_name = st.sidebar.selectbox(
    #     "Project",
    #     project_names,
    #     index=project_names.index(project_id_to_name[st.session_state["selected_project_id"]]),
    #     key="sidebar_project_select"
    # )
    # # Map back to project_id
    # selected_project_id = [pid for pid, name in project_id_to_name.items() if name == selected_project_name][0]
    # st.session_state["selected_project_id"] = selected_project_id

    # curr_chat_ids = chats_projects.get_chats_ids_by_projects(selected_project_id)
    # messages_df = messages.get_df(chats_ids=curr_chat_ids)
    messages_df = messages.get_df(chat_ids=['hovOAmJBtnOuQFpvBu'])
    chats_summary = messages.get_chats_summary(messages_df)
    # chats_summary = 

    # Sidebar menu
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["Project Analytics", "Chat Analysis", "User Management"]
    )

    # Project Analytics Page (Blank)
    if menu == "Project Analytics":
        st.header("Project Analytics")
        st.markdown("This page is under construction.")
        st.dataframe(chats_summary, use_container_width=True, hide_index=True)

    # Chat Analysis Page
    elif menu == "Chat Analysis":
        st.header("Chat Analysis")
        st.markdown("Analyze chats for the selected project.")
        st.dataframe(messages_df, use_container_width=True)

    # User Management Page
    elif menu == "User Management":
        st.header("User Management")
        st.markdown("Manage users in your project.")

        tab1, tab2 = st.tabs(["Project's Users", "Register New User"])

        with tab1: # project's users tab
            # Fetch users in the project
            users_df = users.get_users()
            # Display users in the project
            st.subheader("Users in Project")
            if len(users_df) == 0: # if table is empty
                st.info("No users are currently registered in this project.")
            else:
                # users_df = pd.DataFrame(users_data)
                users_df['Delete'] = False  # Add a column for deletion
                delete_col_config = st.column_config.CheckboxColumn("Delete", help="Check to delete this user", default=False)
                active_col_config = st.column_config.CheckboxColumn("Active", help="Check to activate this user", default=False)
                edited_users_df = st.data_editor(
                    users_df[['UserID', 'Role', 'Creator', 'Active', 'CreatedAt', 'UpdatedAt', 'Delete']],
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        'Delete': delete_col_config,
                        'Active': active_col_config
                    },
                    disabled=['UserID', 'Role', 'Creator', 'CreatedAt', 'UpdatedAt'],
                    hide_index=True
                )
                # Add Save/Confirm Changes button
                if st.button("Save Changes", key="save_user_deletions"):
                    any_change = False
                    for idx, row in edited_users_df.iterrows():
                        curr_user_id = row['UserID']
                        if row['Delete']:  # if the user is marked for deletion, delete them
                            # Check if the user is trying to delete themselves
                            if curr_user_id == userid:
                                st.warning("You cannot delete yourself from this page.")
                                continue
                            # send delete request to the server
                            try:
                                requests.post(
                                    f"{server}/api/user/destroy",
                                    json={
                                        "username": curr_user_id
                                    }
                                )
                                # delete user from the database
                                users.delete_user(curr_user_id)
                                st.success(f"User {curr_user_id} deleted successfully.")
                                any_change = True
                            except Exception as e:
                                st.error(f"Failed to delete user {curr_user_id}: {str(e)}")
                        if row['Active'] != users.get_user_by_id(curr_user_id)['Active']: # if the active status has changed
                            try:
                                users.change_active_status_for_user(curr_user_id)
                                any_change = True
                                if row['Active']:
                                    st.success(f"User {curr_user_id} activated successfully.")
                                else:
                                    try: # send empty whitelist to stop pulling messages
                                        requests.post(
                                        f"{server}/api/user/whitelist-rooms",
                                        json={
                                            "username": curr_user_id,
                                            "room_ids": []
                                        })
                                    except Exception as e:
                                        st.error(f"Failed to update user {curr_user_id} active status: {str(e)}")
                                    else:
                                        st.success(f"User {curr_user_id} deactivated successfully.")
                            except Exception as e:
                                st.error(f"Failed to update user {row['UserID']} active status: {str(e)}")
                    if any_change:
                        st.rerun()

        with tab2: # register new user tab
            col1, col2 = st.columns(2)
            with col1:
                # Form to register a new user
                st.subheader("Register a New User")
                st.info("Usernames may only contain: a-z, 0-9, = _ - . / +")
                with st.form("register_user_form"):
                    # Input fields for registration
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    server_url = "https://vox-populi.dev"
                    allowed_pattern = r'^[a-z0-9=_.\-/+]+$'
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    # Register button
                    submit_button = st.form_submit_button("Register")
                    if submit_button:
                        if not username or not password or not confirm_password:
                            st.error("Please fill in all fields.")
                        elif password != confirm_password:
                            st.error("Passwords do not match.")
                        elif not re.match(allowed_pattern, username):
                            st.error("Username can only contain: a-z, 0-9, = _ - . / +")
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
                                    result = asyncio.run(web_monitor.register()) # register on server
                                    if result:
                                        users.add_user(  # register user in the database
                                            user_id=username, 
                                            hashed_password=hashed_password,
                                            creator_id=userid, 
                                            role="User",
                                            active=True,
                                        )
                                        user_projects.add_user_to_project(
                                            user_id=username
                                        )

                                        json = {   # send to server
                                            "username": username,
                                            "password": password
                                        }
                                        result = requests.post(f"{server}/api/user/create", json=json)
                                        if not result.json().get("success"):
                                            st.error(f"Error registering user on server: {result.json().get('message', 'Unknown error')}")
                                            return
                                        else:
                                            st.success(f"User {username} registered successfully!")
                                    else:
                                        st.error("Registration failed. Username might already exist.")
                                except Exception as e:
                                    st.error(f"Registration error: {str(e)}")
           
