import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
import qrcode
import dbs
from web_monitor import WebMonitor  # Import WebMonitor
import asyncio
import time


def user_app(userid, users, projects, password):
    """Main function for the User Dashboard."""
    # Fetch user data
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

    # Get user information
    # username = user_data['Username']
    # userid = user_data['UserID']

    # # Fetch user's chats
    # user_chats = users.get_user_chats(userid)

    # # Convert chats to a DataFrame (empty DataFrame if no chats)
    # chats_df = pd.DataFrame(user_chats) if user_chats else pd.DataFrame(columns=['ChatID', 'ChatName', 'Donated', 'StartDate', 'ProjectID'])
    # chats_df['Donated'] = chats_df['Donated'].astype(bool)
    # chats_df['StartDate'] = pd.to_datetime(chats_df['StartDate'], errors='coerce').dt.date

    # # Fetch project details
    # project_ids = chats_df['ProjectID'].unique() if not chats_df.empty else []
    # projects = dbs.get_projects()  # Fetch all projects from the database
    # projects_df = pd.DataFrame(projects)
    # projects_names = projects_df['ProjectName'].unique() if not projects_df.empty else []

    # Page title
    st.title("User Dashboard")
    st.sidebar.success(f"Welcome, {userid}!")

    # Sidebar QR Code with 7-minute cooldown
    cooldown_seconds = 7 * 60  # 7 minutes
    now = time.time()
    platform_options = ["signal", "whatsapp", "telegram"]
    selected_platform = st.sidebar.selectbox("Choose platform for QR code", platform_options, key="qr_platform")
    cooldown_key = f"last_qr_time_{userid}_{selected_platform}"
    last_qr_time = st.session_state.get(cooldown_key, 0)
    cooldown_remaining = int(cooldown_seconds - (now - last_qr_time))

    if st.sidebar.button("Generate QR Code"):
        if cooldown_remaining > 0:
            st.sidebar.info(f"Please wait {cooldown_remaining // 60}:{cooldown_remaining % 60:02d} minutes before generating a new QR code.")
        else:
            if "web_monitor" not in st.session_state:
                web_monitor = WebMonitor(username=userid, password=password)
                try:
                    login_result = asyncio.run(web_monitor.login())
                    if login_result.get("status") == "success":
                        st.session_state["web_monitor"] = web_monitor
                    else:
                        st.sidebar.error("Login failed. Cannot generate QR code.")
                        return
                except Exception as e:
                    st.sidebar.error(f"Login error: {str(e)}")
                    return
            else:
                web_monitor = st.session_state["web_monitor"]

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
    # Always show the last QR code if it exists
    # if "last_qr_code" in st.session_state and st.session_state["last_qr_code"] is not None:
    #     print(st.session_state["last_qr_code"])
    #     st.sidebar.image(st.session_state["last_qr_code"], caption="Generated QR Code", use_container_width=True)
    #     st.sidebar.info("This QR code is valid for 5 minutes. Please generate a new one if needed.")
    # Show cooldown info if needed
    # if cooldown_remaining > 0:
    #     st.sidebar.info(f"Please wait {cooldown_remaining // 60}:{cooldown_remaining % 60:02d} minutes before generating a new QR code.")

    # # Sidebar: Filter by ProjectID
    # st.sidebar.header("Filter by Project")
    # if len(project_ids) > 0:
    #     selected_projects = st.sidebar.selectbox("Select a Project", projects_names, key="project_filter")
    #     selected_project = projects_df[projects_df['ProjectName'] == selected_projects].iloc[0]
    #     st.sidebar.markdown("### Project Information")
    #     st.sidebar.markdown(f"**Researcher:** {selected_project['LeadResearcher']}")
    #     st.sidebar.markdown(f"**Description:** {selected_project['Description']}")
    #     selected_project_id = selected_project['ProjectID']
    # else:
    #     st.sidebar.markdown("No projects available.")
    #     selected_project_id = None

    # # Filters
    # st.header("My Chats")
    # st.markdown("### 🔍 Filter Your Chats")
    # search_text = st.text_input("Search by chat name")
    # donation_filter = st.selectbox("Filter by donation status", ["All", "Donated", "Not Donated"])

    # # Apply filters
    # if selected_project_id:
    #     filtered_df = chats_df[chats_df['ProjectID'] == selected_project_id]  # Filter by selected ProjectID
    #     if search_text:
    #         filtered_df = filtered_df[filtered_df['ChatName'].str.contains(search_text, case=False)]

    #     if donation_filter == "Donated":
    #         filtered_df = filtered_df[filtered_df['Donated'] == True]
    #     elif donation_filter == "Not Donated":
    #         filtered_df = filtered_df[filtered_df['Donated'] == False]
    # else:
    #     filtered_df = chats_df  # Empty DataFrame if no projects

    # # Display and edit table
    # editable_cols = ['Donated', 'StartDate']
    # displayed_cols = ['ChatID', 'ChatName'] + editable_cols

    # st.markdown("### ☑️ Chats Picker")
    # edited_df = st.data_editor(
    #     filtered_df[displayed_cols] if not filtered_df.empty else pd.DataFrame(columns=displayed_cols),
    #     use_container_width=True,
    #     num_rows="fixed",
    #     column_config={
    #         "StartDate": st.column_config.DateColumn("Start Date"),
    #         "Donated": st.column_config.CheckboxColumn("Donated"),
    #     },
    #     disabled=["ChatName"],
    #     hide_index=True
    # )

    # # Save button logic
    # if not filtered_df.empty and st.button("Save Changes"):
    #     for _, row in edited_df.iterrows():
    #         chat_id = row["ChatID"]
    #         original_row = chats_df.loc[chats_df["ChatID"] == chat_id].iloc[0]

    #         if (
    #             row["Donated"] != original_row["Donated"]
    #             or row["StartDate"] != pd.to_datetime(original_row["StartDate"]).date()
    #         ):
    #             # Update the database with the changes
    #             dbs.update_chat(
    #                 chat_id=chat_id,
    #                 donated=bool(row["Donated"]),  # Ensure boolean conversion
    #                 start_date=row["StartDate"]
    #             )
    #             st.toast(f"Saved changes for chat: {row['ChatName']}", icon="✅")