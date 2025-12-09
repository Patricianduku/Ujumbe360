# Ujumbe360 - School Management System

Ujumbe360 is a comprehensive Django-based School Management System designed to streamline educational institution operations. It provides separate portals for administrators, teachers, and parents to manage students, fees, grades, attendance, announcements, and complaints.

## Features

###  Admin Portal
- **Student Management**: Add, edit, and manage student records
- **Fee Management**: Set fee structures and track payments
- **Grade Management**: Create exams and enter student grades
- **Attendance Tracking**: Monitor student attendance
- **Announcement System**: Create and manage school announcements
- **Complaint Management**: Handle parent and student complaints
- **Dashboard**: Comprehensive overview of school statistics

###  Parent Portal
- **Dashboard**: Overview of child's academic and financial status
- **My Children**: View detailed child information
- **Grades**: Access academic performance and reports
- **Fees**: Check fee statements and payment history
- **Announcements**: Stay updated with school news
- **Complaints**: Submit and track complaints

###  User Features
- **Dual Authentication**: Separate login for staff and parents
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Live data across all portals
- **Secure Access**: Role-based permissions and data protection

##  Technology Stack

- **Backend**: Django 4.x
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: HTML5, CSS3, JavaScript
- **UI Framework**: Bootstrap 5
- **Icons**: Bootstrap Icons
- **Authentication**: Django's built-in authentication system

##  Project Structure

```
Ujumbe360/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # Database file
├── ujumbe360/               # Project configuration
│   ├── __init__.py
│   ├── settings.py          # Django settings
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
└── lms/                     # Main application
    ├── __init__.py
    ├── admin.py             # Django admin configuration
    ├── apps.py              # App configuration
    ├── models.py            # Database models
    ├── views.py             # View functions
    ├── forms.py             # Django forms
    ├── urls.py              # App URL routing
    ├── tests.py             # Unit tests
    ├── migrations/          # Database migrations
    └── templates/           # HTML templates
        ├── base.html
        ├── base_admin.html
        ├── registration/
        ├── admin_portal/
        ├── parent_portal/
        ├── students/
        ├── fees/
        ├── grades/
        ├── attendance/
        ├── announcements/
        └── complaints/
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Patricianduku/Ujumbe360.git
   cd Ujumbe360
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (for admin access)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Admin Portal: http://127.0.0.1:8000/admin-portal/
   - Parent Portal: http://127.0.0.1:8000/parent-portal/
   - Login: http://127.0.0.1:8000/login/

##  Default User Roles

### Admin/Staff Login
- Username: Your chosen username during superuser creation
- Password: Your chosen password
- Access: Full administrative privileges

### Parent Login
- Username: Student's admission number
- Password: Parent's phone number or custom password
- Access: Limited to their child's information

##  Database Models

### Core Models
- **Student**: Student records and information
- **FeeStructure**: Fee definitions by class level
- **Payment**: Payment records and transactions
- **Exam**: Exam/Assessment definitions
- **Grade**: Student academic performance
- **Attendance**: Student attendance records
- **Announcement**: School announcements and notices
- **Complaint**: Parent/student complaints and threads

##  Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Settings Customization
Modify `ujumbe360/settings.py` for:
- Database configuration
- Email settings
- File upload settings
- Security settings

##  Testing

Run the test suite:
```bash
python manage.py test
```

##  Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in settings
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up PostgreSQL database
- [ ] Configure static files serving
- [ ] Set up proper ALLOWED_HOSTS
- [ ] Configure email settings
- [ ] Set up HTTPS/SSL certificates

### Docker Deployment
```bash
# Build and run with Docker
docker build -t ujumbe360 .
docker run -p 8000:8000 ujumbe360
```

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


##  Acknowledgments

- Django Framework for the robust backend
- Bootstrap for the responsive UI components
- Bootstrap Icons for the icon set
- All contributors who have helped improve this project

##  Future Roadmap

- [ ] Mobile application (React Native)
- [ ] Advanced reporting and analytics
- [ ] SMS notifications integration
- [ ] Online payment gateway integration
- [ ] Multi-school support
- [ ] API documentation with Swagger
- [ ] Automated backup system
- [ ] Advanced user role management

---

**Ujumbe360** - Empowering educational institutions with modern technology solutions.

