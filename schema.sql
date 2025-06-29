-- USERS TABLE
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    student_id VARCHAR(20) UNIQUE,
    email VARCHAR(100),
    password VARCHAR(100),
    phone VARCHAR(20),
    role ENUM('user', 'admin') DEFAULT 'user'
);

-- RESERVATIONS TABLE
CREATE TABLE reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20),
    slot_code VARCHAR(10),
    date DATE,
    time TIME,
    duration INT,
    status VARCHAR(20) DEFAULT 'reserved'
);

-- CUSTOM RESERVATIONS TABLE
CREATE TABLE custom_reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20),
    parking_name VARCHAR(100),
    slot_index INT,
    date DATE,
    time TIME,
    duration INT
);

-- PARKING REPORTS TABLE
CREATE TABLE parking_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20),
    name VARCHAR(100),
    parking_location VARCHAR(100),
    report_type VARCHAR(50),
    image_path TEXT,
    slot VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settled BOOLEAN DEFAULT FALSE
);

-- PARKINGS TABLE
CREATE TABLE parkings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    latitude DOUBLE,
    longitude DOUBLE,
    slot_count INT DEFAULT 10
);
