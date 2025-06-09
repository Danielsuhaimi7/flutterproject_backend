from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_connection
import os
import pickle
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load AI model once at startup
model_path = 'model.pkl'
model = pickle.load(open(model_path, 'rb'))

@app.route('/')
def home():
    return "Flask backend is working!"

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    student_id = data['student_id']
    password = data['password']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, role FROM users WHERE student_id=%s AND password=%s", (student_id, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "student_id": user[0],
            "role": user[1]
        })
    else:
        return jsonify({"status": "fail", "message": "Invalid credentials"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data['name']
    student_id = data['student_id']
    email = data['email']
    password = data['password']
    phone = data['phone']
    role = data.get('role', 'user')  # 👈 Use 'user' by default

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, student_id, email, password, phone, role)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, student_id, email, password, phone, role))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": "Registration successful"})

@app.route('/report', methods=['POST'])
def submit_report():
    student_id = request.form.get('student_id')
    name = request.form.get('name')
    parking_location = request.form.get('parking_location')
    report_type = request.form.get('report_type')
    file = request.files.get('file')

    image_path = None
    if file:
        filename = secure_filename(file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO parking_reports (student_id, name, parking_location, report_type, image_path)
        VALUES (%s, %s, %s, %s, %s)
    """, (student_id, name, parking_location, report_type, image_path))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": "Report submitted successfully"})

@app.route('/reserve_slot', methods=['POST'])
def reserve_slot():
    data = request.json
    student_id = data['student_id']
    slot_code = data['slot_code']
    date = data['date']
    time = data['time']
    duration = data['duration']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reservations (student_id, slot_code, date, time, duration)
        VALUES (%s, %s, %s, %s, %s)
    """, (student_id, slot_code, date, time, duration))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": "Slot reserved successfully"})

@app.route('/booked_slots', methods=['POST'])
def booked_slots():
    data = request.json
    date = data['date']
    time = data['time']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT slot_code FROM reservations
        WHERE date = %s AND time <= %s AND ADDTIME(time, SEC_TO_TIME(duration * 3600)) > %s
    """, (date, time, time))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    booked = [row[0] for row in results]
    return jsonify({"booked": booked})

@app.route('/predict_slot', methods=['POST'])
def predict_slot():
    try:
        data = request.json
        user_id = int(data['user_id'])
        hour = int(data['hour'])
        weekday = int(data['weekday'])

        prediction = model.predict([[hour, weekday, user_id]])
        return jsonify({'recommended_slot': prediction[0]})
    except Exception as e:
        print("Predict Error:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/get_user_reservation', methods=['POST'])
def get_user_reservation():
    data = request.json
    student_id = data['student_id']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT slot_code FROM reservations
        WHERE student_id = %s
        ORDER BY id DESC LIMIT 1
    """, (student_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return jsonify({'status': 'success', 'slot_code': row[0]})
    else:
        return jsonify({'status': 'fail', 'message': 'No reservation found'})

@app.route('/user_reservations', methods=['POST'])
def user_reservations():
    data = request.json
    student_id = data.get('student_id')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT slot_code, date, time, duration 
        FROM reservations 
        WHERE student_id = %s 
        ORDER BY date DESC, time DESC
    """, (student_id,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(results)

@app.route('/user_reservation_details', methods=['POST'])
def user_reservation_details():
    data = request.json
    student_id = data['student_id']

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT slot_code, date, time, duration
        FROM reservations
        WHERE student_id = %s
    """, (student_id,))
    reservations = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'reservations': reservations})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
