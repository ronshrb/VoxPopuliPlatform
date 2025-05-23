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

class MessagesColl:
    def __init__(self, project_id):
        self.project_id = project_id
        self.client = mongo_conn.get_client()
        self.messages = mongo_conn.get_table('VoxPopuli', project_id)
        self.messages_df = pd.DataFrame(list(self.messages.find()))
    
    def get_messages(self):
        return self.messages_df
    
    def get_chats_info(self):
        # Register the DataFrame as a DuckDB table
        duckdb.register("messages_table", self.messages_df)
        
        # Define the query
        q = """
        SELECT room_id ChatID, room_name ChatName, COUNT(event_id) AS total_messages, platform Platform
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
    
class UsersColl:
    def __init__(self, db_name):
        self.client = mongo_conn.get_client()
        self.users = mongo_conn.get_table(db_name, 'Users')
        self.users_df = pd.DataFrame(list(self.users.find()))

    def add_user(self, user_id, email, hashed_password, role, active=True):
        user_data = {
            "UserID": user_id,
            "Email": email,
            'HashedPassword': hashed_password,
            "Role": role,
            "Active": active,
            "CreatedAt": datetime.now() 
        }
        self.users.insert_one(user_data)

    def get_users(self):
        return self.users_df
    
    
    def get_user_by_email(self, email):
        user = self.users.find_one({"Email": email})
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
    

class ProjectsColl:
    def __init__(self, db_name):
        self.client = mongo_conn.get_client()
        self.projects = mongo_conn.get_table(db_name, 'Projects')
        self.projects_df = pd.DataFrame(list(self.projects.find()))

    def add_project(self, project_id, desc, researchers, active=True):
        project_data = {
            "ProjectID": project_id,
            "ProjectName": desc,
            'Researchers': researchers,
            "Users": [],
            "Active": active,
            "CreatedAt": datetime.now()
        }
        self.projects.insert_one(project_data)

    def add_researcher(self, project_id, researcher_id):
        project = self.projects.find_one({"ProjectID": project_id})
        if project:
            researchers = project.get('Researchers', [])
            if researcher_id not in researchers:
                researchers.append(researcher_id)
                self.projects.update_one({"ProjectID": project_id}, {"$set": {"Researchers": researchers}})
    
    def remove_researcher(self, project_id, researcher_id):
        project = self.projects.find_one({"ProjectID": project_id})
        if project:
            researchers = project.get('Researchers', [])
            if researcher_id in researchers:
                researchers.remove(researcher_id)
                self.projects.update_one({"ProjectID": project_id}, {"$set": {"Researchers": researchers}})
    
    def add_user(self, project_id, user_id):
        project = self.projects.find_one({"ProjectID": project_id})
        if project:
            users = project.get('Users', [])
            if user_id not in users:
                users.append(user_id)
                self.projects.update_one({"ProjectID": project_id}, {"$set": {"Users": users}})

    def remove_user(self, project_id, user_id):
        project = self.projects.find_one({"ProjectID": project_id})
        if project:
            users = project.get('Users', [])
            if user_id in users:
                users.remove(user_id)
                self.projects.update_one({"ProjectID": project_id}, {"$set": {"Users": users}})

    def get_users(self):
        users = self.users.find()
        return pd.DataFrame(list(users))

    def get_project_researchers(self, project_id):
        project = self.projects.find_one({"ProjectID": project_id})
        if project:
            return project.get('Researchers', [])
        return []
    
    def get_projects_by_researcher(self, researcher_id):
        projects = self.projects.find({"Researchers": {"$in": [researcher_id]}}, {"ProjectID": 1, "_id": 0})
        return projects
    
    def get_project_by_researcher_df(self, researcher_id):
        projects = self.get_project_researchers(researcher_id)
        return pd.DataFrame(list(projects))
    
    def get_project_by_id(self, project_id):
        project = self.projects.find_one({"ProjectID": project_id})
        return project if project else None
    
    def get_project_by_id_df(self, project_id):
        project = self.get_project_by_id(project_id)
        return pd.DataFrame(list(project)) if project else None
    
    def get_projects(self):
        return self.projects_df

