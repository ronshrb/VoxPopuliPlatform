import streamlit as st
import pandas as pd
from web_monitor import WebMonitor  # Import WebMonitor
import asyncio
import time
import bcrypt
import requests
import os
from dotenv import load_dotenv
load_dotenv()

server = os.getenv("SERVER")

def user_app(userid, tables_dict, password):
    """
    Main function for the User Dashboard.
    Handles chat/project management, QR code generation, and user actions.
    """
    # Unpack table objects from tables_dict
    chats, users, projects, chats_blacklist, messages = (
        tables_dict["Chats"],
        tables_dict["Users"],
        tables_dict["Projects"],
        tables_dict["ChatsBlacklist"],
        tables_dict["MessagesTable"]
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
    else: # if a web monitor already exists, use it
        web_monitor = st.session_state["web_monitor"]
    

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
    chats_df = chats.get_chats_by_user(userid)
    # chats_df = pd.DataFrame(user_chats) if user_chats else pd.DataFrame(columns=['ChatID', 'Chat Name', 'Platform', 'UserID', 'CreatedAt', 'UpdatedAt'])
    # columns_renaming = {
    #     'chatname': 'Chat Name',
    #     'chatid': 'ChatID',
    #     'platform': 'Platform',
    #     'createat': 'CreatedAt',
    #     'updatedat': 'UpdatedAt',
    # }
    # chats_df.rename(columns=columns_renaming, inplace=True)

    # # Fetch project details
    # available_projects = user_projects.get_user_projects(userid)
    # projects_info = projects.get_projects_by_ids(available_projects)

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
            
            
            # if selected_project_id:
            #     chats_df['Donated'] = chats_df['ChatID'].apply(
            #         lambda chat_id: chats_projects.is_chat_in_project(chat_id, selected_project_id)
            #     )
            # else:
            #     chats_df['Donated'] = False

            # Add Blacklist column (default False)
            chats_df['Blacklist'] = False

            filtered_df = chats_df.copy()

            # Apply all filters to chats DataFrame
            # if selected_project_id:
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
                donated_result = asyncio.run(web_monitor.get_invited_chats(group=False))
                not_donated_result = asyncio.run(web_monitor.get_joined_chats(group=False))
                not_donated_chats = donated_result.get("invited_chats", [])
                donated_chats = not_donated_result.get("joined_chats", [])
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
                        # chats_projects.remove_chat_project(chat_id=chat_id)
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
                        chats.change_active_status_for_chat(chat_id=chat_id)
                        result = asyncio.run(web_monitor.approve_room(chat_id))
                        if result.get("status") == "success":
                            if row["Donated"]: 
                                st.toast(f"Donated Chat: {row['Chat Name']}", icon="✅")
                            else: # Remove chat from project (room is still joined)
                                st.toast(f"Disabled Chat: {row['Chat Name']}", icon="✅")
                        else:
                            st.toast(f"Failed to change chat status: {row['Chat Name']}", icon="❌")

                print("Whitelisting:")
                rooms_for_whitelist = chats.get_whitelisted_rooms_by_user(userid)
                print(f"Current whitelisted rooms: {rooms_for_whitelist}:")
                # for room in users.get_whitelisted_rooms():
                #     print(f' - {room}')
                requests.post(
                    f"{server}/api/user/whitelist-rooms",
                    json={
                        "username": userid,
                        "room_ids": rooms_for_whitelist
                    }
                )
                st.rerun()
            
    # with tab2:
    #     # Statistics tab
    #     st.header("Statistics")
    #     # Get chat IDs for this user and project
    #     user_chats = chats.get_chats_by_user(userid)
    #     user_chat_ids = set(chat['chatid'] for chat in user_chats)
    #     # project_chat_ids = set(chats_projects.get_chats_ids_by_projects(selected_project_id))
    #     # Only chats belonging to this user and project
    #     # relevant_chat_ids = [chat_id for chat_id in user_chat_ids if chat_id in project_chat_ids]
    #     if user_chat_ids:
    #         # Count messages per chat from foo_2025-05-29.jsonl
    #         import json
    #         from collections import Counter
    #         msg_counts = Counter()
    #         try:
    #             with open('app\menashe_2025-05-29.jsonl', 'r', encoding='utf-8') as f:
    #                 for line in f:
    #                     try:
    #                         msg = json.loads(line)
    #                         room_id = msg.get('room_id')
    #                         if room_id:
    #                             msg_counts[room_id] += 1
    #                     except Exception:
    #                         continue
    #         except Exception as e:
    #             st.warning(f"Could not read message file: {e}")
    #         with st.spinner("Fetching room statistics..."):
    #             stats_result = asyncio.run(web_monitor.get_room_stats(user_chat_ids))
    #         if stats_result.get("status") == "success":
    #             stats_df = pd.DataFrame(stats_result["room_stats"])
    #             # Add message count column
    #             stats_df['num_messages'] = stats_df['room_id'].apply(lambda rid: msg_counts.get(rid.split(':')[0], 0))
    #             st.dataframe(stats_df, use_container_width=True, hide_index=True)
    #         else:
    #             st.error(f"Failed to fetch room stats: {stats_result.get('message', 'Unknown error')}")
    #     else:
    #         st.info("No chats found for this project.")
        
    
    with tab3:
        # Account tab placeholder
        st.header("Account Settings")
        
        st.markdown('---')
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.form('change_password_form'):
                st.subheader('Change Password')
                new_password = st.text_input('New Password', type='password')
                confirm_password = st.text_input('Confirm New Password', type='password')
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                submitted = st.form_submit_button('Change Password')
                if submitted:
                    if not new_password or not confirm_password:
                        st.error('Please fill in both password fields.')
                    elif new_password != confirm_password:
                        st.error('Passwords do not match.')
                    else:
                        with st.spinner('Changing password...'):
                            result = asyncio.run(web_monitor.change_password(new_password))
                            if result.get('status') == 'success':
                                users.change_user_password(userid, hashed_password)
                                password = new_password  # Update session state password
                                st.success('Password changed successfully!')
                            else:
                                st.error(f"Failed to change password: {result.get('message', 'Unknown error')}")

        # with col2:
            # with st.form('Leave Project'):
            #     st.subheader('Leave Project')
            #     if available_projects:
            #         project_ids = [pid for pid in available_projects if pid in projects_info]
            #         project_names = [projects_info[pid]['ProjectName'] for pid in project_ids]
            #         selected_project = st.selectbox('Select Project to Leave', project_names, key='leave_project_select')
            #     else:
            #         st.info('You are not part of any projects.')
            #         selected_project = None

            #     submitted = st.form_submit_button('Leave Project')
            #     if submitted and selected_project:
            #         project_id = next(pid for pid, name in zip(project_ids, project_names) if name == selected_project)
            #         with st.spinner(f'Leaving project {selected_project}...'):
            #             user_projects.remove_user_project(userid, project_id)
            #             st.success(f'You have left the project: {selected_project}')
            #             st.rerun()
        with col3:
            with st.form('Disable All Chats'):
                st.subheader('Disable All Chats')
                st.warning('This will disable all of your donated chats.')
                if st.form_submit_button('Disable All Chats'):
                    with st.spinner('Disabling all chats...'):
                        try:
                            requests.post(
                            f"{server}/api/user/whitelist-rooms",
                            json={
                                "username": userid,
                                "room_ids": []
                            }
                        )
                            chats.disable_all_rooms_for_user(userid)
                            
                        except Exception as e:
                            st.error(f"An error occurred while disabling chats: {str(e)}")

        st.markdown('---')
        st.warning('Danger Zone: Deleting your account is irreversible.')
        if st.button('Delete My Account', type='primary'):
            with st.spinner('Deleting your account...'):
                try:
                    requests.post(f"{server}/api/user/destroy",
                        json={
                            "username": userid
                        }
                    )

                    # requests.post(
                    #         f"{server}/api/user/whitelist-rooms",
                    #         json={
                    #             "username": userid,
                    #             "room_ids": []
                    #         }
                    #     )
                    
                    chats.disable_all_rooms_for_user(userid) # can be removed if the user is deleted?
                    users.delete_user(userid)

                    st.success('Your account has been deleted. Logging out...')
                    st.session_state["logged_in"] = False
                    st.session_state["role"] = None
                    st.session_state["user"] = None
                    st.rerun()
                # result = asyncio.run(web_monitor.delete_user())
                # if result.get('status') == 'success':
                #     st.success('Your account has been deleted. Logging out...')
                #     st.session_state['logged_in'] = False
                #     st.session_state['role'] = None
                #     st.session_state['user'] = None
                #     st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to delete account: {str(e)}")


