import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import pandas as pd
import dbs
from datetime import datetime


def generate_join_qr_code(user_data):
    """Generate a QR code for joining a project."""
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(user_data)
    qr.make(fit=True)

    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to BytesIO object
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)

    return buffered


def user_app(email):
    # Safer lookup with error handling
    user_matches = dbs.get_user_by_email(email)

    if user_matches.empty:
        st.error(f"User with email {email} not found in the database.")
        st.write("Please log out and log in again.")
        if st.button("Logout", key="user_not_found_logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.session_state["email"] = None
            st.rerun()
        return

    # Get user information
    username = user_matches['Username'].values[0]
    userid = user_matches['UserID'].values[0]

    # Initialize join project state
    if "join_project_mode" not in st.session_state:
        st.session_state["join_project_mode"] = False

    # Handle join project mode
    if st.session_state["join_project_mode"]:
        st.title("Join New Project")
        st.markdown("Enter the name of the project you want to join")

        project_name = st.text_input("Project Name", key="join_project_name")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Generate QR Code", key="generate_join_qr"):
                if not project_name:
                    st.error("Please enter a project name")
                else:
                    # Create user data for QR code - in production this would be encrypted
                    user_data = f"UserID:{userid}|Username:{username}|Email:{email}|Project:{project_name}"

                    # Generate QR code
                    qr_buffer = generate_join_qr_code(user_data)

                    # Display QR code
                    st.success(f"QR code generated for joining {project_name}")
                    st.image(qr_buffer, caption=f"Join {project_name} QR Code", width=300)

                    st.info(
                        "In a production environment, this QR code would contain cryptographic information to securely validate your request.")

        with col2:
            if st.button("Back to Dashboard", key="back_to_dashboard"):
                st.session_state["join_project_mode"] = False
                st.rerun()

        return

    # Regular user app view
    # Find user's chats
    user_chats = dbs.get_user_chats(userid)

    if len(user_chats) == 0:
        # No chats found, create a default one
        st.warning("No chats found for this user. Creating a default chat.")

        # Get available projects
        projects_df = dbs.get_projects_df()
        default_project = projects_df['ProjectID'].iloc[0] if not projects_df.empty else "default"

        new_chat = {
            'UserID': userid,
            'ChatID': f"chat{len(dbs.get_chats_df()) + 1}",
            'ChatName': f"Welcome Chat for {username}",
            'ChatDescription': "Your first chat in VoxPopuli",
            'Total Messages': 0,
            'Donated?': False,
            'Start Date': datetime.now().strftime('%Y-%m-%d'),
            'Last Updated': datetime.now().strftime('%Y-%m-%d'),
            'Project ID': default_project
        }
        # Add chat to database
        dbs.add_chat(new_chat)

        # Update user_chats
        user_chats = dbs.get_user_chats(userid)

    # Convert data types
    user_chats['Donated?'] = user_chats['Donated?'].astype(bool)
    user_chats['Start Date'] = pd.to_datetime(user_chats['Start Date'], errors='coerce').dt.date
    if 'Last Updated' in user_chats.columns:
        user_chats['Last Updated'] = pd.to_datetime(user_chats['Last Updated'], errors='coerce').dt.date

    # Page title and welcome
    st.title("User Dashboard")
    st.success(f"Welcome, {username}!")

    # Sidebar with user info and join projects button
    st.sidebar.markdown(f"### User Profile")
    st.sidebar.markdown(f"**Username:** {username}")
    st.sidebar.markdown(f"**Email:** {email}")
    st.sidebar.markdown(f"**ID:** {userid}")

    if st.sidebar.button("Join Other Projects", key="join_projects_btn"):
        st.session_state["join_project_mode"] = True
        st.rerun()

    # Main view
    # Get all projects
    projects_df = dbs.get_projects_df()

    # Get list of projects this user is involved in
    user_project_ids = []
    if 'Project ID' in user_chats.columns:
        user_project_ids = user_chats['Project ID'].unique().tolist()

    # Filter projects to only show those the user is involved in
    if user_project_ids:
        user_projects_df = projects_df[projects_df['ProjectID'].isin(user_project_ids)]
    else:
        # If user has no projects yet, show a message
        st.warning("You are not currently participating in any projects.")
        return

    if user_projects_df.empty:
        st.warning("You are not currently participating in any projects.")
        return

    # Create mapping of project names to IDs
    project_options = user_projects_df['ProjectName'].tolist()
    projects_dict = dict(zip(user_projects_df['ProjectName'], user_projects_df['ProjectID']))

    # Show number of projects
    st.info(f"You are participating in {len(user_projects_df)} project(s).")

    # Project selection
    selected_project_name = st.selectbox(
        "Select a Project",
        project_options,
        key="project_select",
        format_func=lambda x: f"{x} ({projects_dict[x]})"
    )

    if selected_project_name:
        project_id = projects_dict[selected_project_name]
        project_details = projects_df[projects_df['ProjectID'] == project_id]

        # Project details
        st.subheader(f"Project: {selected_project_name}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Description:** {project_details['Description'].values[0]}")
            st.markdown(f"**Status:** {project_details['Status'].values[0]}")

        with col2:
            # Get researcher name
            lead_researcher_id = project_details['LeadResearcher'].values[0]
            lead_researcher = dbs.get_users_df()[dbs.get_users_df()['UserID'] == lead_researcher_id]
            if not lead_researcher.empty:
                st.markdown(f"**Lead Researcher:** {lead_researcher['Username'].values[0]}")

            st.markdown(f"**Start Date:** {project_details['StartDate'].values[0]}")

        # Filter user chats to just this project
        if 'Project ID' in user_chats.columns:
            project_user_chats = user_chats[user_chats['Project ID'] == project_id].copy()
        else:
            project_user_chats = user_chats.copy()
            st.warning("Project filtering unavailable - showing all chats")

        # Show number of chats in this project
        st.info(f"You have {len(project_user_chats)} chat(s) in this project.")

        # Chat section
        st.markdown("---")
        st.subheader("Your Chats")

        # Filters
        st.markdown("### 🔍 Filter Your Chats")
        col1, col2 = st.columns(2)

        with col1:
            search_text = st.text_input("Search by chat name", key="search_chat")

        with col2:
            donation_filter = st.selectbox(
                "Filter by donation status",
                ["All", "Donated", "Not Donated"],
                key="donation_filter"
            )

        filtered_df = project_user_chats.copy()
        if search_text:
            filtered_df = filtered_df[filtered_df['ChatName'].str.contains(search_text, case=False)]

        if donation_filter == "Donated":
            filtered_df = filtered_df[filtered_df['Donated?'] == True]
        elif donation_filter == "Not Donated":
            filtered_df = filtered_df[filtered_df['Donated?'] == False]

        # Display and edit table
        editable_cols = ['Donated?']
        if 'Last Updated' in filtered_df.columns:
            displayed_cols = ['ChatID', 'ChatName', 'Total Messages', 'Start Date', 'Last Updated'] + editable_cols
        else:
            displayed_cols = ['ChatID', 'ChatName', 'Total Messages', 'Start Date'] + editable_cols

        # Filter columns to only include those that exist
        displayed_cols = [col for col in displayed_cols if col in filtered_df.columns]

        if len(filtered_df) > 0:
            edited_df = st.data_editor(
                filtered_df[displayed_cols],
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "Start Date": st.column_config.DateColumn("Start Date"),
                    "Last Updated": st.column_config.DateColumn(
                        "Last Updated") if 'Last Updated' in filtered_df.columns else None,
                    "Donated?": st.column_config.CheckboxColumn("Donated?"),
                    "Total Messages": st.column_config.NumberColumn("Messages"),
                },
                disabled=[col for col in displayed_cols if col != 'Donated?'],
                hide_index=True,
                key="chat_editor"
            )

            # Auto-save logic: update only changed rows
            chats_df = dbs.get_chats_df()
            for _, row in edited_df.iterrows():
                chat_id = row["ChatID"]
                original_row = chats_df.loc[chats_df["ChatID"] == chat_id].iloc[0]

                if row["Donated?"] != original_row["Donated?"]:
                    # Update the chat in session state
                    chats_df.loc[chats_df["ChatID"] == chat_id, "Donated?"] = row["Donated?"]
                    dbs.update_chats_df(chats_df)
                    st.toast(f"Saved changes for chat: {row['ChatName']}", icon="✅")
        else:
            st.info("No chats match your filter criteria.")