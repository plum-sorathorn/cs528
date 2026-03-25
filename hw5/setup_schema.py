import os
import sqlalchemy
from google.cloud.sql.connector import Connector

def getconn():
    db_pass = os.environ.get("DB_PASS")
    project_id = "cs528-485615"
    
    connector = Connector()
    return connector.connect(
        f"{project_id}:us-central1:hw5-db-instance",
        "pymysql",
        user="root",
        password=db_pass,
        db="hw5_db"
    )

engine = sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)

with engine.connect() as conn:
    conn.execute(sqlalchemy.text("""
        CREATE TABLE IF NOT EXISTS request_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            country VARCHAR(100), client_ip VARCHAR(50),
            gender VARCHAR(20), age INT, income VARCHAR(50),
            is_banned BOOLEAN, time_of_day TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            requested_file VARCHAR(255)
        )
    """))
    conn.execute(sqlalchemy.text("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            time_of_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            requested_file VARCHAR(255), error_code INT
        )
    """))
    conn.commit()