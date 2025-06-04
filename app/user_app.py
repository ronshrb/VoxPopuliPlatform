import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
import qrcode
import dbs
from web_monitor import WebMonitor  # Import WebMonitor
import asyncio
import time


def user_app(userid, tables_dict, password):
    """
    Main function for the User Dashboard.
    Handles chat/project management, QR code generation, and user actions.
    """
    # Unpack table objects from tables_dict
    chats, users, projects, user_projects, chats_projects, chats_blacklist = (
        tables_dict["Chats"],
        tables_dict["Users"],
        tables_dict["Projects"],
        tables_dict["UserProjects"],
        tables_dict["ChatsProjects"],
        tables_dict["ChatsBlacklist"],
    )
    blacklist_ids = chats_blacklist.get_all_ids()
    # Use a persistent web_monitor instance in session state, but ensure it matches the current user
    if (
        "web_monitor" not in st.session_state
        or not hasattr(st.session_state["web_monitor"], "username")
        or st.session_state["web_monitor"].username != userid
    ):
        # Explicitly set all platforms to ensure bridge_configs is populated
        web_monitor = WebMonitor(username=userid, password=password, platforms=["signal", "whatsapp", "telegram"])
        login_result = asyncio.run(web_monitor.login())
        if login_result.get("status") == "success":
            st.session_state["web_monitor"] = web_monitor
        else:
            st.error("Login failed. Please try again.")
            return
    else:
        web_monitor = st.session_state["web_monitor"]
    # web_monitor = WebMonitor(username=userid, password=password, platforms=["signal", "whatsapp", "telegram"])
    # login_result = asyncio.run(web_monitor.login())
    # st.session_state["web_monitor"] = web_monitor
    # Fetch user data from UsersTable
    user_data = users.get_user_by_id(userid)

    if not user_data:
        st.error(f"User with username {userid} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="user_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["user"] = None
            st.rerun()
        return

    # Fetch user's chats from the database using ChatsTable
    user_chats = chats.get_chat_by_user(userid)
    chats_df = pd.DataFrame(user_chats) if user_chats else pd.DataFrame(columns=['ChatID', 'Chat Name', 'Platform', 'UserID', 'CreatedAt', 'UpdatedAt'])
    columns_renaming = {
        'chatname': 'Chat Name',
        'chatid': 'ChatID',
        'platform': 'Platform',
        'createat': 'CreatedAt',
        'updatedat': 'UpdatedAt',
    }
    chats_df.rename(columns=columns_renaming, inplace=True)

    # Fetch project details
    available_projects = user_projects.get_user_projects(userid)
    projects_info = projects.get_projects_by_ids(available_projects)

    # Page title
    st.title("User Dashboard")

    with st.sidebar:
        st.success(f"Welcome, {userid}!")

        # Sidebar QR Code with 7-minute cooldown
        cooldown_seconds = 7 * 60  # 7 minutes
        now = time.time()
        platform_options = ["whatsapp", "signal", "telegram"]
        selected_platform = st.selectbox("Choose platform for QR code", platform_options, key="qr_platform")
        cooldown_key = f"last_qr_time_{userid}_{selected_platform}"
        last_qr_time = st.session_state.get(cooldown_key, 0)
        cooldown_remaining = int(cooldown_seconds - (now - last_qr_time))

        if st.button("Generate QR Code"):
            if cooldown_remaining > 0:
                st.sidebar.info(f"Please wait {cooldown_remaining // 60}:{cooldown_remaining % 60:02d} minutes before generating a new QR code.")
            else:
                try:
                    with st.sidebar:
                        st.spinner(f"Generating QR Code for {selected_platform}...")
                        qr_code = asyncio.run(web_monitor.generate_qr_code_and_display(platform=selected_platform))
                        st.sidebar.image(qr_code, caption="Generated QR Code", use_container_width=True)
                        st.info("This QR code is valid for 5 minutes. Please generate a new one if needed.")
                    st.session_state[cooldown_key] = time.time()  # Set cooldown for this user+platform
                    st.session_state["last_qr_code"] = qr_code      # Store QR code
                except Exception as e:
                    pass

    # Main tabs for user dashboard
    tab1, tab2, tab3 = st.tabs(["My Chats","Statistics", "Account"])
    with tab1:
        # Filters section
        st.header("My Chats")

        col1, col2 = st.columns([1,2])
        with col1:
            st.markdown("### 🔍 Filter Your Chats")
            # Project filter
            if projects_info:
                project_id_to_name = {pid: info['ProjectName'] for pid, info in projects_info.items()}
                selected_project_id = st.selectbox(
                    "Select a Project",
                    list(project_id_to_name.keys()),
                    format_func=lambda pid: project_id_to_name[pid],
                    key="project_filter"
                )
            else:
                st.markdown("No projects available.")
                selected_project_id = None
            selected_project = projects_info[selected_project_id]
            # Platform filter
            selected_platforms = st.pills(
                "Select Platforms",
                options=["whatsapp", "signal", "telegram"],
                default=["whatsapp", "signal", "telegram"],
                key="platform_filter",
                selection_mode ="multi",
            )
            # Search filter
            search_text = st.text_input("Search by chat name")
            # Donation status filter
            donation_filter = st.selectbox("Filter by donation status", ["All", "Donated", "Not Donated"])
            
            # Add Donated column based on chat-project association
            if selected_project_id:
                chats_df['Donated'] = chats_df['ChatID'].apply(
                    lambda chat_id: chats_projects.is_chat_in_project(chat_id, selected_project_id)
                )
            else:
                chats_df['Donated'] = False

            # Add Blacklist column (default False)
            chats_df['Blacklist'] = False

            filtered_df = chats_df.copy()

            # Apply all filters to chats DataFrame
            if selected_project_id:
                if selected_platforms:
                    filtered_df = filtered_df[
                        (filtered_df['Platform'].isin(selected_platforms))
                    ]
                if search_text:
                    filtered_df = filtered_df[filtered_df['Chat Name'].str.contains(search_text, case=False, na=False)]
                if donation_filter == "Donated":
                    filtered_df = filtered_df[filtered_df['Donated'] == True]
                elif donation_filter == "Not Donated":
                    filtered_df = filtered_df[filtered_df['Donated'] == False]
            
            if st.button("Refresh My Chats"):
                # Refresh chat lists from web_monitor and update local DB
                donated_result = asyncio.run(web_monitor.get_invited_chats())
                not_donated_result = asyncio.run(web_monitor.get_joined_chats())
                donated_chats = donated_result.get("invited_chats", [])
                not_donated_chats = not_donated_result.get("joined_chats", [])
                if donated_chats:
                    chats.update_all_chats(donated_chats)
                if not_donated_chats:
                    chats.update_all_chats(not_donated_chats)
                st.rerun()

        with col2:
            # Display and edit table of chats
            editable_cols = ['Donated', 'Blacklist']
            displayed_cols = ['ChatID', 'Chat Name', 'Platform'] + editable_cols
            st.markdown("### ☑️ Chats Picker")
            edited_df = st.data_editor(
                filtered_df[displayed_cols] if not filtered_df.empty else pd.DataFrame(columns=displayed_cols),
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "Donated": st.column_config.CheckboxColumn("Donated", help="Select if you want to donate this chat to the project"),
                    'ChatID': None,
                    'Blacklist': st.column_config.CheckboxColumn("Blacklist", help="Select to delete this chat from all projects"),
                },
                disabled=["Chat Name"],
                hide_index=True
            )
        with col1:
            # Save changes to chat/project/blacklist state
            if not filtered_df.empty and st.button("Save Changes"):
                for _, row in edited_df.iterrows():
                    chat_id = row["ChatID"]
                    if row["Blacklist"]:
                        # Remove chat from project and delete it
                        chats_projects.remove_chat_project(chat_id=chat_id, project_id=selected_project_id)
                        chats.delete_chat(chat_id)
                        st.toast(f"Deleted chat: {row['Chat Name']}", icon="✅")
                        result = asyncio.run(web_monitor.disable_room(chat_id))
                        chats_blacklist.add_chat(chat_id)  # add to chats blacklist
                        if result.get("status") == "success":
                            st.toast(f"Disabled Chat: {row['Chat Name']}", icon="✅")
                        else:
                            st.toast(f"Failed to disable chat: {row['Chat Name']}", icon="❌")
                        continue
                    original_row = chats_df.loc[chats_df["ChatID"] == chat_id].iloc[0]
                    if row["Donated"] != original_row["Donated"]:
                        if row["Donated"]: 
                            result = asyncio.run(web_monitor.approve_room(chat_id))
                            chats_projects.add_chat_project(chat_id=chat_id, project_id=selected_project_id)
                            st.toast(f"Donated Chat: {row['Chat Name']}", icon="✅")
                        else: # Remove chat from project (room is still joined)
                            chats_projects.remove_chat_project(chat_id=chat_id, project_id=selected_project_id)
                            # Disable (leave) the room
                            result = asyncio.run(web_monitor.disable_room(chat_id))
                            if result.get("status") == "success":
                                st.toast(f"Disabled Chat: {row['Chat Name']}", icon="✅")
                            else:
                                st.toast(f"Failed to disable Chat: {row['Chat Name']}", icon="❌")
                        st.toast(f"Saved changes for chat: {row['Chat Name']}", icon="✅")
                st.rerun()
            
    with tab2:
        # Statistics tab placeholder
        st.header("Statistics")
        st.write("Statistics content goes here.")
    
    with tab3:
        # Account tab placeholder
        st.header("Account")
        st.write("Account settings and information.")
        st.markdown("---")
        st.warning("Danger Zone: Deleting your account is irreversible.")
        if st.button("Delete My Account", type="primary"):
            with st.spinner("Deleting your account..."):
                result = asyncio.run(web_monitor.delete_user())
                if result.get("status") == "success":
                    st.success("Your account has been deleted. Logging out...")
                    st.session_state["logged_in"] = False
                    st.session_state["role"] = None
                    st.session_state["user"] = None
                    st.rerun()
                else:
                    st.error(f"Failed to delete account: {result.get('message', 'Unknown error')}")


