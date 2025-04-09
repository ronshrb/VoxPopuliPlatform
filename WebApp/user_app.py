

import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import pandas as pd
from dbs import *

def user_app(email):
    username = users_df.loc[users_df['Email'] == email, 'Username'].values[0]
    userid = users_df.loc[users_df['Email'] == email, 'UserID'].values[0]
    chats = chats_df[chats_df['UserID'] == userid].copy()
    chats['Donated?'] = chats['Donated?'].astype(bool)
    chats['Start Date'] = pd.to_datetime(chats['Start Date'], errors='coerce').dt.date

    st.title("User Dashboard")
    st.success(f"Welcome, {username}!")

    # Sidebar QR Code
    if st.sidebar.button("Generate QR Code"):
        qr = qrcode.make(f"User: {username}")
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        st.sidebar.image(Image.open(buffer), caption="Your QR Code")

    st.header("Projects")
    project = st.selectbox("Select a Project", ["Project A", "Project B"])

    if project:
        st.subheader(f"Details for {project}")
        st.write("Description: Example project description.")
        st.write("Researcher: Dr. Smith")
        st.write("Establishment: Example University")

        # Filters
        st.markdown("### 🔍 Filter Your Chats")
        search_text = st.text_input("Search by chat name")
        donation_filter = st.selectbox("Filter by donation status", ["All", "Donated", "Not Donated"])

        filtered_df = chats.copy()
        if search_text:
            filtered_df = filtered_df[filtered_df['ChatName'].str.contains(search_text, case=False)]

        if donation_filter == "Donated":
            filtered_df = filtered_df[filtered_df['Donated?'] == True]
        elif donation_filter == "Not Donated":
            filtered_df = filtered_df[filtered_df['Donated?'] == False]

        # Display and edit table
        editable_cols = ['Donated?', 'Start Date']
        displayed_cols = ['ChatID', 'ChatName'] + editable_cols

        edited_df = st.data_editor(
            filtered_df[displayed_cols],
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "Start Date": st.column_config.DateColumn("Start Date"),
                "Donated?": st.column_config.CheckboxColumn("Donated?"),
            },
            disabled=["ChatID", "ChatName"],
            hide_index=True
        )

        # Auto-save logic: update only changed rows
        for _, row in edited_df.iterrows():
            chat_id = row["ChatID"]
            original_row = chats_df.loc[chats_df["ChatID"] == chat_id].iloc[0]

            if (
                row["Donated?"] != original_row["Donated?"]
                or row["Start Date"] != pd.to_datetime(original_row["Start Date"]).date()
            ):
                chats_df.loc[chats_df["ChatID"] == chat_id, "Donated?"] = row["Donated?"]
                chats_df.loc[chats_df["ChatID"] == chat_id, "Start Date"] = row["Start Date"]
                st.toast(f"Saved changes for chat: {row['ChatName']}", icon="✅")



        # updated_donated = {}
        #
        # # Show checklist for each chat
        # for _, row in chats.iterrows():
        #     checked = st.checkbox(
        #         label=row["ChatName"],
        #         value=row["Donated?"],
        #         key=f"{row['ChatID']}"
        #     )
        #     updated_donated[row["ChatID"]] = int(checked)
        #
        # if st.button("Update Donation Status"):
        #     for chat_id, donate_value in updated_donated.items():
        #         chats_df.loc[chats_df['ChatID'] == chat_id, 'Donated?'] = donate_value
        #     st.success("Donation statuses updated!")