# Smart Face Recognition Attendance System

An AI-powered, full-stack web application built with **Django** and **OpenCV** designed to automate student attendance tracking using advanced Deep Neural Networks (DNN) for real-time face detection and recognition.

![Project Banner](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)

##  Project Overview
Traditional attendance systems are manual, time-consuming, and prone to proxy attendance. This system leverages facial recognition technology to provide a seamless, secure, and touchless attendance management solution for educational institutions.

##  Key Features
- **Real-Time Face Recognition:** Utilizes OpenCV's DNN module (`res10_300x300_ssd`) for robust live facial detection.
- **Automated Attendance Logging:** Matches detected faces with the student database and marks attendance instantly.
- **Teacher Dashboard:** A dedicated portal for teachers to manage schedules, view attendance reports, and track defaulters.
- **Student Registration & Onboarding:** Easy UI for registering new students and dynamically capturing their face datasets.
- **Department & Period Filtering:** Structured database isolating attendance records by department, year, and specific class periods.
- **Secure Authentication:** Role-based access control separating Superadmin, Teachers, and Students.

##  Technology Stack
- **Backend:** Python, Django
- **Computer Vision Model:** OpenCV (DNN, Haar Cascades, LBPH Face Recognizer)
- **Frontend / UI:** HTML5, CSS3, JavaScript, Bootstrap
- **Database:** SQLite (Development) / PostgreSQL (Ready)
- **Architecture:** MVT (Model-View-Template)

##  Project Structure
```text
Smart-Face-Recognition-Attendance-System/
├── face_recognition_web/    # Core Django settings & configurations
├── recognition/             # Main app (Views, Models, URLs)
│   ├── models_dnn/          # AI face detection models (Caffe)
│   ├── services/            # Background tasks and email services
│   ├── static/              # CSS, JS, and Images
│   └── templates/           # HTML user interfaces
├── face_data.pkl            # Trained dataset embeddings
├── manage.py                # Django execution script
└── requirements.txt         # Project dependencies
```

##  Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/MohammedRiyazdeen/Smart-Face-Recognition-Attendance-System.git
   cd Smart-Face-Recognition-Attendance-System
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Database Migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a Superuser (Admin):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the Development Server:**
   ```bash
   python manage.py runserver
   ```
   *Visit `http://127.0.0.1:8000` in your browser.*

##  Usage Workflow
1. **Admin/Teacher Setup:** Log into the dashboard to define departments and schedules.
2. **Student Registration:** Enroll a student via the web form; the system will open the webcam to capture sample images and train the model.
3. **Take Attendance:** The teacher activates the camera for a specific period. As students walk by, the system detects faces, verifies them, and pushes attendance data directly to the database.
4. **Analytics:** View heatmaps, generate PDF reports, or notify absentees directly from the UI.

##  Contributing
Contributions, issues, and feature requests are welcome!

##  License
This project is open-source and available under the MIT License.
