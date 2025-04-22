import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
import qrcode
import dbs


def user_app(email):
    """Main function for the User Dashboard."""
    # Fetch user data
    user_data = dbs.get_user_by_email(email)

    if not user_data:
        st.error(f"User with email {email} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="user_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["email"] = None
            st.rerun()
        return

    # Get user information
    username = user_data['Username']
    userid = user_data['UserID']

    # Fetch user's chats
    user_chats = dbs.get_user_chats(userid)

    # Convert chats to a DataFrame (empty DataFrame if no chats)
    chats_df = pd.DataFrame(user_chats) if user_chats else pd.DataFrame(columns=['ChatID', 'ChatName', 'Donated', 'StartDate', 'ProjectID'])
    chats_df['Donated'] = chats_df['Donated'].astype(bool)
    chats_df['StartDate'] = pd.to_datetime(chats_df['StartDate'], errors='coerce').dt.date

    # Fetch project details
    project_ids = chats_df['ProjectID'].unique() if not chats_df.empty else []
    projects = dbs.get_projects()  # Fetch all projects from the database
    projects_df = pd.DataFrame(projects)
    projects_names = projects_df['ProjectName'].unique() if not projects_df.empty else []

    # Page title
    st.title("User Dashboard")
    st.sidebar.success(f"Welcome, {username}!")

    # Sidebar QR Code
    if st.sidebar.button("Generate QR Code"):
        qr = qrcode.make(f"User: {username}")
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        st.sidebar.image(Image.open(buffer), caption="Your QR Code")

    # Sidebar: Filter by ProjectID
    st.sidebar.header("Filter by Project")
    if len(project_ids) > 0:
        selected_projects = st.sidebar.selectbox("Select a Project", projects_names, key="project_filter")
        selected_project = projects_df[projects_df['ProjectName'] == selected_projects].iloc[0]
        st.sidebar.markdown("### Project Information")
        st.sidebar.markdown(f"**Researcher:** {selected_project['LeadResearcher']}")
        st.sidebar.markdown(f"**Description:** {selected_project['Description']}")
        selected_project_id = selected_project['ProjectID']
    else:
        st.sidebar.markdown("No projects available.")
        selected_project_id = None

    # Filters
    st.header("My Chats")
    st.markdown("### 🔍 Filter Your Chats")
    search_text = st.text_input("Search by chat name")
    donation_filter = st.selectbox("Filter by donation status", ["All", "Donated", "Not Donated"])

    # Apply filters
    if selected_project_id:
        filtered_df = chats_df[chats_df['ProjectID'] == selected_project_id]  # Filter by selected ProjectID
        if search_text:
            filtered_df = filtered_df[filtered_df['ChatName'].str.contains(search_text, case=False)]

        if donation_filter == "Donated":
            filtered_df = filtered_df[filtered_df['Donated'] == True]
        elif donation_filter == "Not Donated":
            filtered_df = filtered_df[filtered_df['Donated'] == False]
    else:
        filtered_df = chats_df  # Empty DataFrame if no projects

    # Display and edit table
    editable_cols = ['Donated', 'StartDate']
    displayed_cols = ['ChatName'] + editable_cols

    st.markdown("### ☑️ Chats Picker")
    edited_df = st.data_editor(
        filtered_df[displayed_cols] if not filtered_df.empty else pd.DataFrame(columns=displayed_cols),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "StartDate": st.column_config.DateColumn("Start Date"),
            "Donated": st.column_config.CheckboxColumn("Donated"),
        },
        disabled=["ChatName"],
        hide_index=True
    )

    # Save button logic
    if not filtered_df.empty and st.button("Save Changes"):
        for _, row in edited_df.iterrows():
            chat_id = row["ChatID"]
            original_row = chats_df.loc[chats_df["ChatID"] == chat_id].iloc[0]

            if (
                row["Donated"] != original_row["Donated"]
                or row["StartDate"] != pd.to_datetime(original_row["StartDate"]).date()
            ):
                # Update the database with the changes
                dbs.update_chat(
                    chat_id=chat_id,
                    donated=bool(row["Donated"]),  # Ensure boolean conversion
                    start_date=row["StartDate"]
                )
                st.toast(f"Saved changes for chat: {row['ChatName']}", icon="✅")