from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google.cloud import storage

load_dotenv()
bucket_name = os.getenv("BUCKET_NAME")
users_db_user = os.getenv("users_db_user")
users_db_pass = os.getenv("users_db_pass")
db_name = os.getenv("db_name") 
matrix_db_connection_string = os.getenv("matrix-db-connection-string")

# cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
# class postgres_connector:
#     def __init__(self):
#         self.connector = Connector()
#         self.db_user = os.environ["users_db_user"]
#         self.db_pass = os.environ["users_db_pass"]
#         self.db_connection_string = os.environ["matrix-db-connection-string"] 

#     def getconn(self):
#         conn = self.connector.connect(
#             self.db_connection_string,
#             "pg8000",
#             user=self.db_user,
#             password=self.db_pass,
#             db="Users"
#         )
#         return conn
    
#     def create_engine(self):
#         return create_engine(
#             "postgresql+pg8000://",
#             creator=self.getconn,
#         )
    
class mongo_connector():
    def __init__(self):
        self.db_connection_string = os.environ["MONGODB_URI"] 
        self.client = MongoClient(self.db_connection_string)
        self.db = None

    def get_client(self):
        return self.client
    
    def get_table(self, db_name, collection_name):
        return self.client[db_name][collection_name]


class gcp_connector:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def get_client(self):
        return self.client
    
    def get_bucket(self):
        return self.bucket
    

    
# d = gcp_connector()
# print(d.get_buckets())
# print(d.get_bucket())
    

# POSTGRES_URI = os.getenv("POSTGRES_URI")
# engine = create_engine(POSTGRES_URI)
# Session = sessionmaker(bind=engine)
# session = Session()
# metadata = MetaData()

def getconn():
    with Connector() as connector:
        conn = connector.connect(
            matrix_db_connection_string,  # Cloud SQL connection name
            "pg8000",
            user=users_db_user,
            password=users_db_pass,
            db=db_name
        )
        return conn

engine = create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData()

