from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash,session ,jsonify
from werkzeug.utils import secure_filename
import os
import pandas as pd
import cv2
import numpy as np
from io import BytesIO
from pdf2image import convert_from_path
from google.cloud import vision
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from datetime import datetime
import re
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

service_account_file = "ocr-image-423812-6e9e38c17ca8.json"
client = vision.ImageAnnotatorClient.from_service_account_json(service_account_file)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'yk11'
app.config['MYSQL_PASSWORD'] = 'yk11.club'
app.config['MYSQL_DB'] = 'pdf_csv'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

def create_user_table():
    try:
        cur = mysql.connection.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL
                    )''')
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print("Error creating user table:", e)


create_user_table()
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return bcrypt.generate_password_hash(password).decode('utf-8')

def parse_google_text(text):
    print(text, "text")
    no = 0 
    text = text.replace("| Photo", "").replace("Photo", "").replace("Available", "").replace("Age +", "Age:").replace("Age !", "Age:").replace("Age ", "Age:").replace("[", "1").replace("House Number =", "House Number:").replace("House Number +", "House Number :").replace("Name +", "Name :").replace("Narne :", "Name :").replace("Name =", "Name :").replace("Name *", "Name :").replace("Name |", "Name :").replace("Name ‘", "Name :").replace("fqn 2? Gender 2 Mate", "Age :69 Gender : Male").replace("Husband's Name?", "Husband's Name:").replace("Name !", "Name :").replace("Age =", "Age :").replace("Gender -", "Gender :").replace("::", ":")
    id, name, father_name, house_number, age, gender = '', '', '', '', '', ''
    for line in text.splitlines():
        if "Father's Name" in line or "Husband's Name" in line or "Others:" in line:
            father_name = line.split(":")[1].strip()
            continue
        elif "Name" in line and (("Father's Name" in line or "Husband's Name" in line or "Others:" in line) == False):
            if ":" in line:
                name = line.split(":")[1].strip()
            elif "Name" in line:
                name = line.split("Name ")[1].strip()
            else:
                print("\n", line, "--------------No name found ------------", "\n")
        elif "House Number" in line and ":" in line:
            house_number = line.split(":")[1].strip()
        elif "Age" in line:
            parts = line.split(":")[1].strip().split(" ")
            age = parts[0]
            genderArr = line.split(":")
            gender = genderArr[-1].strip() if len(genderArr) > 0 and "Gender" in line else ""
            if gender.lower() == 'male':
                gender = 'M'
            elif gender.lower() == 'female':
                gender = 'F'
        elif re.search(r'^[A-Z]{3}[0-9]{7}$', line) or re.search(r'^[A-Z]{3}\d{7}$', line): 
            id_match = re.search(r'^([A-Z]{3}\d{7})$', line)
            if id_match:
                id = id_match.group(1)
        elif line.isnumeric() and (no == 0 or (no != 0 and int(line) < int(no))):
            no = line

    return [no, id, name, father_name, house_number, age, gender]

def google_detect_text(content):
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    full_text = response.full_text_annotation.text
    return full_text

def extract_image_text_from_pdf(pdf_path, start_page, end_page):
    images = convert_from_path(pdf_path, first_page=start_page, last_page=end_page, dpi=350)
    all_data = []

    for image in images:
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
        _, binary_image = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=lambda c: (cv2.boundingRect(c)[1], cv2.boundingRect(c)[0]))

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 100 and h > 100:
                roi = image.crop((x, y, x + w, y + h))
                buffered = BytesIO()
                roi.save(buffered, format="JPEG")
                gt = google_detect_text(buffered.getvalue())
                parsed_data = parse_google_text(gt)
                if len(parsed_data) > 0:
                    all_data.append(parsed_data)

    return all_data
    
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cur.fetchone()
        cur.close()

        if user:
            flash('Login successful', 'success')
            session['logged_in'] = True
            session['username'] = email  
            return redirect(url_for('upload_pdf'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        start_page = request.form['start_page']
        end_page = request.form['end_page']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            all_data = extract_image_text_from_pdf(file_path, int(start_page), int(end_page))
            df = pd.DataFrame(all_data, columns=["No", "ID", 'Name', "Father's Name / Guardian Name", 'Address', 'Age', 'Gender'])
            excel_filename = f'output_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'
            excel_path = os.path.join(app.config['UPLOAD_FOLDER'], excel_filename)
            df.to_excel(excel_path, index=False)

            flash('File converted successfully!', 'success')
            return jsonify({'filename': excel_filename})  
    return render_template('upload.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
