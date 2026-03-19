from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["university"]

def add_student():
    student = {
        "student_id": input("ID: "),
        "first_name": input("First name: "),
        "last_name": input("Last name: "),
        "group_id": input("Group: "),
        "enrollment_year": int(input("Year: ")),
        "email": input("Email: ")
    }
    db.Students.insert_one(student)
    print("Added!")

def get_student():
    sid = input("Student ID: ")
    s = db.Students.find_one({"student_id": sid})
    print(s)

def menu():
    while True:
        print("\n1. Add student")
        print("2. Get student")
        print("3. Exit")
        choice = input(">> ")

        if choice == "1":
            add_student()
        elif choice == "2":
            get_student()
        elif choice == "3":
            break

menu()