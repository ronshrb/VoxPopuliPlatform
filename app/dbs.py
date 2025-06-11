from sqlalchemy import Table, Column, String, Boolean, Date, select, insert, update, delete,ForeignKeyConstraint
import pandas as pd
from datetime import datetime
import connectors
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
            Column('lastupdate', Date),
            Column('deleted', Boolean, default=False)
        )


chats_table = Table(
    'chats', metadata,
    Column('chatid', String, primary_key=True),
    Column('chatname', String, nullable=False),
    Column('platform', String, nullable=False),
    Column('userid', String, primary_key=True),  # Add as part of composite PK
    Column('createdat', Date),
    Column('updatedat', Date),
    Column('active', Boolean, default=False),
    ForeignKeyConstraint(['userid'], ['users.userid'])
)


chats_blacklist_table = Table(
    'chats_blacklist', metadata,
    Column('chatid', String, primary_key=True),
    Column('userid', String, primary_key=True)
)

class UsersTable:
    def __init__(self):
        self.users_table = users_table
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
        # Fetch from SQLAlchemy, then rename columns as required
        result = session.execute(select(
            self.users_table.c.userid,
            self.users_table.c.role,
            self.users_table.c.creator,
            self.users_table.c.active,
            self.users_table.c.createdat,
            self.users_table.c.lastupdate
        )).fetchall()
        columns = ['UserID', 'Role', 'Creator', 'Active', 'CreatedAt', 'UpdatedAt']
        if result:
            df = pd.DataFrame(result, columns=columns)
        else:
            df = pd.DataFrame(columns=columns)
        return df
    
    def change_active_status_for_user(self, user_id):
        """
        Change the active status for a user.
        """
        try:
            # Fetch current status
            result = session.execute(
                select(self.users_table.c.active).where(self.users_table.c.userid == user_id)
            ).fetchone()
            if result:
                current_status = result[0]
                new_status = not current_status  # Toggle status
                stmt = update(self.users_table).where(self.users_table.c.userid == user_id).values(
                    active=new_status,
                    lastupdate=datetime.now()
                )
                session.execute(stmt)
                session.commit()
                return new_status
            return None
        except Exception as e:
            session.rollback()
            print(f"Error in change_active_status_for_user: {e}")
            return None

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
                    'Deleted': d.get('deleted'),
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

    # def get_whitelisted_rooms(self, userid):
    #     """
    #     Return a list of chat IDs (strings) of the user that appear in chat_projects.
    #     """
    #     try:
    #         # Get all chat IDs for this user from chats table
    #         active_chats = session.execute(
    #             select(self.chats.c.chatid).where(self.chats.c.active == True & self.chats.c.userid == userid)
    #         ).fetchall()
    #         chat_ids = [row[0] for row in active_chats] if active_chats else []
    #         if not chat_ids:
    #             return []
    #         # Get chat IDs that are also in chat_projects
    #         whitelisted_chats = session.execute(
    #             select(self.chats.c.chatid)
    #             .where(
    #                 self.chats.c.chatid.in_(
    #                     select(chat_projects_table.c.chatid).where(chat_projects_table.c.chatid.in_(chat_ids))
    #                 )
    #             )
    #         ).fetchall()
    #         ids = [row[0] for row in whitelisted_chats] if whitelisted_chats else []
    #         return ids
    #     except Exception as e:
    #         session.rollback()
    #         print(f"Error in get_whitelisted_rooms: {e}")
    #         return []
        
    def delete_user(self, user_id):
        """
        Soft-delete a user by setting the 'deleted' column to True.
        """
        try:
            stmt = update(self.users_table).where(self.users_table.c.userid == user_id).values(
                deleted=True,
                lastupdate=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in delete_user: {e}")


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
            if not chat_name:
                chat_name = "Unknown Chat"
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

    def update_chat_name(self, chat_id, user_id, chat_name):
        """
        Update the name of a chat by chat_id and user_id.
        """
        try:
            if not chat_name:
                chat_name = "Unknown Chat"
            stmt = update(self.chats_table).where(
                (self.chats_table.c.chatid == chat_id) & (self.chats_table.c.userid == user_id)
            ).values(chatname=chat_name, updatedat=datetime.now())
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in update_chat_name: {e}")

    def update_chat_donation(self, chat_id, user_id):
        """
        Update the donation (active) status of a chat.
        """
        try:
            stmt = update(self.chats_table).where(
                (self.chats_table.c.chatid == chat_id) & (self.chats_table.c.userid == user_id)
            ).values(updatedat=datetime.now())
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in update_chat_donation: {e}")

    def update_all_chats(self, chats_dict, userid):
        """
        Update all chats in the provided list/dict. Adds new chats if not present, updates names if changed.
        """
        for chat in chats_dict:
            chat_id = chat.get("ChatID")
            chat_name = chat.get("Chat Name")
            # user_id = chat.get("UserID")
            chat_in_db = self.get_chat_by_id(chat_id, userid)
            if chat_in_db: # check if needed to update chat name
                if chat_in_db['Chat Name'] != chat_name:
                    self.update_chat_name(chat_id, userid, chat_name)
            else: # if chat not in db, add it
                platform = chat.get("Platform")
                self.add_chat(chat_id, chat_name, platform, userid)
                # self.update_chat_donation(chat_id, user_id)

    def get_df(self):
        """
        Fetch all chats as a DataFrame with renamed columns.
        """
        result = session.execute(select(self.chats_table)).fetchall()
        if not result:
            return pd.DataFrame()
        df = pd.DataFrame(result, columns=result[0]._mapping.keys())
        columns_renaming = {
            'chatid': 'ChatID',
            'chatname': 'Chat Name',
            'platform': 'Platform',
            'userid': 'UserID',
            'active': 'Donated',
            'createdat': 'CreatedAt',
            'updatedat': 'UpdatedAt',
        }
        df = df.rename(columns=columns_renaming)
        return df

    def get_chat_by_id(self, chat_id, user_id):
        """
        Fetch a single chat by its chat_id and user_id.
        """
        result = session.execute(
            select(self.chats_table).where(
                (self.chats_table.c.chatid == chat_id) & (self.chats_table.c.userid == user_id)
            )
        ).fetchone()
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

    def get_chats_by_user(self, user_id):
        """
        Fetch all chats for a given user_id.
        """
        result = session.execute(select(self.chats_table).where(self.chats_table.c.userid == user_id)).fetchall()
        chats_df = pd.DataFrame(result) if result else pd.DataFrame(columns=['ChatID', 'Chat Name', 'Platform', 'UserID', 'Donated', 'CreatedAt', 'UpdatedAt',])
        columns_renaming = {
            'chatname': 'Chat Name',
            'chatid': 'ChatID',
            'platform': 'Platform',
            'userid': 'UserID',
            'active': 'Donated',
            'createdat': 'CreatedAt',
            'updatedat': 'UpdatedAt',
        }
        chats_df = chats_df.rename(columns=columns_renaming)
        return chats_df
    
    def change_active_status_for_chat(self, chat_id, user_id):
        """
        Change the active status for a chat.
        """
        try:
            # Fetch current status
            result = session.execute(
                select(self.chats_table.c.active).where(
                    (self.chats_table.c.chatid == chat_id) & (self.chats_table.c.userid == user_id)
                )
            ).fetchone()
            if result:
                current_status = result[0]
                new_status = not current_status  # Toggle status
                print(new_status)
                stmt = update(self.chats_table).where(
                    (self.chats_table.c.chatid == chat_id) & (self.chats_table.c.userid == user_id)
                ).values(
                    active=new_status,
                    updatedat=datetime.now()
                )
                session.execute(stmt)
                session.commit()
                return new_status
            return None
        except Exception as e:
            session.rollback()
            print(f"Error in change_active_status_for_chat: {e}")
            return None

    def delete_chat(self, chat_id, user_id):
        """
        Delete a chat from the database by chat_id and user_id.
        """
        try:
            stmt = delete(self.chats_table).where(
                (self.chats_table.c.chatid == chat_id) & (self.chats_table.c.userid == user_id)
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in delete_chat_by_id: {e}")

    def get_whitelisted_rooms_by_user(self, userid):
        """
        Return a list of chat IDs (strings) of the user that appear in chat_projects.
        """
        try:
            # Get all chat IDs for this user from chats table
            active_chats = session.execute(
                select(self.chats_table.c.chatid).where(
                    (self.chats_table.c.active == True) & (self.chats_table.c.userid == userid)
                )
            ).fetchall()
            chat_ids = [row[0] for row in active_chats] if active_chats else []
            if not chat_ids:
                return []
            return chat_ids
        except Exception as e:
            session.rollback()
            print(f"Error in get_whitelisted_rooms: {e}")
            return []
        
    
    def disable_all_rooms_for_user(self, userid):
        """
        Disable all rooms for a user.
        """
        try:
            stmt = update(self.chats_table).where(self.chats_table.c.userid == userid).values(active=False, updatedat=datetime.now())
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error in disable_rooms_by_user: {e}")


class ChatsBlacklistTable:
    def __init__(self):
        self.chats_blacklist_table = chats_blacklist_table

    def get_all_ids(self, userid):
        """
        Fetch all chat IDs in the blacklist for a specific user.
        """
        try:
            result = session.execute(
                select(self.chats_blacklist_table.c.chatid)
                .where(self.chats_blacklist_table.c.userid == userid)
            ).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            session.rollback()
            print(f"Error in get_all_ids: {e}")
            return []

    def add_chat(self, chat_id, userid):
        """
        Add a chat to the blacklist for a specific user.
        """
        print(chat_id, userid)
        try:
            stmt = insert(self.chats_blacklist_table).values(chatid=chat_id, userid=userid)
            session.execute(stmt)
            session.commit()
        except Exception as e:
            print(e)
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
            if df is not None:
                df = pd.concat([df, self.blob_to_dataframe(path)], ignore_index=True)
            else:
                df = self.blob_to_dataframe(path)
        renaming_dict = {
            'id': 'MessageID',
            'room_id': 'ChatID',
            'username': 'UserID',
            'anonymized_sender': 'Sender',
            'anonymized_content': 'Content',
            'timestamp': 'Timestamp',
            }
        df = df[list(renaming_dict.keys())]
        df = df.rename(columns=renaming_dict)
        return df
    
    def get_chats_ids_and_names(self, df, user_ids=None):
        """
        Get a dictionary of chat names as keys and chat IDs as values for the specified user IDs.
        If user_ids is None, return all chats.
        """
        chat_dict = {}
        for _, row in df.iterrows():
            chat_name = row['Chat Name']
            chat_id = row['ChatID']
            user_id = row['UserID']
            if chat_name not in chat_dict:
                chat_dict[f'{chat_name} by {user_id}'] = chat_id
        return chat_dict
    
    def get_chats_summary(self, df, chats_df):
        """
        Get a summary of messages grouped by chat ID and user ID.
        """
        if df.empty:
            return pd.DataFrame(columns=['Chat ID', 'User ID', 'Total Messages'])
        else:
            summary = df.groupby(['ChatID', 'UserID']).size().reset_index(name='Total Messages')
            summary.columns = ['Chat ID', 'User', 'Total Messages']
            summary['Chat ID'] = summary['Chat ID'].astype(str)
            summary['User'] = summary['User'].astype(str)
            summary.sort_values(by=['Chat ID', 'User'], inplace=True)
            summary.reset_index(drop=True, inplace=True)

            # Merge with chats_df to get chat names
            summary = summary.merge(chats_df[['ChatID', 'Chat Name', 'Platform', 'Donated', 'CreatedAt']], left_on='Chat ID', right_on='ChatID', how='left')
            summary.drop(columns=['ChatID'], inplace=True)
            desired_order = ['Chat ID', 'User', 'Chat Name', 'Total Messages', 'Donated', 'Platform', 'CreatedAt']
            summary = summary[desired_order]

            return summary
