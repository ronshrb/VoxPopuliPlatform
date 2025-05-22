import sqlalchemy
from google.cloud.sql.connector import Connector
from sqlalchemy import Table, Column, Integer, String, Boolean, Date, MetaData, create_engine, update
from sqlalchemy.sql import insert, select
from datetime import datetime, timedelta
import os
import connectors

postgres_conn = connectors.postgres_connector()
postgres_pool = postgres_conn.create_engine()

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

# # Define the messages table
# messages_table = Table(
#     "messages",
#     metadata,
#     Column("MessageID", Integer, primary_key=True, autoincrement=True),
#     Column("ChatID", Integer, nullable=False),
#     Column("UserID", Integer, nullable=False),
#     Column("Message", String, nullable=False),
#     Column("Timestamp", String, nullable=False),
#     Column("Sentiment", String, nullable=False),
# )

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

# # Create tables in the database
# with pool.connect() as connection:
#     metadata.create_all(connection)

# Function to add a user
def add_user(email, username, hashed_password, role, active=True):
    with postgres_pool.connect() as connection:
        stmt = insert(users_table).values(
            Email=email,
            Username=username,
            HashedPassword=hashed_password,
            Role=role,
            Active=active,
            CreatedAt=datetime.now().date()
        )
        connection.execute(stmt)
        connection.commit()


# Function to fetch all users
def get_users():
    with postgres_pool.connect() as connection:
        stmt = select(users_table)
        result = connection.execute(stmt)
        return [dict(row._mapping) for row in result]

# Function to add a chat
def add_chat(user_id, chat_name, chat_description, project_id=None):
    with postgres_pool.connect() as connection:
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
        connection.commit()

# Function to fetch all chats for a user
def get_user_chats(user_id):
    with postgres_pool.connect() as connection:
        stmt = select(chats_table).where(chats_table.c.UserID == user_id)
        result = connection.execute(stmt)
        return [dict(row._mapping) for row in result]
    
def update_chat(chat_id, donated, start_date):
    with postgres_pool.connect() as connection:
        stmt = update(chats_table).where(chats_table.c.ChatID == chat_id).values(
            Donated=donated,
            StartDate=start_date,
            LastUpdated=datetime.now().date()
        )
        connection.execute(stmt)
        connection.commit()



# Function to get a user by email (case-insensitive)
def get_user_by_email(email):
    with postgres_pool.connect() as connection:
        stmt = select(users_table).where(users_table.c.Email==email)
        result = connection.execute(stmt).fetchone()
        return dict(result._mapping) if result else None

# Function to fetch all projects
def get_projects():
    with postgres_pool.connect() as connection:
        stmt = select(projects_table)
        result = connection.execute(stmt)
        return [dict(row._mapping) for row in result]
    

# Function to fetch all chats for a specific project
def get_project_chats(project_id):
    with postgres_pool.connect() as connection:
        stmt = select(chats_table).where(chats_table.c.ProjectID == project_id)
        result = connection.execute(stmt)
        return [dict(row._mapping) for row in result]


def get_users_by_project(project_id):
    with postgres_pool.connect() as connection:
        # Join users_table and chats_table on UserID, and filter by ProjectID
        stmt = (
            select(users_table)
            .join(chats_table, users_table.c.UserID == chats_table.c.UserID)
            .where(chats_table.c.ProjectID == project_id)
        )
        result = connection.execute(stmt)
        # Return the list of users as dictionaries
        return [dict(row._mapping) for row in result]
    
# Function to fetch a project by its ID
def get_project_by_id(project_id):
    with postgres_pool.connect() as connection:
        stmt = select(projects_table).where(projects_table.c.ProjectID == project_id)
        result = connection.execute(stmt).fetchone()
        return dict(result._mapping) if result else None
    
# Function to fetch a user by their ID
def get_user_by_id(user_id):
    with postgres_pool.connect() as connection:
        stmt = select(users_table).where(users_table.c.UserID == user_id)
        result = connection.execute(stmt).fetchone()
        return dict(result._mapping) if result else None
    
# Function to fetch a chat by its ID
def get_chat_by_id(chat_id):
    with postgres_pool.connect() as connection:
        stmt = select(chats_table).where(chats_table.c.ChatID == chat_id)
        result = connection.execute(stmt).fetchone()
        return dict(result._mapping) if result else None

# Function to fetch all projects for a specific researcher
def get_researcher_projects(researcher_id):
    with postgres_pool.connect() as connection:
        stmt = select(projects_table).where(projects_table.c.LeadResearcher == researcher_id)
        result = connection.execute(stmt)
        return [dict(row._mapping) for row in result]