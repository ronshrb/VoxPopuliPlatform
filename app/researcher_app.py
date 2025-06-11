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
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import matplotlib
import colorsys

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
    chats, users, chats_blacklist, messages = (
        tables_dict["Chats"],
        tables_dict["Users"],
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


    # Page title
    st.sidebar.title("Researcher Dashboard")

    st.sidebar.success(f"Welcome, {userid}!")

    # chats_ids = chats.get_chats_ids_by_user(userid)
    all_users_ids = users.get_users()['UserID'].tolist()
    messages_df = messages.get_df(user_ids=all_users_ids)
    chats_summary = messages.get_chats_summary(messages_df, chats.get_df())

    with st.sidebar:
        # --- Download options for messages_df ---
        with st.expander("Download all messages"):
            st.download_button(
                label="Download as CSV",
                data=messages_df.to_csv(index=False).encode('utf-8'),
                file_name="messages.csv",
                mime="text/csv"
            )
            
            st.download_button(
                label="Download as JSON",
                data=messages_df.to_json(orient="records", force_ascii=False, date_format="iso"),
                file_name="messages.json",
                mime="application/json"
            )
            import io
            parquet_buffer = io.BytesIO()
            messages_df.to_parquet(parquet_buffer, index=False)
            st.download_button(
                label="Download as Parquet",
                data=parquet_buffer.getvalue(),
                file_name="messages.parquet",
                mime="application/octet-stream"
            )

    # Sidebar menu
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["Chats Overview", "Chats Analysis", "User Management"]
    )
    
        
    # Project Analytics Page (Blank)
    if menu == "Chats Overview":
        st.header("Chats Overview")
        st.markdown("This page is under construction.")
        st.dataframe(chats_summary, use_container_width=True, hide_index=True)

    # Chat Analysis Page
    elif menu == "Chats Analysis":
        st.header("Chats Analysis")
        st.markdown("Analyze chats for the selected project.")

        # Get chat names and ids dictionary using the updated function signature
        chats_df = chats.get_df()
        chat_name_to_id = messages.get_chats_ids_and_names(chats_df)
        if chat_name_to_id:
            available_chats = [chat_name for chat_name, chat_id in chat_name_to_id.items() if chat_id in messages_df['ChatID'].unique()]
            # Change the chat selection widget from a radio button to a dropdown (selectbox)
            selected_chat_name = st.selectbox("Pick a chat to analyze:", options=available_chats, key="chat_select")
            selected_chat_id = chat_name_to_id[selected_chat_name]
        else:
            st.warning("No chats available to select.")
            return  # Exit early if no chats

        chat_to_display = messages_df[messages_df['ChatID'] == selected_chat_id]
        chat_to_display = chat_to_display[['Sender', 'Content', 'Timestamp']].copy()
        col1, col2 = st.columns([0.2, 0.6])
        with col1:
            # --- Metrics ---
            st.subheader("Chat Metrics")
            num_users = chat_to_display['Sender'].nunique()
            num_messages = len(chat_to_display)
            st.metric("Number of Active Users", num_users)
            st.metric("Number of Messages", num_messages)
        with col2:
            # --- Word Cloud ---
            st.subheader("Word Cloud")
            # Specify a font that supports Hebrew (update the path as needed)
            font_path = r"app/ARIAL.TTF"\
            # font_path = r"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            def fix_hebrew(text):
                # Reverse each Hebrew word
                def reverse_hebrew_word(match):
                    return match.group(0)[::-1]
                # Hebrew unicode range: \u0590-\u05FF
                return re.sub(r'[\u0590-\u05FF]+', reverse_hebrew_word, text)
            text = " ".join(chat_to_display['Content'].dropna().astype(str))
            # text = fix_hebrew(text)
            stopwords = set(STOPWORDS)
            # Add Hebrew stopwords
            hebrew_stopwords = {'הפ', 'רתוי', 'הלוכי', 'וליאו', 'לא', 'ןאכ', 'לצא', 'אוה', 'לע', 'ותיא', 'המצע', 'םכתא', 'ןכ', 'ולא', 'םתא', 'ול', 'יתיה', 'היהי', 'ןהל', 'התוא', 'הביס וזיאמ', 'ליבשב', 'ילבמ', 'םמצע', 'ילע', 'ןיב', 'תועצמאב', 'ןכתיא', 'ןהמצע', 'ןאל', 'ןיא', 'תולוכי', 'ןתא', 'טעמ', 'ימ', 'ןמ', 'םירחא', 'עודמ', 'ךתיא', 'שכ', 'לש', 'ונחנא', 'ןיבל', 'ירוחאמ', 'רבעל', 'ללגב', 'ןכלש', 'וב םוקמ', 'םע', 'ךא', 'רחא', 'םכתיא', 'םיטעמ', 'ש העשב', 'םכילע', 'הטמל', 'אל', 'זא', 'לוכי', 'הלעמל', 'ימצע', 'יכ', 'סא', 'ולש', 'הפיא', 'היהת', 'ותוא', 'ולכוי', 'לכי', 'איה', 'ואל', 'ןה', 'הז', 'םילוכי', 'ןאכמ', 'קר', 'הלכי', 'םכל', 'הלש', 'לומ', 'ןתיא', 'םהל', 'םא', 'ךכ', 'תורחא', 'ובש םוקמל', 'תא', 'וילע', 'ולכי', 'דצמ', 'זע', 'ןכל', 'תחת', 'ץוחמ', 'ומכ', 'תאז', 'ונמצע', 'ןהלש', 'תחתמ', 'ינפל', 'ןוויכמ', 'ךיא', 'דציכ', 'ונלש', 'עצמאב', 'םש', 'ךותב', 'ןכתא', 'יתמ', 'הדימב', 'רשא', 'ןכיה', 'םכלש', 'םהילע', 'תרחא', 'ךתוא', 'רשאכ', 'לכ', 'ונתיא', 'תאו', 'יפכ', 'ךילע', 'ונל', 'תילכת וזיאל', 'ןתוא', 'םהלש', 'התיא', 'לכוי', 'ףא', 'התיה', 'ידמ', 'דבלמ', 'הללגבש הביסה', 'ומצע', 'ללכ', 'המל', 'ןיאמ', 'יתוא', 'דע', 'יא', 'ונילע', 'ןכיעל', 'ירה', 'יל', 'המ', 'הנה', 'םהמצע', 'הזיא', 'דאמ', 'רגנ', 'םה', 'ינא', 'ירחא', 'הדימ וזיאב', 'הלא', 'ונ', 'וא', 'הזכ', 'הככ', 'בוש', 'ךרד', 'היה', 'דגנ', 'תוז', 'התא', 'הילע', 'לעמ', 'ןמצע', 'םתיא', 'םרב', 'ךכיפל', 'ךלש', 'ןלוכ', 'ןכיהמ', 'ונתוא', 'תורמל', 'דעבמ', 'לבא', 'יתיא', 'םלוכ', 'ןינמ', 'הפיאמ', 'םג', 'ןהילע', 'םתוא', 'לגוסמ', 'הל', 'ובש םוקמב', 'ילוא', 'שי', 'תויהל', 'ילש', 'ילב'}     
            hebrew_stopwords = {word[::-1] for word in hebrew_stopwords}
            stopwords.update(hebrew_stopwords)
            anonymization_labels = {'NAME', 'SPECIAL', 'DATE', 'ADDRESS'}
            stopwords.update(anonymization_labels)
            # try:
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                stopwords=stopwords,
                font_path=font_path
            ).generate(text)
            # except OSError:
            #     print(os.listdir("/"))
            #     print(os.listdir("/app"))
            #     print(os.listdir("/app/utils"))
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)

                # --- Activity by Day ---
        st.subheader("Activity")
        chat_to_display['Date'] = pd.to_datetime(chat_to_display['Timestamp']).dt.date
        messages_per_day = chat_to_display.groupby('Date').size()
        st.line_chart(messages_per_day, use_container_width=True)
        col1, col2 = st.columns([0.5, 0.5])
        with col1:
            # 2. Message Length Distribution: Histogram of message lengths
            st.markdown("### Message Length Distribution")
            msg_lengths = chat_to_display['Content'].dropna().astype(str).apply(len)
            fig3, ax3 = plt.subplots()
            ax3.hist(msg_lengths, bins=30, color='skyblue', edgecolor='black')
            ax3.set_xlabel("Message Length (characters)")
            ax3.set_ylabel("Frequency")
            ax3.set_title("Distribution of Message Lengths")
            st.pyplot(fig3)

        with col2:

            # --- Activity Chart Selector ---
            subcol1, subcol2 = st.columns([0.5, 0.5])
            with subcol1:
                st.subheader("Chat Activity By")
            with subcol2:
                activity_group = st.selectbox(
                    "Group activity by:",
                    options=["Hour", "Part of Day", "Day of Week"],
                    key="activity_group_select",
                    label_visibility="collapsed"
                )
            chat_to_display['Date'] = pd.to_datetime(chat_to_display['Timestamp']).dt.date
            if activity_group == "Hour":
                chat_to_display['Hour'] = pd.to_datetime(chat_to_display['Timestamp']).dt.hour
                messages_per_hour = chat_to_display.groupby('Hour').size()
                avg_messages_per_hour = messages_per_hour / chat_to_display['Date'].nunique()
                avg_messages_per_hour = avg_messages_per_hour.reindex(range(24), fill_value=0)
                # Pie chart for hour
                fig, ax = plt.subplots()
                ax.pie(avg_messages_per_hour, labels=avg_messages_per_hour.index, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
            elif activity_group == "Part of Day":
                def get_part_of_day(hour):
                    if 5 <= hour < 12:
                        return "Morning"
                    elif 12 <= hour < 17:
                        return "Afternoon"
                    elif 17 <= hour < 21:
                        return "Evening"
                    else:
                        return "Night"
                chat_to_display['Hour'] = pd.to_datetime(chat_to_display['Timestamp']).dt.hour
                chat_to_display['PartOfDay'] = chat_to_display['Hour'].apply(get_part_of_day)
                messages_per_part = chat_to_display.groupby('PartOfDay').size()
                # Ensure order
                part_order = ["Night", "Morning", "Afternoon", "Evening"]
                messages_per_part = messages_per_part.reindex(part_order, fill_value=0)
                avg_messages_per_part = messages_per_part / chat_to_display['Date'].nunique()
                # Pie chart for part of day
                fig, ax = plt.subplots()
                ax.pie(avg_messages_per_part, labels=avg_messages_per_part.index, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
            elif activity_group == "Day of Week":
                chat_to_display['DayOfWeek'] = pd.to_datetime(chat_to_display['Timestamp']).dt.day_name()
                messages_per_dayofweek = chat_to_display.groupby('DayOfWeek').size()
                # Ensure order: Monday, Tuesday, ..., Sunday
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                messages_per_dayofweek = messages_per_dayofweek.reindex(day_order, fill_value=0)
                # Pie chart for day of week
                fig, ax = plt.subplots()
                ax.pie(messages_per_dayofweek, labels=messages_per_dayofweek.index, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)

        # --- Messages ---
        # Assign a unique light color to each sender
        chat_to_display_final = chat_to_display[['Sender', 'Content', 'Timestamp']].copy()
        unique_senders = chat_to_display_final['Sender'].unique()
        # Generate light pastel colors using HSV
        def pastel_color(i, total):
            hue = i / total
            lightness = 0.85
            saturation = 0.5
            rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
            return f'background-color: {matplotlib.colors.rgb2hex(rgb)}'
        sender_to_color = {sender: pastel_color(i, len(unique_senders)) for i, sender in enumerate(unique_senders)}
        def color_rows(row):
            return [sender_to_color[row['Sender']]] * len(row)
        styled_df = chat_to_display_final.style.apply(color_rows, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)




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
                    role = st.selectbox("Role", ["User", "Researcher"], key="register_role_select")
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
                                    if role == "User":
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
                                                role=role,
                                                active=True,
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
                                    else:
                                        # For researcher role, just register in the database
                                        users.add_user(
                                            user_id=username, 
                                            hashed_password=hashed_password,
                                            creator_id=userid, 
                                            role=role,
                                            active=True,
                                        )
                                        st.success(f"Researcher {username} registered successfully!")
                                except Exception as e:
                                    st.error(f"Registration error: {str(e)}")

