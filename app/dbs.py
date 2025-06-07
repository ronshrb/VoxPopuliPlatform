from sqlalchemy import Table, Column, Integer, String, Boolean, Date, MetaData, select, insert, update, ForeignKey, delete
import pandas as pd
from datetime import datetime
import connectors
import duckdb
import os
from dotenv import load_dotenv
from io import StringIO
load_dotenv()


# Remove SQLAlchemy/Postgres setup from here, import from connectors instead
engine = connectors.engine
Session = connectors.Session
session = connectors.session
metadata = connectors.metadata

users_table = Table(
            'users', metadata,
            Column('userid', String, primary_key=True),
            Column('hashedpassword', String),
            Column('role', String),
            Column('creator', String),
            Column('active', Boolean),
            Column('createdat', Date),
            Column('lastupdate', Date)
        )

projects_table = Table(
            'projects', metadata,
            Column('projectid', String, primary_key=True),
            Column('projectname', String),
            Column('active', Boolean),
            Column('createdat', Date),
            Column('lastupdate', Date)
        )

chats_table = Table(
            'chats', metadata,
            Column('chatid', String, primary_key=True),
            Column('chatname', String),
            Column('platform', String),
            Column('userid', String),
            Column('createdat', Date),
            Column('updatedat', Date)
        )

# metadata.create_all(engine)  # Uncomment to create tables if needed
user_projects_table = Table(
    'user_projects', metadata,
    Column('userid', String, ForeignKey('users.userid', ondelete='CASCADE'), primary_key=True),
    Column('projectid', String, ForeignKey('projects.projectid', ondelete='CASCADE'), primary_key=True)
)

chat_projects_table = Table(
    'chat_projects', metadata,
    Column('chatid', String, ForeignKey('chats.chatid', ondelete='CASCADE'), primary_key=True),
    Column('projectid', String, ForeignKey('projects.projectid', ondelete='CASCADE'), primary_key=True)
)

chats_blacklist_table = Table(
    'chats_blacklist', metadata,
    Column('chatid', String, primary_key=True)
)
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
    
class UsersTable:
    def __init__(self):
        self.users_table = users_table
        self.user_projects_table = user_projects_table
        self.chat_projects_table = chat_projects_table
        self.chats = chats_table

    def add_user(self, user_id, hashed_password, creator_id, role='User', active=True):
        """
        Add a new user to the database.
        """
        try:
            stmt = insert(self.users_table).values(
                userid=user_id,
                hashedpassword=hashed_password,
                role=role,
                creator=creator_id,
                active=active,
                createdat=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in add_user: {e}")

    def get_users(self):
        """
        Fetch all users as a DataFrame.
        """
        result = session.execute(select(self.users_table)).fetchall()
        return pd.DataFrame(result, columns=result[0].keys()) if result else pd.DataFrame()

    def get_user_by_id(self, user_id):
        """
        Fetch a single user by their user_id.
        """
        try:
            result = session.execute(
                select(self.users_table).where(self.users_table.c.userid == user_id)
            ).fetchone()
            if result:
                d = dict(result._mapping)
                return {
                    'UserID': d.get('userid'),
                    'HashedPassword': d.get('hashedpassword'),
                    'Role': d.get('role'),
                    'Creator': d.get('creator'),
                    'Active': d.get('active'),
                    'CreatedAt': d.get('createdat'),
                }
            return None
        except Exception as e:
            session.rollback()
            print(f"Error in get_user_by_id: {e}")
            return None

    def get_user_by_email(self, email):
        """
        Fetch a user by their email address. (If Email column is available)
        """
        # If you have an Email column, implement this
        return None

    def get_users_by_ids(self, user_ids):
        """
        Fetch multiple users by a list of user_ids.
        Returns a list of user dicts, or an empty list if none found.
        """
        if not user_ids:
            return []
        try:
            result = session.execute(
                select(self.users_table).where(self.users_table.c.userid.in_(user_ids))
            ).fetchall()
            users = []
            for row in result:
                d = dict(row._mapping)
                users.append({
                    'UserID': d.get('userid'),
                    'Role': d.get('role'),
                    'Creator': d.get('creator'),
                    'Active': d.get('active'),
                    'CreatedAt': d.get('createdat'),
                })
            return users
        except Exception as e:
            session.rollback()
            print(f"Error in get_users_by_ids: {e}")
            return []
        
    def change_user_password(self, user_id, new_hashed_password):
        """
        Change the password for a user.
        """
        try:
            stmt = update(self.users_table).where(self.users_table.c.userid == user_id).values(
                hashedpassword=new_hashed_password,
                lastupdate=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in change_user_password: {e}")

    def get_whitelisted_rooms(self, user_id, for_server=False):
        """
        Return a list of chat IDs (strings) of the user that appear in chat_projects.
        """
        try:
            # Get all chat IDs for this user from chats table
            user_chats = session.execute(
                select(self.chats.c.chatid).where(self.chats.c.userid == user_id)
            ).fetchall()
            chat_ids = [row[0] for row in user_chats] if user_chats else []
            if not chat_ids:
                return []
            # Get chat IDs that are also in chat_projects
            whitelisted_chats = session.execute(
                select(self.chats.c.chatid)
                .where(
                    self.chats.c.chatid.in_(
                        select(chat_projects_table.c.chatid).where(chat_projects_table.c.chatid.in_(chat_ids))
                    )
                )
            ).fetchall()
            ids = [row[0] for row in whitelisted_chats] if whitelisted_chats else []
            if for_server:
                ids = [id.split(':')[0].replace('!', '') for id in ids]  # Filter for server IDs
            return ids
        except Exception as e:
            session.rollback()
            print(f"Error in get_whitelisted_rooms: {e}")
            return []
        
    def delete_user(self, user_id):
        """
        Delete a user from the database by user_id.
        """
        try:
            # First delete from user_projects association table
            stmt = delete(self.user_projects_table).where(self.user_projects_table.c.userid == user_id)
            session.execute(stmt)
            # Then delete from chats_projects association table
            stmt = delete(self.chat_projects_table).where(self.chat_projects_table.c.chatid == user_id)
            session.execute(stmt)
            # Finally delete from users table
            stmt = delete(self.users_table).where(self.users_table.c.userid == user_id)
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in delete_user: {e}")

class ProjectsTable:
    def __init__(self):
        self.projects_table = projects_table
        self.user_projects_table = user_projects_table

    def add_project(self, project_id, desc, researchers=None, active=True):
        """
        Add a new project to the database.
        """
        try:
            stmt = insert(self.projects_table).values(
                projectid=project_id,
                projectname=desc,
                active=active,
                createdat=datetime.now()
            )
            session.execute(stmt)
            session.commit()
            # Add researchers to user_projects association table
            if researchers:
                for researcher_id in researchers:
                    self.add_researcher(project_id, researcher_id)
        except Exception as e:
            session.rollback()
            print(f"Error in add_project: {e}")

    def add_researcher(self, project_id, researcher_id):
        """
        Add a researcher to a project in the user_projects table.
        """
        try:
            stmt = insert(self.user_projects_table).values(
                userid=researcher_id,
                projectid=project_id
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            if 'duplicate key' not in str(e):
                print(f"Error in add_researcher: {e}")

    def remove_researcher(self, project_id, researcher_id):
        """
        Remove a researcher from a project in the user_projects table.
        """
        try:
            from sqlalchemy import delete
            stmt = delete(self.user_projects_table).where(
                (self.user_projects_table.c.userid == researcher_id) &
                (self.user_projects_table.c.projectid == project_id)
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in remove_researcher: {e}")

    def add_user(self, project_id, user_id):
        """
        Add a user to a project. Updates the project's user list.
        """
        try:
            project = self.get_project_by_id(project_id)
            if project:
                users = project.get('users', '').split(',') if project.get('users') else []
                if user_id not in users:
                    users.append(user_id)
                    stmt = update(self.projects_table).where(self.projects_table.c.projectid == project_id).values(users=','.join(users))
                    session.execute(stmt)
                    session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in add_user to project: {e}")

    def remove_user(self, project_id, user_id):
        """
        Remove a user from a project. Updates the project's user list.
        """
        try:
            project = self.get_project_by_id(project_id)
            if project:
                users = project.get('users', '').split(',') if project.get('users') else []
                if user_id in users:
                    users.remove(user_id)
                    stmt = update(self.projects_table).where(self.projects_table.c.projectid == project_id).values(users=','.join(users))
                    session.execute(stmt)
                    session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in remove_user from project: {e}")

    def get_projects(self):
        """
        Fetch all projects as a list of dictionaries.
        """
        result = session.execute(select(self.projects_table)).fetchall()
        return [
            {
                'ProjectID': row._mapping['projectid'],
                'ProjectName': row._mapping['projectname'],
                'Active': row._mapping['active'],
                'CreatedAt': row._mapping['createdat'],
                'LastUpdate': row._mapping['lastupdate'],
            }
            for row in result
        ] if result else []

    def get_project_researchers(self, project_id):
        """
        Get a list of researcher IDs associated with a project.
        """
        # Return list of researcher IDs for a project from user_projects table
        try:
            result = session.execute(
                select(self.user_projects_table.c.userid).where(self.user_projects_table.c.projectid == project_id)
            ).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_project_researchers: {e}")
            return []

    def get_projects_by_researcher(self, researcher_id):
        """
        Get a list of projects for a given researcher.
        """
        # Return list of projects for a given researcher from user_projects table
        try:
            # Get all project IDs for this researcher
            result = session.execute(
                select(self.user_projects_table.c.projectid).where(self.user_projects_table.c.userid == researcher_id)
            ).fetchall()
            project_ids = [row[0] for row in result] if result else []
            if not project_ids:
                return []
            # Now fetch project details for these IDs
            result = session.execute(
                select(self.projects_table).where(self.projects_table.c.projectid.in_(project_ids))
            ).fetchall()
            # Return PascalCase keys for app compatibility
            return [
                {
                    'ProjectID': row._mapping['projectid'],
                    'ProjectName': row._mapping['projectname'],
                    'Active': row._mapping['active'],
                    'CreatedAt': row._mapping['createdat'],
                    'LastUpdate': row._mapping['lastupdate'],
                }
                for row in result
            ] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_projects_by_researcher: {e}")
            return []

    def get_project_by_id(self, project_id):
        """
        Fetch a project by its project_id.
        """
        result = session.execute(select(self.projects_table).where(self.projects_table.c.projectid == project_id)).fetchone()
        if result:
            d = dict(result._mapping)
            return {
                'ProjectID': d.get('projectid'),
                'ProjectName': d.get('projectname'),
                'Active': d.get('active'),
                'CreatedAt': d.get('createdat'),
                'LastUpdate': d.get('lastupdate'),
            }
        return None
    
    def get_projects_by_ids(self, project_ids):
        """
        Fetch multiple projects by their project_ids.
        """
        # Accepts a list of project_ids and returns a dict: {projectid: {ProjectName, Active, CreatedAt, LastUpdate}}
        if not project_ids:
            return {}
        result = session.execute(
            select(self.projects_table).where(self.projects_table.c.projectid.in_(project_ids))
        ).fetchall()
        projects_dict = {}
        for row in result:
            d = dict(row._mapping)
            projects_dict[d['projectid']] = {
                'ProjectName': d.get('projectname'),
                'Active': d.get('active'),
                'CreatedAt': d.get('createdat'),
                'LastUpdate': d.get('lastupdate'),
            }
        return projects_dict

    # def get_project_name_by_id(self, project_id):
    #     result = session.execute(select(self.projects_table.c.projectname).where(self.projects_table.c.projectid == project_id)).fetchone()
    #     return result[0] if result else None

class ChatsTable:
    """
    Table handler for chat records in the database.
    Provides methods to add, update, delete, and fetch chats.
    """
    def __init__(self):
        self.chats_table = chats_table

    def add_chat(self, chat_id, chat_name, platform, user_id):
        """
        Add a new chat to the database.
        """
        try:
            stmt = insert(self.chats_table).values(
                chatid=chat_id,
                chatname=chat_name,
                platform=platform,
                userid=user_id,
                createdat=datetime.now(),
                updatedat=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in add_chat: {e}")

    def update_chat_name(self, chat_id, chat_name):
        """
        Update the name of a chat by chat_id.
        """
        try:
            stmt = update(self.chats_table).where(self.chats_table.c.chatid == chat_id).values(chatname=chat_name, updatedat=datetime.now())
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in update_chat_name: {e}")

    def update_chat_donation(self, chat_id):
        """
        Update the donation (active) status of a chat.
        """
        try:
            stmt = update(self.chats_table).where(self.chats_table.c.chatid == chat_id).values(updatedat=datetime.now())
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in update_chat_donation: {e}")

    def update_all_chats(self, chats_dict):
        """
        Update all chats in the provided list/dict. Adds new chats if not present, updates names if changed.
        """
        for chat in chats_dict:
            chat_id = chat.get("ChatID")
            chat_name = chat.get("Chat Name")
            chat_in_db = self.get_chat_by_id(chat_id)
            if chat_in_db: # check if needed to update chat name
                if chat_in_db['Chat Name'] != chat_name:
                    self.update_chat_name(chat_id, chat_name)
            else: # if chat not in db, add it
                platform = chat.get("Platform")
                user_id = chat.get("UserID")
                self.add_chat(chat_id, chat_name, platform, user_id)
                # self.update_chat_donation(chat_id)

    def get_chats(self):
        """
        Fetch all chats as a DataFrame.
        """
        result = session.execute(select(self.chats_table)).fetchall()
        return pd.DataFrame(result, columns=result[0].keys()) if result else pd.DataFrame()

    def get_chat_by_id(self, chat_id):
        """
        Fetch a single chat by its chat_id.
        """
        result = session.execute(select(self.chats_table).where(self.chats_table.c.chatid == chat_id)).fetchone()
        if result:
            d = dict(result._mapping)
            return {
                'ChatID': d.get('chatid'),
                'Chat Name': d.get('chatname'),
                'Platform': d.get('platform'),
                'UserID': d.get('userid'),
                'CreatedAt': d.get('createdat'),
                'UpdatedAt': d.get('updatedat')
            }
        return None

    def get_chat_by_user(self, user_id):
        """
        Fetch all chats for a given user_id.
        """
        result = session.execute(select(self.chats_table).where(self.chats_table.c.userid == user_id)).fetchall()
        return [dict(row._mapping) for row in result] if result else []

    def delete_chat(self, chat_id):
        """
        Delete a chat from the database by chat_id.
        """
        try:
            stmt = delete(self.chats_table).where(self.chats_table.c.chatid == chat_id)
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in delete_chat_by_id: {e}")

class UserProjectsTable:
    def __init__(self):
        self.user_projects_table = user_projects_table

    def add_user_project(self, user_id, project_id):
        """
        Add a user-project association.
        """
        stmt = insert(self.user_projects_table).values(
            userid=user_id,
            projectid=project_id
        )
        session.execute(stmt)
        session.commit()

    def remove_user_project(self, user_id, project_id):
        """
        Remove a user-project association.
        """
        from sqlalchemy import delete
        stmt = delete(self.user_projects_table).where(
            (self.user_projects_table.c.userid == user_id) &
            (self.user_projects_table.c.projectid == project_id)
        )
        session.execute(stmt)
        session.commit()

    def get_user_projects(self, user_id):
        """
        Get all project IDs for a user.
        """
        result = session.execute(
            select(self.user_projects_table.c.projectid).where(self.user_projects_table.c.userid == user_id)
        ).fetchall()
        return [row[0] for row in result] if result else []

    def add_user_to_project(self, user_id, project_id):
        """
        Add a user to a project.
        """
        try:
            stmt = insert(self.user_projects_table).values(
                userid=user_id,
                projectid=project_id
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in add_user_to_project: {e}")
        
    def get_projects_users(self, project_id):
        """
        Get all user IDs associated with a project.
        """
        try:
            result = session.execute(
                select(self.user_projects_table.c.userid).where(self.user_projects_table.c.projectid == project_id)
            ).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_projects_users: {e}")
            return []
        

class ChatProjectsTable:
    def __init__(self):
        self.chat_projects_table = chat_projects_table

    def get_df(self):
        """
        Fetch all chat-project associations as a DataFrame.
        """
        result = session.execute(select(self.chat_projects_table)).fetchall()
        return pd.DataFrame(result, columns=result[0].keys()) if result else pd.DataFrame()

    def add_chat_project(self, chat_id, project_id):
        """
        Add a chat-project association.
        """
        try:
            stmt = insert(self.chat_projects_table).values(
                chatid=chat_id,
                projectid=project_id
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            if 'duplicate key' not in str(e):
                print(f"Error in add_chat_project: {e}")

    def remove_chat_project(self, chat_id, project_id=None):
        """
        Remove a chat-project association.
        """
        
        try:
            if project_id:
                stmt = delete(self.chat_projects_table).where(
                    (self.chat_projects_table.c.chatid == chat_id) &
                    (self.chat_projects_table.c.projectid == project_id)
                )

            else:
                stmt = delete(self.chat_projects_table).where(
                    self.chat_projects_table.c.chatid == chat_id
                )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in remove_chat_project: {e}")

    def get_projects_for_chat(self, chat_id):
        """
        Get all project IDs associated with a chat.
        """
        try:
            result = session.execute(
                select(self.chat_projects_table.c.projectid).where(self.chat_projects_table.c.chatid == chat_id)
            ).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_projects_for_chat: {e}")
            return []

    # def get_chats_for_project(self, project_id):
    #     """
    #     Get all chat IDs associated with a project.
    #     """
    #     try:
    #         result = session.execute(
    #             select(self.chat_projects_table.c.chatid).where(self.chat_projects_table.c.projectid == project_id)
    #         ).fetchall()
    #         return [row[0] for row in result] if result else []
    #     except Exception as e:
    #         session.rollback()
    #         print(f"Error in get_chats_for_project: {e}")
    #         return []
    def get_chats_ids_by_projects(self, project_ids):
        """
        Get all chat IDs associated with a list of project IDs.
        """
        if not project_ids:
            return []
        if type(project_ids) is not list:
            project_ids = [project_ids]
        try:
            result = session.execute(
                select(self.chat_projects_table.c.chatid).where(self.chat_projects_table.c.projectid.in_(project_ids))
            ).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_chats_ids_by_projects: {e}")
            return []
    def is_chat_in_project(self, chat_id, project_id):
        """
        Check if a chat is associated with a project.
        """
        try:
            result = session.execute(
                select(self.chat_projects_table).where(
                    (self.chat_projects_table.c.chatid == chat_id) &
                    (self.chat_projects_table.c.projectid == project_id)
                )
            ).fetchone()
            return result is not None
        except Exception as e:
            session.rollback()
            print(f"Error in is_chat_in_project: {e}")
            return False
        
    def chat_project_exists(self, chat_id, project_id):
        """
        Check if a chat-project association exists.
        """
        try:
            result = session.execute(
                select(self.chat_projects_table).where(
                    (self.chat_projects_table.c.chatid == chat_id) &
                    (self.chat_projects_table.c.projectid == project_id)
                )
            ).fetchone()
            return result is not None
        except Exception as e:
            session.rollback()
            print(f"Error in chat_project_exists: {e}")
            return False

class ChatsBlacklistTable:
    def __init__(self):
        self.chats_blacklist_table = chats_blacklist_table

    def get_all_ids(self):
        """
        Fetch all chat IDs in the blacklist.
        """
        try:
            result = session.execute(select(self.chats_blacklist_table.c.chatid)).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_all_ids: {e}")
            return []

    def add_chat(self, chat_id):
        """
        Add a chat to the blacklist.
        """
        try:
            stmt = insert(self.chats_blacklist_table).values(chatid=chat_id)
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            if 'duplicate key' not in str(e):
                print(f"Error in add_id: {e}")


class MessagesTable:
    def __init__(self):
        self.gcp_connector = connectors.gcp_connector()
        self.client = self.gcp_connector.get_client()
        self.bucket = self.gcp_connector.get_bucket()

    def blob_to_dataframe(self, blob_name):
        """
        Download a NDJSON file from GCP bucket and load it into a pandas DataFrame.
        """
        blob = self.bucket.blob(blob_name)
        data = blob.download_as_bytes()
        df = pd.read_json(StringIO(data.decode('utf-8')), lines=True)
        return df
    
    def get_df(self, user_ids=None, chat_ids=None):
        blobs = self.bucket.list_blobs()
        selected_blobs = [blob for blob in blobs if 
                          (user_ids is None or blob.name.split('/')[0] in user_ids) and 
                          (chat_ids is None or (len(blob.name.split('/')) > 1 and 
                                                blob.name.split('/')[1] in chat_ids))]
        df = None
        for blob in selected_blobs:
            path = blob.name
            # user = path.split('/')[0]
            # chat_id = path.split('/')[1] if len(path.split('/')) > 1 else None
            # date = path.split('/')[2].split('.')[0] if len(path.split('/')) > 2 else None
            if df:
                df = pd.concat([df, self.blob_to_dataframe(path)], ignore_index=True)
            else:
                df = self.blob_to_dataframe(path)
        return df
    
    def get_chats_summary(self, user_ids=None, chat_ids=None):
        """
        Get a summary of messages grouped by chat ID and user ID.
        """
        df = self.get_df(user_ids, chat_ids)
        if df.empty:
            return pd.DataFrame()
        
        # Group by chat_id and user_id, counting messages
        summary = df.groupby(['room_id', 'sender_id']).size().reset_index(name='message_count')
        summary.rename(columns={'room_id': 'ChatID', 'sender_id': 'UserID'}, inplace=True)
        return summary

# d = Messages()
# print(d.get_df())
    # def get_messages_by_user(self, user_id, blob_name):
    #     """
    #     Fetch messages for a specific user from a NDJSON file in GCP bucket.
    #     """
    #     bucket = self.client.bucket(self.bucket_name)
    #     blob = bucket.blob(blob_name)
    #     data = blob.download_as_bytes()
    #     # Convert bytes to StringIO for pandas
    #     df = pd.read_json(StringIO(data.decode('utf-8')), lines=True)
    #     # Filter by user_id if needed
    #     df = df[df['username'] == user_id]
    #     return df
