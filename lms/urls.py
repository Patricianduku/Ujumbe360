from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

# Use Django's built-in LogoutView with custom next_page
logout_view = LogoutView.as_view(next_page='/login/')

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Dashboards
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('parent-portal/', views.parent_dashboard, name='parent_dashboard'),
    
    # ============================================================
    # 1. STUDENT MANAGEMENT
    # ============================================================
    path('admin-portal/students/', views.student_list, name='student_list'),
    path('admin-portal/students/create/', views.student_create, name='student_create'),
    path('admin-portal/students/<int:pk>/edit/', views.student_update, name='student_update'),
    path('admin-portal/students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    
    # ============================================================
    # 2. FEES MODULE
    # ============================================================
    path('admin-portal/fees/', views.fee_list, name='fee_list'),
    path('admin-portal/fees/structure/create/', views.fee_structure_create, name='fee_structure_create'),
    path('admin-portal/fees/structure/<int:pk>/edit/', views.fee_structure_update, name='fee_structure_update'),
    path('admin-portal/fees/structure/<int:pk>/delete/', views.fee_structure_delete, name='fee_structure_delete'),
    path('admin-portal/fees/student/<int:student_id>/', views.student_fee_detail, name='student_fee_detail'),
    path('admin-portal/fees/student/<int:student_id>/payment/add/', views.add_payment, name='add_payment'),
    
    # Attendance (staff)
    path('admin-portal/attendance/', views.attendance_list, name='attendance_list'),
    path('admin-portal/attendance/create/', views.attendance_create, name='attendance_create'),
    path('admin-portal/attendance/<int:pk>/edit/', views.attendance_update, name='attendance_update'),
    path('admin-portal/attendance/<int:pk>/delete/', views.attendance_delete, name='attendance_delete'),

    # ============================================================
    # 3. ACADEMIC / GRADES MODULE
    # ============================================================
    path('admin-portal/exams/', views.exam_list, name='exam_list'),
    path('admin-portal/exams/create/', views.exam_create, name='exam_create'),
    path('admin-portal/exams/<int:pk>/edit/', views.exam_update, name='exam_update'),
    path('admin-portal/exams/<int:pk>/delete/', views.exam_delete, name='exam_delete'),
    path('admin-portal/grades/entry/', views.grade_entry, name='grade_entry'),
    path('admin-portal/grades/<int:pk>/edit/', views.grade_update, name='grade_update'),
    path('admin-portal/grades/<int:pk>/delete/', views.grade_delete, name='grade_delete'),
    path('admin-portal/grades/student/<int:student_id>/report/', views.student_academic_report, name='student_academic_report'),
    
    # ============================================================
    # 4. ANNOUNCEMENT SYSTEM
    # ============================================================
    path('admin-portal/announcements/', views.announcement_list, name='announcement_list'),
    path('admin-portal/announcements/create/', views.announcement_create, name='announcement_create'),
    path('admin-portal/announcements/<int:pk>/edit/', views.announcement_update, name='announcement_update'),
    path('admin-portal/announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
    path('announcements/', views.announcement_view, name='announcement_view'),  # Public view
    
    # ============================================================
    # 5. COMPLAINTS MODULE
    # ============================================================
    path('admin-portal/complaints/', views.complaint_list, name='complaint_list'),
    path('admin-portal/complaints/<int:pk>/', views.complaint_detail, name='complaint_detail_admin'),
    path('admin-portal/complaints/<int:pk>/edit/', views.complaint_update, name='complaint_update'),
    path('admin-portal/complaints/<int:pk>/delete/', views.complaint_delete, name='complaint_delete'),
    path('complaints/create/', views.complaint_create, name='complaint_create'),
    path('complaints/<int:pk>/', views.complaint_detail, name='complaint_detail'),
    path('parent/complaints/', views.parent_complaints, name='parent_complaints'),
    
    # ===============================
    # PARENT PORTAL URLS
    # ===============================
    path('parent-portal/children/', views.parent_children, name='parent_children'),
    path('parent-portal/grades/', views.parent_grades, name='parent_grades'),
    path('parent-portal/fees/', views.parent_fees, name='parent_fees'),
    path('parent-portal/announcements/', views.parent_announcements, name='parent_announcements'),
    path('parent-portal/complaints/', views.parent_complaints, name='parent_complaints'),


]
