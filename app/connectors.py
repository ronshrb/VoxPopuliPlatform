
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine
import os
from pymongo import MongoClient


class postgres_connector:
    def __init__(self):
        self.connector = Connector()
        self.db_user = os.environ["users_db_user"]
        self.db_pass = os.environ["users_db_pass"]
        self.db_connection_string = os.environ["matrix-db-connection-string"] 

    def getconn(self):
        conn = self.connector.connect(
            self.db_connection_string,
            "pg8000",
            user=self.db_user,
            password=self.db_pass,
            db="Users"
        )
        return conn
    
    def create_engine(self):
        return create_engine(
            "postgresql+pg8000://",
            creator=self.getconn,
        )
    
class mongo_connector():
    def __init__(self):
        self.db_connection_string = os.environ["MONGODB_URI"] 
        self.client = MongoClient(self.db_connection_string)
        self.db = None


    def get_client(self):
        return self.client
    
    def get_table(self, db_name, collection_name):
        return self.client[db_name][collection_name]

        
