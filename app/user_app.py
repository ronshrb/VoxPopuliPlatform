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
    if not user_chats:
        st.info("You have no active chats. Start a new one!")
        return

    # Convert chats to a DataFrame
    chats_df = pd.DataFrame(user_chats)
    chats_df['Donated'] = chats_df['Donated'].astype(bool)
    chats_df['StartDate'] = pd.to_datetime(chats_df['StartDate'], errors='coerce').dt.date

    # Page title
    st.title("User Dashboard")
    st.success(f"Welcome, {username}!")

    # Sidebar QR Code
    if st.sidebar.button("Generate QR Code"):
        qr = qrcode.make(f"User: {username}")
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        st.sidebar.image(Image.open(buffer), caption="Your QR Code")

    # Filters
    st.header("My Chats")
    st.markdown("### 🔍 Filter Your Chats")
    search_text = st.text_input("Search by chat name")
    donation_filter = st.selectbox("Filter by donation status", ["All", "Donated", "Not Donated"])

    # Apply filters
    filtered_df = chats_df.copy()
    if search_text:
        filtered_df = filtered_df[filtered_df['ChatName'].str.contains(search_text, case=False)]

    if donation_filter == "Donated":
        filtered_df = filtered_df[filtered_df['Donated'] == True]
    elif donation_filter == "Not Donated":
        filtered_df = filtered_df[filtered_df['Donated'] == False]

    # Display and edit table
    editable_cols = ['Donated', 'StartDate']
    displayed_cols = ['ChatID', 'ChatName'] + editable_cols

    st.markdown("### 📝 Edit Your Chats")
    edited_df = st.data_editor(
        filtered_df[displayed_cols],
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "StartDate": st.column_config.DateColumn("Start Date"),
            "Donated": st.column_config.CheckboxColumn("Donated"),
        },
        disabled=["ChatID", "ChatName"],
        hide_index=True
    )

    # Auto-save logic: update only changed rows
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
                donated=row["Donated"],
                start_date=row["StartDate"]
            )
            st.toast(f"Saved changes for chat: {row['ChatName']}", icon="✅")