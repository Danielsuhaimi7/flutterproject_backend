import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
import mysql.connector

# Load reservation data from MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="smart_parking"  
)

query = "SELECT student_id, slot_code, HOUR(time) as hour, DAYOFWEEK(date) as weekday FROM reservations"
df = pd.read_sql(query, conn)

# Encode categorical features
df['slot_code'] = df['slot_code'].astype('category').cat.codes
df['student_id'] = df['student_id'].astype('category').cat.codes

X = df[['student_id', 'hour', 'weekday']]
y = df['slot_code']

model = RandomForestClassifier()
model.fit(X, y)

# Save model
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model trained and saved.")
