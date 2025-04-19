import sqlalchemy

# Build connection string using Cloud SQL Python connector (recommended)
from google.cloud.sql.connector import Connector

connector = Connector()

db_user = os.environ["users_db_user"]
db_pass = os.environ["users_db_pass"]  # comes securely from Secret Manager

def getconn():
    conn = connector.connect(
        "YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME",
        "pg8000",
        user=db_user
        password=db_pass
        db="users"
    )
    return conn

pool = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)
