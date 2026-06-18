import os
import uuid
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta

app = Flask(__name__, static_url_path='/static')
CORS(app)

# STRICT NO-CACHE POLICY FOR REAL-TIME SYNC
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

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
                "unique_id": "MAG-ADMIN",
                "password": "MagadhAdmin@2026",
                "phone": "917903353191",
                "address": "Add- Block Road, New Bypas Road (Asthawan), Bihar",
                "photo_url": ""
            })
    except Exception as e:
        pass

init_admin()

def get_base_url():
    url = request.host_url
    if "onrender.com" in url and url.startswith("http://"):
        url = url.replace("http://", "https://")
    return url

def generate_uid():
    return f"MAG-{random.randint(10000, 99999)}"

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Magadh Library Engine is Running Flawlessly!"})

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if students_collection.find_one({"email": data.get('email')}):
        return jsonify({"message": "Email already exists"}), 400
    
    uid = generate_uid()
    new_student = {
        "unique_id": uid, 
        "aadhaar": data.get('aadhaar', 'N/A'),
        "name": data.get('name'),
        "email": data.get('email'),
        "phone": data.get('phone'),
        "emergency_contact": "N/A",
        "password": data.get('password'),
        "slot_number": "Pending Allocation",
        "address": "Not provided",
        "photo_url": "",
        "documents": [], 
        "join_date": None,
        "expiry_date": None,
        "status": "Pending",
        "attendance": [],
        "gender": "N/A",
        "vip_member": False,
        "plan_type": "N/A",
        "plan_amount": 0,
        "paid_amount": 0,
        "due_amount": 0,
        "dob": "N/A",
        "father_name": "N/A"
    }
    students_collection.insert_one(new_student)
    return jsonify({"message": f"Account created! Login ID: {uid}", "unique_id": uid}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    identifier = data.get('email') 
    password = data.get('password')
    
    admin = admin_collection.find_one({"$or": [{"email": identifier}, {"unique_id": identifier}]})
    if admin and admin.get("password") == password:
        admin['_id'] = str(admin['_id'])
        return jsonify({"role": "admin", "data": admin}), 200

    student = students_collection.find_one({"$or": [{"email": identifier}, {"unique_id": identifier}]})
    if student and (password == student.get("password") or password == student.get("phone")):
        student['_id'] = str(student['_id'])
        return jsonify({"role": "student", "data": student}), 200
        
    return jsonify({"message": "Invalid Login ID or Password"}), 401

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
    admin_collection.update_one({"role": "admin"}, {"$set": {k: v for k, v in update_data.items() if v}})
    return jsonify({"message": "Admin profile updated successfully!"}), 200

@app.route('/api/update-admin-photo', methods=['POST'])
def update_admin_photo():
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename != '':
        filename = str(uuid.uuid4()) + "_" + photo_file.filename.replace(" ", "_")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo_file.save(filepath)
        photo_url = f"{get_base_url()}static/uploads/{filename}"
        admin_collection.update_one({"role": "admin"}, {"$set": {"photo_url": photo_url}})
        return jsonify({"photo_url": photo_url}), 200
    return jsonify({"message": "Error"}), 400

@app.route('/api/assign-slot', methods=['POST'])
def assign_slot():
    unique_id = request.form.get('unique_id')
    email = request.form.get('email')
    plan_amount = int(request.form.get('plan_amount', 0) or 0)
    paid_amount = int(request.form.get('paid_amount', 0) or 0)
    
    update_data = {
        "name": request.form.get('name'),
        "email": email,
        "password": request.form.get('password'),
        "phone": request.form.get('phone'),
        "emergency_contact": request.form.get('emergency_contact', 'N/A'),
        "slot_number": request.form.get('slot', 'N/A'),
        "aadhaar": request.form.get('aadhaar', 'N/A'),
        "address": request.form.get('address', 'N/A'),
        "gender": request.form.get('gender', 'N/A'),
        "vip_member": request.form.get('vip') == 'true',
        "plan_type": request.form.get('plan_type', 'N/A'),
        "plan_amount": plan_amount,
        "paid_amount": paid_amount,
        "due_amount": plan_amount - paid_amount,
        "join_date": request.form.get('start_date', datetime.now().strftime("%Y-%m-%d")),
        "expiry_date": request.form.get('expiry_date', (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")),
        "dob": request.form.get('dob', 'N/A'),
        "father_name": request.form.get('father_name', 'N/A'),
        "status": "Active"
    }

    # Handle Photo uploads
    main_photo = request.files.get('main_photo')
    if main_photo and main_photo.filename != '':
        filename = str(uuid.uuid4()) + "_main_" + main_photo.filename.replace(" ", "_")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        main_photo.save(filepath)
        update_data["photo_url"] = f"{get_base_url()}static/uploads/{filename}"

    uploaded_files = request.files.getlist('photos')
    photo_urls = []
    for file in uploaded_files:
        if file and file.filename != '':
            filename = str(uuid.uuid4()) + "_doc_" + file.filename.replace(" ", "_")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            photo_urls.append(f"{get_base_url()}static/uploads/{filename}")

    if photo_urls:
        update_data["documents"] = photo_urls

    query = None
    if unique_id and unique_id.strip() != "" and unique_id != "undefined":
        query = {"unique_id": unique_id}
    elif email and email.strip() != "":
        query = {"email": email}

    student = students_collection.find_one(query) if query else None

    if student:
        # Update Existing student
        students_collection.update_one({"_id": student['_id']}, {"$set": update_data})
        return jsonify({"message": "Profile Updated & Synced successfully!"}), 200
    else:
        # Create New student
        if students_collection.find_one({"email": email}):
            return jsonify({"message": "Error: This Email is already registered."}), 400
        
        update_data["unique_id"] = generate_uid()
        update_data["attendance"] = []
        if "documents" not in update_data:
            update_data["documents"] = []
        if "photo_url" not in update_data:
            update_data["photo_url"] = ""

        students_collection.insert_one(update_data)
        return jsonify({"message": f"New Member Created! ID: {update_data['unique_id']}"}), 201

@app.route('/api/mark-paid', methods=['POST'])
def mark_paid():
    email = request.json.get('email')
    student = students_collection.find_one({"email": email})
    if student:
        plan_amt = student.get('plan_amount', 0)
        students_collection.update_one({"email": email}, {"$set": {"due_amount": 0, "paid_amount": plan_amt}})
        return jsonify({"message": "Payment fully settled!"}), 200
    return jsonify({"message": "Not found"}), 404

@app.route('/api/mark-attendance', methods=['POST'])
def mark_attendance():
    identifier = request.json.get('identifier')
    today = datetime.now().strftime("%Y-%m-%d")
    query = {"$or": [{"email": identifier}, {"slot_number": identifier}, {"unique_id": identifier}]}
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
        s['_id'] = str(s['_id'])
        students.append(s)
    return jsonify(students), 200

@app.route('/api/delete-student', methods=['POST'])
def delete_student():
    email = request.json.get('email')
    students_collection.delete_one({"email": email})
    return jsonify({"message": "Student deleted successfully!"}), 200

@app.route('/api/update-photo', methods=['POST'])
def update_photo():
    email = request.form.get('email')
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename != '':
        filename = str(uuid.uuid4()) + "_" + photo_file.filename.replace(" ", "_")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo_file.save(filepath)
        photo_url = f"{get_base_url()}static/uploads/{filename}"
        students_collection.update_one(
            {"email": email}, 
            {"$set": {"photo_url": photo_url}, "$push": {"documents": photo_url}}
        )
        return jsonify({"photo_url": photo_url}), 200
    return jsonify({"message": "Error"}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)