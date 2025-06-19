import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_connection
import os
import pickle
import numpy as np
from werkzeug.utils import secure_filename
from datetime import timedelta, date, time, datetime
from flask import send_from_directory

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
    cursor.execute("SELECT name, student_id, role FROM users WHERE student_id=%s AND password=%s", (student_id, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "name": user[0],
            "student_id": user[1],
            "role": user[2]
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
    role = data.get('role', 'user')

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
    slot = request.form.get('slot')
    file = request.files.get('file')

    image_path = None
    if file:
        filename = secure_filename(file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO parking_reports (student_id, name, parking_location, report_type, image_path, slot)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (student_id, name, parking_location, report_type, image_path, slot))
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

    return jsonify({"reservations": results})

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
        ORDER BY date DESC, time DESC
    """, (student_id,))
    raw_reservations = cursor.fetchall()
    cursor.close()
    conn.close()

    def serialize_value(key, value):
        if isinstance(value, timedelta):
            return int(value.total_seconds() // 3600)
        elif isinstance(value, (datetime, date, time)):
            if key == "time":
                return value.strftime('%I:%M %p')
            return value.isoformat()
        return value

    reservations = [
        {k: serialize_value(k, v) for k, v in row.items()}
        for row in raw_reservations
    ]

    return jsonify({"reservations": reservations})

@app.route('/availability_graph', methods=['GET'])
def availability_graph():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT HOUR(time) as hour, COUNT(*) as count
        FROM reservations
        WHERE date = CURDATE()
        GROUP BY hour
        ORDER BY hour
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    max_capacity = 10
    availability = []
    for h in range(6, 22):
        booked = next((row[1] for row in data if row[0] == h), 0)
        probability = max(0, min(1, 1 - (booked / max_capacity)))
        availability.append({"hour": h, "availability": round(probability, 2)})

    return jsonify({"predictions": availability})

@app.route('/weekly_availability', methods=['GET'])
def weekly_availability():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DAYOFWEEK(date) AS weekday, HOUR(time) AS hour, COUNT(*) AS count
        FROM reservations
        GROUP BY weekday, hour
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    max_capacity = 10
    data = {day: {hour: 1.0 for hour in range(8, 19)} for day in range(1, 8)}

    for day, hour, count in rows:
        if 8 <= hour <= 18:
            probability = max(0, min(1, 1 - (count / max_capacity)))
            data[day][hour] = round(probability, 2)

    return jsonify({"availability": data})

@app.route('/daily_availability', methods=['GET'])
def daily_availability():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DAYOFWEEK(date) AS weekday, COUNT(*) AS count
        FROM reservations
        GROUP BY weekday
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    max_per_day = 10 * 11 
    data = {i: 1.0 for i in range(1, 8)}

    for day, count in rows:
        availability = max(0, min(1, 1 - count / max_per_day))
        data[day] = round(availability, 2)

    return jsonify({"availability": data})

@app.route('/add_parking_location', methods=['POST'])
def add_parking_location():
    data = request.json
    name = data.get('name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not all([name, latitude, longitude]):
        return jsonify({"status": "fail", "message": "Missing required fields"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO parkings (name, latitude, longitude)
            VALUES (%s, %s, %s)
        """, (name, latitude, longitude))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print("DB Error:", e)
        return jsonify({"status": "fail", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()
        
@app.route('/get_parkings', methods=['GET'])
def get_parkings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, latitude, longitude FROM parkings")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    data = [
        {"name": row[0], "latitude": row[1], "longitude": row[2]}
        for row in rows
    ]
    return jsonify({"status": "success", "parkings": data})

@app.route('/save_parking_layout', methods=['POST'])
def save_parking_layout():
    data = request.json
    parking_id = data['parking_id']
    slot_count = data['slot_count']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE parkings SET slot_count = %s WHERE id = %s
    """, (slot_count, parking_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": "Layout saved"})

@app.route('/get_user_info', methods=['POST'])
def get_user_info():
    data = request.json
    student_id = data.get('student_id')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, email, phone FROM users WHERE student_id = %s
    """, (student_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return jsonify({
            "name": user[0],
            "email": user[1],
            "phone": user[2]
        })
    else:
        return jsonify({"error": "User not found"}), 404
    
@app.route('/save_custom_layout', methods=['POST'])
def save_custom_layout():
    try:
        data = request.get_json()
        parking_name = data.get('parking_name')
        layout = data.get('layout')

        if not parking_name or not layout:
            return jsonify({'status': 'fail', 'message': 'Missing data'}), 400

        os.makedirs('custom_layouts', exist_ok=True)  # Ensure folder exists

        with open(f'custom_layouts/{parking_name}.json', 'w') as f:
            json.dump(layout, f)

        print(f"[✔] Layout for '{parking_name}' saved.")
        return jsonify({'status': 'success'})

    except Exception as e:
        print("[✘] Save layout error:", e)
        return jsonify({'status': 'fail', 'message': str(e)}), 500

@app.route("/get_custom_layout", methods=["POST"])
def get_custom_layout():
    data = request.get_json()
    parking_name = data.get("parking_name")

    try:
        with open(f'custom_layouts/{parking_name}.json', 'r') as f:
            layout = json.load(f)
        return jsonify({"layout": layout})
    except FileNotFoundError:
        return jsonify({"layout": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/reserve_custom_slot', methods=['POST'])
def reserve_custom_slot():
    data = request.json
    student_id = data.get('student_id')
    parking_name = data.get('parking_name')
    slot_index = data.get('slot_index')
    date = data.get('date')
    time = data.get('time')
    duration = data.get('duration')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO custom_reservations (student_id, parking_name, slot_index, date, time, duration)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, parking_name, slot_index, date, time, duration))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        print("[✘] reserve_custom_slot error:", e)
        return jsonify({'status': 'fail', 'message': str(e)}), 500
    
@app.route('/get_booked_custom_slots', methods=['POST'])
def get_booked_custom_slots():
    data = request.get_json()
    parking_name = data.get('parking_name')
    date = data.get('date')
    time = data.get('time')

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT slot_index FROM custom_reservations
            WHERE parking_name = %s AND date = %s AND time <= %s
              AND ADDTIME(time, SEC_TO_TIME(duration * 3600)) > %s
        """, (parking_name, date, time, time))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        booked = [r[0] for r in results]
        return jsonify({"booked": booked})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/users', methods=['GET'])
def get_all_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT student_id, name, email, phone, role FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"users": users})

@app.route('/edit_user', methods=['POST'])
def edit_user():
    data = request.get_json()
    student_id = data.get('student_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    role = data.get('role')

    if not student_id:
        return jsonify({'status': 'fail', 'message': 'Missing student_id'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET name = %s, email = %s, phone = %s, role = %s
            WHERE student_id = %s
        """, (name, email, phone, role, student_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'fail', 'message': str(e)}), 500

@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    student_id = data.get('student_id')

    if not student_id:
        return jsonify({'status': 'fail', 'message': 'Missing student_id'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE student_id = %s", (student_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/all_reports', methods=['GET'])
def all_reports():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, student_id, name, parking_location, report_type, slot, image_path, created_at, settled
        FROM parking_reports
        ORDER BY created_at DESC
    """)
    reports = cursor.fetchall()
    cursor.close()
    conn.close()

    for report in reports:
        if report['image_path']:
            report['image_url'] = f"http://192.168.1.110:5000/uploads/{os.path.basename(report['image_path'])}"
        else:
            report['image_url'] = None

    return jsonify({"reports": reports})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/mark_report_settled', methods=['POST'])
def mark_report_settled():
    data = request.json
    report_id = data.get('report_id')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE parking_reports SET settled = 1 WHERE id = %s", (report_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
