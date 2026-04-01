import os, ipaddress, sqlalchemy, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from google.cloud.sql.connector import Connector

def getconn():
    return Connector().connect("cs528-485615:us-central1:hw5-db-instance", "pymysql",
                               user="root", password=os.environ["DB_PASS"], db="hw5_db")

engine = sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)

# --- 3NF MIGRATION LOGIC ---
def run_3nf_migration(engine):
    print("Starting 3NF Migration...")
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("DROP TABLE IF EXISTS request_logs_v2;"))
        
        conn.execute(sqlalchemy.text("CREATE TABLE IF NOT EXISTS ip_locations (ip VARCHAR(50) PRIMARY KEY, country VARCHAR(100) NOT NULL);"))
        conn.execute(sqlalchemy.text("INSERT IGNORE INTO ip_locations (ip, country) SELECT DISTINCT client_ip, country FROM request_logs;"))
        
        # FIXED: Added requested_file and time_of_day to the V2 table
        conn.execute(sqlalchemy.text("""
            CREATE TABLE request_logs_v2 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ip VARCHAR(50),
                gender VARCHAR(20),
                age VARCHAR(20),
                income VARCHAR(50),
                is_banned BOOLEAN,
                requested_file VARCHAR(255),
                time_of_day VARCHAR(50),
                FOREIGN KEY (ip) REFERENCES ip_locations(ip)
            );
        """))
        
        # Extract the behavioral columns from the root table
        conn.execute(sqlalchemy.text("""
            INSERT INTO request_logs_v2 (ip, gender, age, income, is_banned, requested_file, time_of_day) 
            SELECT client_ip, gender, age, income, is_banned, requested_file, time_of_day FROM request_logs;
        """))
        conn.commit()
    print("Migration Complete.")

run_3nf_migration(engine)

# --- MACHINE LEARNING LOGIC ---
df = pd.read_sql("SELECT r.ip, r.gender, r.age, r.income, r.is_banned, r.requested_file, r.time_of_day, l.country FROM request_logs_v2 r JOIN ip_locations l ON r.ip = l.ip", engine)
df['ip_int'] = df['ip'].apply(lambda x: int(ipaddress.ip_address(x)))

# Clean Age
df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0)

# Use regex to pull the number out of the file string (e.g., '15043.html' -> 15043)
df['file_id'] = df['requested_file'].str.extract(r'(\d+)').astype(float).fillna(0)

# Extract the hour from the time string
df['hour'] = df['time_of_day'].str.split(':').str[0].astype(float).fillna(0)

# Model 1 (IP -> Country)
le_c = LabelEncoder()
y1 = le_c.fit_transform(df['country'])
X1_train, X1_test, y1_train, y1_test = train_test_split(df[['ip_int']], y1, test_size=0.2, random_state=42)
m1 = RandomForestClassifier(n_estimators=10, random_state=42).fit(X1_train, y1_train)

# Model 2 (Demographics & Behavior -> Income)
# We feed the model our new 'file_id' and 'hour' features
X2 = pd.get_dummies(df[['age', 'gender', 'country', 'is_banned', 'ip_int', 'file_id', 'hour']], columns=['gender', 'country'])
y2 = LabelEncoder().fit_transform(df['income'])

X2_train, X2_test, y2_train, y2_test = train_test_split(X2, y2, test_size=0.2, random_state=42)
m2 = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42).fit(X2_train, y2_train)

# Output Results to separate files
res1 = f"Model 1 Accuracy: {m1.score(X1_test, y1_test):.4f}"
with open("/tmp/model1_predictions.txt", "w") as f:
    f.write(res1)

res2 = f"Model 2 Accuracy: {m2.score(X2_test, y2_test):.4f}"
with open("/tmp/model2_predictions.txt", "w") as f:
    f.write(res2)
print("Results saved to separate files.")