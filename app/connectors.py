
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine


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