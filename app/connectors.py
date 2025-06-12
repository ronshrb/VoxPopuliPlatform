from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from google.cloud import storage

load_dotenv()
bucket_name = os.getenv("BUCKET_NAME")
users_db_user = os.getenv("users_db_user")
users_db_pass = os.getenv("users_db_pass")
db_name = os.getenv("db_name") 
matrix_db_connection_string = os.getenv("matrix-db-connection-string")

 
class gcp_connector:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def get_client(self):
        return self.client
    
    def get_bucket(self):
        return self.bucket
    


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

