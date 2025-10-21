import csv
import sqlite3

connection = sqlite3.connect('databse.db')
cursor = connection.cursor()

cursor.execute("create table if not exists students(name TEXT, email TEXT, studentid TEXT, phone TEXT, password TEXT)")

f = open('Student Details.csv', 'r')
reader = csv.reader(f)
next(reader)
for row in reader:
    name = row[1]
    email = row[5]
    usn = row[0]
    phone = row[3]

    import random
    import string
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice(string.punctuation)
    remaining = random.choices(string.ascii_letters + string.digits + string.punctuation, k=4)
    password_list = [upper, lower, digit, special] + remaining
    random.shuffle(password_list)
    password = ''.join(password_list)

    data = [name, email, usn, phone, password]
    print(data)
    # cursor.execute("insert into students values (?,?,?,?,?)", data)
    # connection.commit()
