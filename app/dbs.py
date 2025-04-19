import sqlalchemy
from google.cloud.sql.connector import Connector
from sqlalchemy import Table, Column, Integer, String, Boolean, Date, MetaData, create_engine
from sqlalchemy.sql import insert, select
from datetime import datetime, timedelta
import os

# Initialize Cloud SQL Connector and database connection
connector = Connector()

db_user = os.environ["users_db_user"]
db_pass = os.environ["users_db_pass"]  # comes securely from Secret Manager

def getconn():
    conn = connector.connect(
        "YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME",
        "pg8000",
        user=db_user,
        password=db_pass,
        db="users"
    )
    return conn

pool = create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

metadata = MetaData()

# Define the users table
users_table = Table(
    "users",
    metadata,
    Column("UserID", Integer, primary_key=True, autoincrement=True),
    Column("Email", String, nullable=False, unique=True),
    Column("Username", String, nullable=False, unique=True),
    Column("HashedPassword", String, nullable=False),
    Column("Role", String, nullable=False),
    Column("Active", Boolean, nullable=False),
    Column("CreatedAt", Date, nullable=False),
)

# Define the chats table
chats_table = Table(
    "chats",
    metadata,
    Column("ChatID", Integer, primary_key=True, autoincrement=True),
    Column("UserID", Integer, nullable=False),
    Column("ChatName", String, nullable=False),
    Column("ChatDescription", String, nullable=True),
    Column("TotalMessages", Integer, nullable=False, default=0),
    Column("Donated", Boolean, nullable=False, default=False),
    Column("StartDate", Date, nullable=False),
    Column("LastUpdated", Date, nullable=False),
    Column("ProjectID", String, nullable=True),
)

# Define the messages table
messages_table = Table(
    "messages",
    metadata,
    Column("MessageID", Integer, primary_key=True, autoincrement=True),
    Column("ChatID", Integer, nullable=False),
    Column("UserID", Integer, nullable=False),
    Column("Message", String, nullable=False),
    Column("Timestamp", String, nullable=False),
    Column("Sentiment", String, nullable=False),
)

# Define the projects table
projects_table = Table(
    "projects",
    metadata,
    Column("ProjectID", String, primary_key=True),
    Column("ProjectName", String, nullable=False),
    Column("Description", String, nullable=True),
    Column("LeadResearcher", String, nullable=False),
    Column("StartDate", Date, nullable=False),
    Column("Status", String, nullable=False),
)

# Create tables in the database
with pool.connect() as connection:
    metadata.create_all(connection)

# Function to add a user
def add_user(email, username, hashed_password, role, active=True):
    with pool.connect() as connection:
        stmt = insert(users_table).values(
            Email=email,
            Username=username,
            HashedPassword=hashed_password,
            Role=role,
            Active=active,
            CreatedAt=datetime.now().date()
        )
        connection.execute(stmt)

# Function to fetch all users
def get_users():
    with pool.connect() as connection:
        stmt = select(users_table)
        result = connection.execute(stmt)
        return [dict(row) for row in result]

# Function to add a chat
def add_chat(user_id, chat_name, chat_description, project_id=None):
    with pool.connect() as connection:
        stmt = insert(chats_table).values(
            UserID=user_id,
            ChatName=chat_name,
            ChatDescription=chat_description,
            TotalMessages=0,
            Donated=False,
            StartDate=datetime.now().date(),
            LastUpdated=datetime.now().date(),
            ProjectID=project_id
        )
        connection.execute(stmt)

# Function to fetch all chats for a user
def get_user_chats(user_id):
    with pool.connect() as connection:
        stmt = select(chats_table).where(chats_table.c.UserID == user_id)
        result = connection.execute(stmt)
        return [dict(row) for row in result]

# Function to add a message
def add_message(chat_id, user_id, message, sentiment="Neutral"):
    with pool.connect() as connection:
        stmt = insert(messages_table).values(
            ChatID=chat_id,
            UserID=user_id,
            Message=message,
            Timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            Sentiment=sentiment
        )
        connection.execute(stmt)

# Function to fetch all messages for a chat
def get_chat_messages(chat_id):
    with pool.connect() as connection:
        stmt = select(messages_table).where(messages_table.c.ChatID == chat_id)
        result = connection.execute(stmt)
        return [dict(row) for row in result]
