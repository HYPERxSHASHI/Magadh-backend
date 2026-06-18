import os
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta

app = Flask(__name__, static_url_path='/static')
CORS(app)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Secure DB Connection
MONGO_URI = "mongodb+srv://admin123:adminpass@cluster0.a93no6o.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
client = MongoClient(MONGO_URI)

db = client["MagadhLibrary"]
students_collection = db["students"]
admin_collection = db["admin"]

def init_admin():
    try:
        if not admin_collection.find_one({"role": "admin"}):
            admin_collection.insert_one({
                "role": "admin",
                "name": "ADMIN",
                "email": "admin@magadhlibrary.in",
                "password": "MagadhAdmin@2026",
                "phone": "917903353191",
                "address": "Add- Block Road, New Bypas Road (Asthawan), Bihar"
            })
    except Exception as e:
        print(f"Database error: {e}")

init_admin()

def get_base_url():
    url = request.host_url
    if "onrender.com" in url and url.startswith("http://"):
        url = url.replace("http://", "https://")
    return url

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Magadh Library Backend is Running!"})

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if students_collection.find_one({"email": data.get('email')}):
        return jsonify({"message": "Email already exists"}), 400
    
    new_student = {
        "aadhaar": data.get('aadhaar', 'N/A'),
        "name": data.get('name'),
        "email": data.get('email'),
        "phone": data.get('phone'),
        "password": data.get('password'),
        "slot_number": "Pending Allocation",
        "address": "Not provided",
        "photo_url": "",
        "join_date": None,
        "expiry_date": None,
        "status": "Pending",
        "attendance": [],
        "payment_status": "Remaining"  # Default status feature added
    }
    students_collection.insert_one(new_student)
    return jsonify({"message": "Account created successfully!"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    admin = admin_collection.find_one({"role": "admin"})
    if admin and admin.get("email") == email and admin.get("password") == password:
        admin['_id'] = str(admin['_id'])
        return jsonify({"role": "admin", "data": admin}), 200

    student = students_collection.find_one({"email": email})
    if student and (password == student.get("password") or password == student.get("phone")):
        student['_id'] = str(student['_id'])
        return jsonify({"role": "student", "data": student}), 200
        
    return jsonify({"message": "Invalid Credentials"}), 401

@app.route('/api/update-admin', methods=['POST'])
def update_admin():
    data = request.json
    update_data = {
        "name": data.get("name"),
        "email": data.get("email"),
        "password": data.get("password"),
        "phone": data.get("phone"),
        "address": data.get("address")
    }
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    admin_collection.update_one(
        {"role": "admin"},
        {"$set": update_data}
    )
    return jsonify({"message": "Admin profile updated successfully!"}), 200

@app.route('/api/assign-slot', methods=['POST'])
def assign_slot():
    email = request.form.get('email')
    slot = request.form.get('slot')
    address = request.form.get('address')
    photo_file = request.files.get('photo')
    
    photo_url = ""
    if photo_file and photo_file.filename != '':
        filename = str(uuid.uuid4()) + "_" + photo_file.filename.replace(" ", "_")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo_file.save(filepath)
        photo_url = f"{get_base_url()}static/uploads/{filename}"

    join_date = datetime.now()
    expiry_date = join_date + timedelta(days=30)
    
    update_data = {
        "slot_number": slot,
        "address": address,
        "join_date": join_date.strftime("%Y-%m-%d"),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "status": "Active"
    }
    if photo_url:
        update_data["photo_url"] = photo_url
        
    result = students_collection.update_one(
        {"email": email},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        return jsonify({"message": "Registration confirmed and 1-month plan activated!"}), 200
    return jsonify({"message": "Student not found."}), 404

@app.route('/api/mark-paid', methods=['POST'])
def mark_paid():
    data = request.json
    email = data.get('email')
    result = students_collection.update_one({"email": email}, {"$set": {"payment_status": "Paid"}})
    if result.modified_count > 0:
        return jsonify({"message": "Payment status updated to Paid successfully!"}), 200
    return jsonify({"message": "Student not found."}), 404

@app.route('/api/mark-attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    identifier = data.get('identifier')
    today = datetime.now().strftime("%Y-%m-%d")

    query = {"$or": [{"email": identifier}, {"slot_number": identifier}]}
    student = students_collection.find_one(query)

    if not student:
        return jsonify({"message": "Student not found in database."}), 404
    if today in student.get("attendance", []):
        return jsonify({"message": f"{student['name']} is already marked present today!"}), 400

    students_collection.update_one(query, {"$push": {"attendance": today}})
    return jsonify({"message": f"Attendance marked for {student['name']}!"}), 200

@app.route('/api/students', methods=['GET'])
def get_all_students():
    students = []
    for s in students_collection.find():
        students.append({
            "aadhaar": s.get("aadhaar", "N/A"),
            "name": s.get("name", "N/A"),
            "email": s.get("email", "N/A"),
            "phone": s.get("phone", "N/A"),
            "slot": s.get("slot_number", "Unassigned"),
            "address": s.get("address", "N/A"),
            "expiry_date": s.get("expiry_date", "Pending"),
            "attendance": s.get("attendance", []),
            "payment_status": s.get("payment_status", "Remaining")
        })
    return jsonify(students), 200

@app.route('/api/delete-student', methods=['POST'])
def delete_student():
    email = request.json.get('email')
    result = students_collection.delete_one({"email": email})
    if result.deleted_count > 0:
        return jsonify({"message": "Student deleted successfully!"}), 200
    return jsonify({"message": "Student not found."}), 404

@app.route('/api/update-photo', methods=['POST'])
def update_photo():
    email = request.form.get('email')
    photo_file = request.files.get('photo')
    
    if not email or not photo_file or photo_file.filename == '':
        return jsonify({"message": "Invalid request."}), 400

    filename = str(uuid.uuid4()) + "_" + photo_file.filename.replace(" ", "_")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    photo_file.save(filepath)
    photo_url = f"{get_base_url()}static/uploads/{filename}"

    result = students_collection.update_one(
        {"email": email},
        {"$set": {"photo_url": photo_url}}
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "Photo updated successfully!", "photo_url": photo_url}), 200
    return jsonify({"message": "Student not found."}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)