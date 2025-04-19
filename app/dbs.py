import pandas as pd
import bcrypt
import streamlit as st
import random
from datetime import datetime, timedelta


# Generate dummy data with more users, chats, and messages
def init_data():
    # Create dummy users
    num_users = 50  # 50 users total
    user_ids = [f"user{i + 1}" for i in range(num_users)]

    # Divide users into regular users and researchers
    # Ensure researchers have consistent IDs (user41-user50)
    user_roles = ["User"] * 40 + ["Researcher"] * 10

    # Generate usernames, emails, and passwords
    usernames = [f"User{i + 1}" for i in range(num_users)]
    emails = [f"user{i + 1}@example.com" for i in range(num_users)]

    # For development/testing, use a fixed salt to ensure password consistency
    # In production, you would use bcrypt.gensalt() for each password
    fixed_salt = bcrypt.gensalt()

    # Hash passwords (all "password123" for simplicity)
    hashed_passwords = []
    for _ in range(num_users):
        hashed_password = bcrypt.hashpw('password123'.encode('utf-8'), fixed_salt)
        hashed_passwords.append(hashed_password)

    # Create users dataframe
    users = {
        'UserID': user_ids,
        'Email': emails,
        'Username': usernames,
        'HashedPassword': hashed_passwords,
        'Role': user_roles,
        'Active?': [True] * num_users,
        'Created At': [(datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d') for _ in
                              range(num_users)]
    }

    # Create dummy chats (multiple chats per user)
    chat_id_counter = 1
    chats = {
        'UserID': [],
        'ChatID': [],
        'ChatName': [],
        'ChatDescription': [],
        'Total Messages': [],
        'Donated?': [],
        'Start Date': [],
        'Last Updated': [],
        'Project ID': []
    }

    # List of dummy project IDs
    project_ids = ["project_linguistics", "project_psychology", "project_sociology", "project_survey"]

    # Chat topics for random selection
    chat_topics = [
        "Political opinions", "Climate change", "Healthcare", "Education",
        "Technology", "Social media", "Immigration", "Economy",
        "Entertainment", "Sports", "Food preferences", "Travel experiences",
        "Housing market", "Employment", "Public transportation", "Environment"
    ]

    # Generate 200 chats distributed among users
    for _ in range(200):
        # Select a random user (users with lower IDs get more chats for realism)
        user_idx = int(random.triangular(0, num_users - 1, 0))
        user_id = user_ids[user_idx]

        # Create a chat
        chat_id = f"chat{chat_id_counter}"
        chat_id_counter += 1

        # Select a random topic
        topic = random.choice(chat_topics)
        chat_name = f"Chat about {topic}"
        chat_description = f"Discussion regarding {topic} and related subjects"

        # Randomize other properties
        total_messages = random.randint(5, 100)
        donated = random.random() > 0.7  # 30% chance of being donated

        # Random date in the past year
        start_date = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')
        last_updated = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=random.randint(1, 30))).strftime(
            '%Y-%m-%d')

        # Select a random project
        project_id = random.choice(project_ids)

        # Add chat to list
        chats['UserID'].append(user_id)
        chats['ChatID'].append(chat_id)
        chats['ChatName'].append(chat_name)
        chats['ChatDescription'].append(chat_description)
        chats['Total Messages'].append(total_messages)
        chats['Donated?'].append(donated)
        chats['Start Date'].append(start_date)
        chats['Last Updated'].append(last_updated)
        chats['Project ID'].append(project_id)

    # Create messages dataframe
    messages = {
        'MessageID': [],
        'ChatID': [],
        'UserID': [],
        'Message': [],
        'Timestamp': [],
        'Sentiment': []
    }

    # Message templates for generating dummy content
    opinion_starters = [
        "I think that", "In my opinion,", "I believe", "It seems to me that",
        "From my perspective,", "I would say that", "My view is that",
        "I feel that", "My take on this is", "I'd argue that"
    ]

    opinion_contents = [
        "we should focus more on sustainable solutions.",
        "there are multiple factors to consider here.",
        "this is a complex issue with no easy answers.",
        "the data suggests a different approach might work better.",
        "historical precedent doesn't apply in this situation.",
        "community involvement is essential for success.",
        "education plays a critical role in addressing this.",
        "technology offers promising solutions to this problem.",
        "economic considerations cannot be ignored.",
        "public health should be our priority.",
        "the environmental impact must be carefully assessed.",
        "we need more research before drawing conclusions.",
        "cultural factors significantly influence outcomes here.",
        "policy reforms are urgently needed.",
        "a balanced approach would yield better results.",
        "international cooperation is necessary.",
        "local initiatives often have the greatest impact.",
        "media coverage has distorted public perception on this issue.",
        "ethical considerations should guide our decisions.",
        "incremental changes are more sustainable long-term."
    ]

    followups = [
        "What do you think?",
        "Has that been your experience too?",
        "Do you agree with this assessment?",
        "I'd be interested in hearing other perspectives.",
        "This is based on my personal experience.",
        "Research seems to support this view.",
        "I'm still learning about this topic.",
        "I've changed my mind about this recently.",
        "There are certainly exceptions to this.",
        "This view might be controversial."
    ]

    sentiments = ["Positive", "Negative", "Neutral", "Mixed"]

    # Generate messages for each chat
    message_id_counter = 1
    for idx, chat in enumerate(chats['ChatID']):
        user_id = chats['UserID'][idx]
        total_msgs = chats['Total Messages'][idx]

        # Generate random messages for this chat
        for _ in range(total_msgs):
            message_id = f"msg{message_id_counter}"
            message_id_counter += 1

            # Generate a random message
            opinion = f"{random.choice(opinion_starters)} {random.choice(opinion_contents)} {random.choice(followups)}"

            # Random timestamp between start date and last updated
            start = datetime.strptime(chats['Start Date'][idx], '%Y-%m-%d')
            end = datetime.strptime(chats['Last Updated'][idx], '%Y-%m-%d')
            msg_timestamp = start + (end - start) * random.random()

            # Random sentiment
            sentiment = random.choice(sentiments)

            # Add message to list
            messages['MessageID'].append(message_id)
            messages['ChatID'].append(chat)
            messages['UserID'].append(user_id)
            messages['Message'].append(opinion)
            messages['Timestamp'].append(msg_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            messages['Sentiment'].append(sentiment)

    # Create projects dataframe with consistent lead researchers
    # Always assign specific researchers to specific projects
    projects = {
        'ProjectID': project_ids,
        'ProjectName': ["Linguistic Analysis", "Psychological Study", "Sociological Research", "General Survey"],
        'Description': [
            "Analyzing language patterns in online discussions",
            "Study of psychological responses to various topics",
            "Research on social dynamics in online conversations",
            "General opinion survey on various subjects"
        ],
        'LeadResearcher': [
            "user41",  # Always assign user41 to Linguistic Analysis
            "user42",  # Always assign user42 to Psychological Study
            "user43",  # Always assign user43 to Sociological Research
            "user44"  # Always assign user44 to General Survey
        ],
        'StartDate': [
            (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d') for _ in range(4)
        ],
        'Status': ["Active", "Active", "Completed", "Planning"]
    }

    # Convert to dataframes
    users_df = pd.DataFrame(users)
    chats_df = pd.DataFrame(chats)
    messages_df = pd.DataFrame(messages)
    projects_df = pd.DataFrame(projects)

    return users_df, chats_df, messages_df, projects_df


# Initialize data in session state if not already present
if 'users_df' not in st.session_state:
    st.info("Initializing database with dummy data...")
    users_df, chats_df, messages_df, projects_df = init_data()
    st.session_state['users_df'] = users_df
    st.session_state['chats_df'] = chats_df
    st.session_state['messages_df'] = messages_df
    st.session_state['projects_df'] = projects_df


# Functions to access and update the data
def get_users_df():
    return st.session_state['users_df']


def get_chats_df():
    return st.session_state['chats_df']


def get_messages_df():
    return st.session_state['messages_df']


def get_projects_df():
    return st.session_state['projects_df']


def update_users_df(new_df):
    st.session_state['users_df'] = new_df


def update_chats_df(new_df):
    st.session_state['chats_df'] = new_df


def update_messages_df(new_df):
    st.session_state['messages_df'] = new_df


def update_projects_df(new_df):
    st.session_state['projects_df'] = new_df


def add_user(new_user):
    # Add a single user to the dataframe
    users_df = get_users_df()
    new_user_df = pd.DataFrame([new_user])
    updated_df = pd.concat([users_df, new_user_df], ignore_index=True)
    update_users_df(updated_df)
    return updated_df


def add_chat(new_chat):
    # Add a single chat to the dataframe
    chats_df = get_chats_df()
    new_chat_df = pd.DataFrame([new_chat])
    updated_df = pd.concat([chats_df, new_chat_df], ignore_index=True)
    update_chats_df(updated_df)
    return updated_df


def add_message(chat_id, user_id, message_text):
    # Add a single message to the dataframe
    messages_df = get_messages_df()

    # Generate new message ID
    if len(messages_df) == 0:
        new_message_id = "msg1"
    else:
        # Extract the numeric part of the last message ID and increment it
        last_id = messages_df['MessageID'].iloc[-1]
        numeric_part = int(''.join(filter(str.isdigit, last_id)))
        new_message_id = f"msg{numeric_part + 1}"

    # Create new message
    new_message = {
        'MessageID': new_message_id,
        'ChatID': chat_id,
        'UserID': user_id,
        'Message': message_text,
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Sentiment': 'Neutral'  # Default sentiment
    }

    # Add message to dataframe
    new_message_df = pd.DataFrame([new_message])
    updated_df = pd.concat([messages_df, new_message_df], ignore_index=True)
    update_messages_df(updated_df)

    # Update message count in chat
    chats_df = get_chats_df()
    chat_idx = chats_df.index[chats_df['ChatID'] == chat_id].tolist()[0]
    chats_df.at[chat_idx, 'Total Messages'] += 1
    chats_df.at[chat_idx, 'Last Updated'] = datetime.now().strftime('%Y-%m-%d')
    update_chats_df(chats_df)

    return new_message_id


def get_user_by_email(email):
    # Find a user by email (case-insensitive)
    users_df = get_users_df()
    user_matches = users_df[users_df['Email'].str.lower() == email.lower()]
    return user_matches


def get_user_chats(user_id):
    # Get all chats for a specific user
    chats_df = get_chats_df()
    return chats_df[chats_df['UserID'] == user_id].copy()


def get_chat_messages(chat_id):
    # Get all messages for a specific chat
    messages_df = get_messages_df()
    return messages_df[messages_df['ChatID'] == chat_id].copy().sort_values('Timestamp')


def get_project_chats(project_id):
    # Get all chats for a specific project
    chats_df = get_chats_df()
    return chats_df[chats_df['Project ID'] == project_id].copy()


def get_project_details(project_id):
    # Get details for a specific project
    projects_df = get_projects_df()
    return projects_df[projects_df['ProjectID'] == project_id]


# Direct access to the dataframes (for backward compatibility)
users_df = get_users_df()
chats_df = get_chats_df()


# Helper function for debugging passwords
def debug_password(email, input_password):
    """Helper function to debug password issues"""
    user_matches = get_user_by_email(email)
    if not user_matches.empty:
        stored_hash = user_matches.iloc[0]['HashedPassword']
        input_hash = bcrypt.hashpw(input_password.encode('utf-8'), stored_hash)

        result = {
            'email': email,
            'found_user': True,
            'stored_hash_type': type(stored_hash).__name__,
            'input_hash_type': type(input_hash).__name__,
            'stored_hash': str(stored_hash)[:20] + '...',  # First few chars for comparison
            'input_hash': str(input_hash)[:20] + '...',
            'match': input_hash == stored_hash
        }
    else:
        result = {
            'email': email,
            'found_user': False
        }

    return result