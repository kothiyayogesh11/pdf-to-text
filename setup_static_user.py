import mysql.connector
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Jtech@123",
    database="pdf_csv"
)

cursor = conn.cursor()

# Create users table if it doesn't exist
create_table_query = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
)
"""
cursor.execute(create_table_query)

static_user = {
    "email": "admin@jiyantech.com",
    "password": "1234567890"
}

hashed_password = bcrypt.generate_password_hash(static_user["password"]).decode('utf-8')

try:
    cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (static_user["email"], hashed_password))
    conn.commit()
    print("Static user added successfully.")
except Exception as e:
    print("Error:", e)
    conn.rollback()

cursor.close()
conn.close()
