import sqlalchemy
from google.cloud.sql.connector import Connector
from sqlalchemy import Table, Column, Integer, String, Boolean, Date, MetaData, create_engine, update
from sqlalchemy.sql import insert, select
from datetime import datetime, timedelta
import os
import connectors
import duckdb
import pandas as pd


# Mongo
mongo_conn = connectors.mongo_connector()

class MongoDBCollection:
    def __init__(self, db_name, collection_name):
        self.client = mongo_conn.get_client()
        self.collection = mongo_conn.get_table(db_name, collection_name)
        self.collection_df = pd.DataFrame(list(self.collection.find()))
    
    def get_collection(self):
        return self.collection_df
    
    def get_collection_df(self):
        return pd.DataFrame(list(self.collection.find()))
    
    def get_collection_by_id(self, item_id):
        item = self.collection.find_one({"_id": item_id})
        return item if item else None
    
    def add_item(self, item_data):
        self.collection.insert_one(item_data)
    
    def update_item(self, item_id, update_data):
        self.collection.update_one({"_id": item_id}, {"$set": update_data})
    
    def delete_item(self, item_id):
        self.collection.delete_one({"_id": item_id})

class MessagesColl(MongoDBCollection):
    def __init__(self, project_id):
        super().__init__('VoxPopuli', project_id)
    
    def get_messages(self):
        return self.collection_df
    
    def get_messages_by_user(self, userid):
        pass

    def get_chats_info(self):
        # Register the DataFrame as a DuckDB table
        duckdb.register("messages_table", self.collection_df)
        
        # Define the query
        q = """
        SELECT room_id "Chat ID", room_name "Chat Name", COUNT(event_id) AS "Total Messages", platform Platform
        FROM messages_table
        GROUP BY room_id, room_name, platform
        """

        return duckdb.query(q).to_df()
    
    def get_users(self):
        q = f"""
        SELECT DISTINCT sender_id, sender_name
        FROM {self.messages_df}
        """
        return duckdb.query(q).to_df()
    
class UsersColl(MongoDBCollection):

    def __init__(self, db_name):
        super().__init__(db_name, 'Users')

    def add_user(self, user_id, hashed_password, creator_id, role='User', active=True):
        user_data = {
            "UserID": user_id,
            'HashedPassword': hashed_password,
            "Role": role,
            "Creator": creator_id,
            "Active": active,
            "CreatedAt": datetime.now() 
        }
        self.collection.insert_one(user_data)

    def get_users(self):
        return self.collection_df
    
    def get_user_by_id(self, user_id):
        user = self.collection.find_one({"UserID": user_id})
        return user if user else None
    
    def get_user_by_email(self, email):
        user = self.collection.find_one({"Email": email})
        return user if user else None
    
    # def user_statistics_by_project(self, project_id):
    #     # Register the DataFrame as a DuckDB table
    #     duckdb.register("users_table", self.users_df)
        
    #     # Define the query
    #     q = f"""
    #     SELECT UserID, COUNT(DISTINCT ChatID) AS TotalChats
    #     FROM users_table
    #     LEFT JOIN messages ON users_table.UserID = messages.Userbridge_userID
    #     WHERE ProjectID = '{project_id}'
    #     GROUP BY UserID
    #     """

    #     return duckdb.query(q).to_df()
    

class ProjectsColl(MongoDBCollection):
    def __init__(self, db_name):
        super().__init__(db_name, 'Projects')

    def add_project(self, project_id, desc, researchers, active=True):
        project_data = {
            "ProjectID": project_id,
            "ProjectName": desc,
            'Researchers': researchers,
            "Users": [],
            "Active": active,
            "CreatedAt": datetime.now()
        }
        self.collection.insert_one(project_data)

    def add_researcher(self, project_id, researcher_id):
        project = self.collection.find_one({"ProjectID": project_id})
        if project:
            researchers = project.get('Researchers', [])
            if researcher_id not in researchers:
                researchers.append(researcher_id)
                self.collection.update_one({"ProjectID": project_id}, {"$set": {"Researchers": researchers}})
    
    def remove_researcher(self, project_id, researcher_id):
        project = self.collection.find_one({"ProjectID": project_id})
        if project:
            researchers = project.get('Researchers', [])
            if researcher_id in researchers:
                researchers.remove(researcher_id)
                self.collection.update_one({"ProjectID": project_id}, {"$set": {"Researchers": researchers}})
    
    def add_user(self, project_id, user_id):
        project = self.collection.find_one({"ProjectID": project_id})
        if project:
            users = project.get('Users', [])
            if user_id not in users:
                users.append(user_id)
                self.collection.update_one({"ProjectID": project_id}, {"$set": {"Users": users}})

    def remove_user(self, project_id, user_id):
        project = self.collection.find_one({"ProjectID": project_id})
        if project:
            users = project.get('Users', [])
            if user_id in users:
                users.remove(user_id)
                self.collection.update_one({"ProjectID": project_id}, {"$set": {"Users": users}})

    def get_users(self):
        users = self.users.find()
        return pd.DataFrame(list(users))

    def get_project_researchers(self, project_id):
        project = self.collection.find_one({"ProjectID": project_id})
        if project:
            return project.get('Researchers', [])
        return []
    
    def get_projects_by_researcher(self, researcher_id):
        projects = self.collection.find({"Researchers": {"$in": [researcher_id]}}, {"ProjectID": 1, "_id": 0})
        return projects
    
    def get_project_by_researcher_df(self, researcher_id):
        projects = self.get_project_researchers(researcher_id)
        return pd.DataFrame(list(projects))
    
    def get_project_by_id(self, project_id):
        project = self.collection.find_one({"ProjectID": project_id})
        return project if project else None
    
    def get_project_by_id_df(self, project_id):
        project = self.get_project_by_id(project_id)
        return pd.DataFrame(list(project)) if project else None
    
    def get_projects(self):
        return self.collection_df


class ChatsColl(MongoDBCollection):
    def __init__(self, db_name):
        super().__init__(db_name, 'Chats')

    def add_chat(self, chat_id, chat_name, platform, user_id, donated=False):
        chat_data = {
            "ChatID": chat_id,
            "Chat Name": chat_name,
            "Platform": platform,
            "UserID": user_id,
            "CreatedAt": datetime.now(),
            "UpdatedAt": datetime.now(),
            "Donated": donated

        }
        self.collection.insert_one(chat_data)

    def update_chat_name(self, chat_id, chat_name):
        self.collection.update_one({"ChatID": chat_id}, {"$set": {"Chat Name": chat_name, "UpdatedAt": datetime.now()}})

    def update_chat_donation(self, chat_id, donated):
        self.collection.update_one({"ChatID": chat_id}, {"$set": {"Donated": donated, "UpdatedAt": datetime.now()}})

    def update_collection(self, chats_dict):
        for chat in chats_dict:
            chat_id = chat.get("ChatID")
            chat_name = chat.get("Chat Name")
            platform = chat.get("Platform")
            user_id = chat.get("UserID")
            donated = chat.get("Donated")
            
            if chat_id:
                self.add_chat(chat_id, chat_name, platform, user_id, donated)
            else:
                self.update_chat_name(chat_id, chat_name)
                # self.update_chat_donation(chat_id, donated)

    def get_chats(self):
        return self.get_collection_df()
    
    def get_chat_by_id(self, chat_id):
        chat = self.collection.find_one({"ChatID": chat_id})
        return chat if chat else None
    
    def get_chat_by_user(self, user_id):
        chat = self.collection.find_one({"UserID": user_id})
        return chat if chat else None
    