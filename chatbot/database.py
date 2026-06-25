import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="manoj3218",
    database="chatbotdb"
)

cursor = db.cursor()