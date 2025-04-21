import streamlit as st
import dbs
import bcrypt
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


def user_app(email):
    """Main function for the User Dashboard."""
    # Find user by email
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

    # Page title
    st.title("User Dashboard")
    st.success(f"Welcome, {username}!")

    # Sidebar with options
    menu = st.sidebar.selectbox(
        "Dashboard Menu",
        ["My Chats", "Chat Analytics", "Profile Settings"]
    )

    # My Chats Screen
    if menu == "My Chats":
        st.header("My Chats")
        st.markdown("Here are your active chats:")

        # Fetch user's chats from the database
        user_chats = dbs.get_user_chats(userid)

        if not user_chats:
            st.info("You have no active chats. Start a new one!")
        else:
            # Display chats in a table
            chats_df = pd.DataFrame(user_chats)
            st.dataframe(chats_df[['ChatName', 'ChatDescription', 'TotalMessages', 'LastUpdated']])

            # Option to open a specific chat
            selected_chat = st.selectbox(
                "Select a chat to view details:",
                options=[chat['ChatName'] for chat in user_chats],
                key="select_chat"
            )

            if selected_chat:
                chat_details = next(chat for chat in user_chats if chat['ChatName'] == selected_chat)
                st.subheader(f"Chat: {chat_details['ChatName']}")
                st.markdown(f"**Description:** {chat_details['ChatDescription']}")
                st.markdown(f"**Total Messages:** {chat_details['TotalMessages']}")
                st.markdown(f"**Last Updated:** {chat_details['LastUpdated']}")

                # Fetch messages for the selected chat
                chat_messages = dbs.get_chat_messages(chat_details['ChatID'])

                if not chat_messages:
                    st.info("No messages in this chat yet.")
                else:
                    messages_df = pd.DataFrame(chat_messages)
                    st.dataframe(messages_df[['UserID', 'Message', 'Timestamp', 'Sentiment']])

    # Chat Analytics Screen
    elif menu == "Chat Analytics":
        st.header("Chat Analytics")
        st.markdown("Analyze your chat activity and sentiment trends.")

        # Fetch user's chats
        user_chats = dbs.get_user_chats(userid)

        if not user_chats:
            st.info("You have no chats to analyze.")
        else:
            # Collect all messages from user's chats
            chat_ids = [chat['ChatID'] for chat in user_chats]
            user_messages = dbs.get_messages_by_chat_ids(chat_ids)

            if not user_messages:
                st.info("No messages to analyze.")
            else:
                # Convert messages to a DataFrame
                messages_df = pd.DataFrame(user_messages)

                # Sentiment distribution
                st.subheader("Sentiment Distribution")
                sentiment_counts = messages_df['Sentiment'].value_counts()
                fig, ax = plt.subplots()
                sentiment_counts.plot(kind='bar', ax=ax, color=['#5cb85c', '#d9534f', '#5bc0de', '#f0ad4e'])
                ax.set_title("Sentiment Distribution")
                ax.set_ylabel("Number of Messages")
                ax.set_xlabel("Sentiment")
                st.pyplot(fig)

                # Chat activity over time
                st.subheader("Chat Activity Over Time")
                messages_df['Timestamp'] = pd.to_datetime(messages_df['Timestamp'])
                daily_activity = messages_df.groupby(messages_df['Timestamp'].dt.date).size()
                fig, ax = plt.subplots()
                daily_activity.plot(kind='line', ax=ax, marker='o', linestyle='-', color='#337ab7')
                ax.set_title("Chat Activity Over Time")
                ax.set_ylabel("Number of Messages")
                ax.set_xlabel("Date")
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig)

    # Profile Settings Screen
    elif menu == "Profile Settings":
        st.header("Profile Settings")
        st.markdown("Update your profile information or change your password.")

        # Display current profile information
        st.subheader("Profile Information")
        st.markdown(f"**Username:** {username}")
        st.markdown(f"**Email:** {user_data['Email']}")
        st.markdown(f"**Role:** {user_data['Role']}")

        # Option to change password
        st.subheader("Change Password")
        current_password = st.text_input("Current Password", type="password", key="current_password")
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_new_password = st.text_input("Confirm New Password", type="password", key="confirm_new_password")

        if st.button("Update Password"):
            if not current_password or not new_password or not confirm_new_password:
                st.error("Please fill in all fields.")
            elif new_password != confirm_new_password:
                st.error("New passwords do not match.")
            else:
                # Verify current password
                if bcrypt.checkpw(current_password.encode('utf-8'), user_data['HashedPassword'].encode('utf-8')):
                    # Hash the new password
                    hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                    # Update the password in the database
                    dbs.update_user_password(userid, hashed_new_password)
                    st.success("Password updated successfully!")
                else:
                    st.error("Current password is incorrect.")