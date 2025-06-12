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
    chats, users, chats_blacklist, messages = (
        tables_dict["Chats"],
        tables_dict["Users"],
        tables_dict["ChatsBlacklist"],
        tables_dict["MessagesTable"]
    )
    blacklist_ids = chats_blacklist.get_all_ids(userid)
    
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

        if selected_platform == 'telegram':
            import re
            telegram_room_key = f'telegram_bot_room_id_{userid}'
            
            # Initialize telegram session variables only if they don't exist yet
            if 'telegram' not in st.session_state:
                st.session_state['telegram'] = True
            if 'telegram_login_qr_sent' not in st.session_state:
                st.session_state['telegram_login_qr_sent'] = False
            if 'telegram_phone_sent' not in st.session_state:
                st.session_state['telegram_phone_sent'] = False
                
            # Step 1: Send 'login qr' only when button is pressed
            if not st.session_state['telegram_login_qr_sent']:
                if st.button("Start Telegram Login"):
                    asyncio.run(web_monitor.send_message_to_telegram_bot('login qr'))
                    st.session_state['telegram_login_qr_sent'] = True
                    st.rerun()
                # st.stop()
            elif not st.session_state['telegram_phone_sent']:
                # Step 2: Enter phone number and send only when button is pressed
                phone_number = st.text_input(
                    "Enter your phone number (with country code) for Telegram QR code",
                    key="telegram_phone_input",
                    placeholder="+1234567890"
                )
                phone_pattern = re.compile(r"^\+\d{10,15}$")
                if phone_pattern.match(phone_number):
                    if st.button("Send Phone Number to Telegram Bot"):
                        result = asyncio.run(web_monitor.send_message_to_telegram_bot(phone_number))
                        if not result or result.get("status") != "success":
                            st.error("Failed to send phone number to Telegram bot. Please try again.")
                        else:
                            st.session_state['telegram_phone_sent'] = True
                            st.rerun()
                    # st.stop()
            else:
                # Step 3: Enter login code and send only when button is pressed
                login_code = st.text_input(
                    "Login code sent to your Telegram. Enter the code here to generate QR code",
                    key="telegram_code_input"
                )
                if login_code and st.button("Send Login Code to Telegram"):
                    result = asyncio.run(web_monitor.send_message_to_telegram_bot(login_code))
                    if not result or result.get("status") != "success":
                        st.error("Failed to send login code to Telegram bot. Please try again.")
                    else:
                        st.session_state['telegram_code_sent'] = True
                        st.rerun()
                # st.stop()
                

        if selected_platform != 'telegram':
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
    tab1, tab3 = st.tabs(["My Chats", "Account"])
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
            
            
            chats_df['Blacklist'] = False

            filtered_df = chats_df.copy()

            # Apply all filters to chats DataFrame
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
                all_chats = donated_chats + not_donated_chats
                all_chats = [chat for chat in all_chats if chat["ChatID"] not in blacklist_ids] # Exclude blacklisted chats
                if all_chats:
                    chats.update_all_chats(all_chats, userid=userid)
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
                        chats.delete_chat(chat_id, userid)
                        # result = asyncio.run(web_monitor.disable_room(chat_id))
                        chats_blacklist.add_chat(chat_id, userid)  # add to chats blacklist
                        st.toast(f"Blacklisted Chat: {row['Chat Name']}", icon="✅")
                        continue
                    original_row = chats_df.loc[chats_df["ChatID"] == chat_id].iloc[0]
                    if row["Donated"] != original_row["Donated"]:
                        chats.change_active_status_for_chat(chat_id=chat_id, user_id=userid)
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

        with col2:
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

        with col3:
            with st.form('Delete Account'):
                st.subheader('Delete Account')
                st.warning('Danger Zone: Deleting your account is irreversible.')
                if st.form_submit_button('Delete My Account'):
                    with st.spinner('Deleting your account...'):
                        try:
                            requests.post(f"{server}/api/user/destroy",
                                json={
                                    "username": userid
                                }
                            )
                            
                            chats.disable_all_rooms_for_user(userid) # can be removed if the user is deleted?
                            result = asyncio.run(web_monitor.delete_user())
                            users.delete_user(userid)
                            if result.get('status') == 'success':
                                # users.delete_user(userid)
                                st.success('User was deleted successfully!')
                            else:
                                st.error(f"Failed to delete user: {result.get('message', 'Unknown error')}")
                            st.success('Your account has been deleted. Logging out...')
                            st.session_state["logged_in"] = False
                            st.session_state["role"] = None
                            st.session_state["user"] = None
                            st.rerun()
                        except requests.exceptions.RequestException as e:
                            st.error(f"Failed to delete account: {str(e)}")


