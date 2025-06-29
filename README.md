📦 Backend (Flask) - Smart Parking Reservation System

Directory: /backend

Description:
This is the Flask-based RESTful API backend that powers the Smart Campus Parking Reservation System. It handles user authentication, parking reservations, reporting, availability predictions, and administrative operations.

 Features:
- User registration & login
- Real-time slot reservations
- Custom parking layout support
- Heatmap and time-based availability prediction
- Parking issue reporting with image uploads
- Admin user management
- RESTful API endpoints with CORS

Requirements:
- Python 3.8+
- MySQL Server
- pip for installing dependencies

Installation:
1. Clone the repository:
 git clone https://github.com/Danielsuhaimi7/flutterproject_backend.git
 cd smart-parking-system/backend

2. Install dependencies:
 pip install -r requirements.txt

3. Create database and configure MySQL:
- Create a MySQL database and update credentials in db.py
- Tables required: users, reservations, custom_reservations, parking_reports, parkings
- Run schema.sql in MySQL to initialize the database.

4. Run the Flask app:
- python app.py
  
5. Access the backend:
- By default: http://localhost:5000

Important Folders:
- uploads/ – stores report images
- custom_layouts/ – JSON files for custom parking layouts
