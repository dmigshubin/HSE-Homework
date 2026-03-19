import time
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["university"]

start = time.time()

for i in range(10000):
    db.Students.insert_one({
        "student_id": f"S{i}",
        "first_name": "Test",
        "last_name": "User",
        "group_id": "G1",
        "enrollment_year": 2023,
        "email": f"test{i}@mail.com"
    })

end = time.time()

print("Time:", end - start)
print("TPS:", 10000 / (end - start))