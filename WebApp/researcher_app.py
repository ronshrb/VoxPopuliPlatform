import pandas as pd
import bcrypt
import streamlit as st
from dbs import *


def register_user(username, email, password):
    # Check if the username already exists
    if username in users_df['Username'].values:
        st.error("Username already exists.")
        return False

    # Check if the email already exists
    if email in users_df['Email'].values:
        st.error("Email already in use.")
        return False

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Add new user to the DataFrame (or your actual DB)
    new_user = {
        'UserID': f'user{len(users_df) + 1}',  # Generate new UserID
        'Email': email,
        'Username': username,
        'HashedPassword': hashed_password,
        'Role': 'User',  # You can modify the role based on logic
        'Active?': True
    }

    # Append new user to the DataFrame (you'd usually update your DB here)
    users_df.loc[len(users_df)] = new_user

    st.success(f"User {username} registered successfully.")
    return True


def researcher_app(username):
    st.title("Researcher Dashboard")
    st.success(f"Welcome, {username}!")

    # Project Pages
    st.header("Projects")
    project = st.selectbox("Select a Project", ["Project A", "Project B"])
    if project:
        st.subheader(f"Dashboard for {project}")
        st.write("Number of Users: 10")
        st.write("Number of Chats: 50")

        if st.button("Export Data"):
            st.success("Data exported successfully.")

        search_subject = st.text_input("Search Chats by Subject")
        if st.button("Search"):
            st.write(f"Results for '{search_subject}': Example chat data.")

        # Register User functionality
        if st.button("Register User"):
            with st.form(key="register_user_form"):
                username_input = st.text_input("Username")
                email_input = st.text_input("Email")
                password_input = st.text_input("Password", type="password")
                submit_button = st.form_submit_button(label="Register")

                if submit_button:
                    if username_input and email_input and password_input:
                        if register_user(username_input, email_input, password_input):
                            st.success(f"User {username_input} has been registered.")
                    else:
                        st.error("Please fill out all fields.")
