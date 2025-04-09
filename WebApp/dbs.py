import pandas as pd
import bcrypt
from streamlit_authenticator import Hasher

chats = {
    'UserID': ['user1', 'user1', 'user2'],
    'ChatID': ['chat1', 'chat3', 'chat2'],
    'ChatName': ['Chat Name 1', 'Chat Name 3' ,'Chat Name 2'],
    'ChatDescription': ['Description 1', 'Description 3', 'Description 2'],
    'Total Messages': [100, 150, 200],
    "Donated?": [True, False, True],
    "Start Date": ['2023-01-01', '2023-02-01', '2023-03-01']
}

users = {
    'UserID': ['user1', 'user2'],
    'Email': ['user1@mail.com', 'user2@mail.com'],
    'Username': ['User1', 'User2'],
    'HashedPassword': [bcrypt.hashpw('password1'.encode('utf-8'), bcrypt.gensalt()), bcrypt.hashpw('password2'.encode('utf-8'), bcrypt.gensalt())],
    'Role': ['User', 'Researcher'],
    'Active?': [True, True]
}

chats_df = pd.DataFrame(chats)
users_df = pd.DataFrame(users)

# # Example for hashing all user passwords (only do once and store back in DB)
# plain_passwords = users_df["Password"].tolist()
# hasher = Hasher()
# users_df["HashedPassword"] = list(map(hasher.hash, users_df["Password"]))