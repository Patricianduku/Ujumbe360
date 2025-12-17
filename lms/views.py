from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import requests
import json
import base64
import datetime

from .models import (
    Student, FeeStructure, Payment, Subject, Exam, Grade, Attendance,
    Announcement, Complaint, ComplaintThread, MPesaTransaction
)
from .forms import (
    StudentForm, FeeStructureForm, PaymentForm, SubjectForm, ExamForm, GradeForm, AttendanceForm,
    AnnouncementForm, ComplaintForm, ComplaintThreadForm
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def is_staff_user(user):
    return user.is_staff or user.is_superuser


def get_parent_student(request):
    """
    Resolve the student linked to a logged-in parent.
    Priority:
    - session 'student_admission_number'
    - username (raw admission number or prefixed parent_)
    """
    admission_number = request.session.get("student_admission_number")
    if not admission_number and getattr(request, "user", None):
        username = request.user.username
        if username.startswith("parent_"):
            admission_number = username.replace("parent_", "")
        else:
            admission_number = username
    if not admission_number:
        return None
    try:
        return Student.objects.get(admission_number=admission_number)
    except Student.DoesNotExist:
        return None


# ============================================================
# 1. STUDENT MANAGEMENT VIEWS
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def student_list(request):
    students = Student.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(admission_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(parent_name__icontains=search_query) |
            Q(parent_phone__icontains=search_query)
        )
    
    # Filter by class_level
    class_filter = request.GET.get('class_level', '')
    if class_filter:
        students = students.filter(class_level=class_filter)
    
    # Get unique class levels for filter dropdown
    class_levels = Student.objects.values_list('class_level', flat=True).distinct().order_by('class_level')
    
    context = {
        'students': students,
        'search_query': search_query,
        'class_filter': class_filter,
        'class_levels': class_levels,
    }
    return render(request, 'students/student_list.html', context)


@login_required
@user_passes_test(is_staff_user)
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student created successfully!')
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'students/student_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_user)
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/student_form.html', {'form': form, 'student': student, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully!')
        return redirect('student_list')
    return render(request, 'students/student_confirm_delete.html', {'student': student})


# ============================================================
# 2. FEES MODULE VIEWS
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def fee_list(request):
    """Enhanced fee management with analytics and search functionality"""
    
    # Get all students with their fee information
    students = Student.objects.all().prefetch_related('payments')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    payment_status = request.GET.get('payment_status', '')
    
    if search_query:
        students = students.filter(
            Q(admission_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(parent_name__icontains=search_query)
        )
    
    # Calculate fee analytics for each student
    student_fee_data = []
    total_expected = 0
    total_collected = 0
    
    for student in students:
        # Get fee structure for student's class
        try:
            fee_structure = FeeStructure.objects.get(class_level=student.class_level)
            expected_amount = fee_structure.amount_required
        except FeeStructure.DoesNotExist:
            expected_amount = 0
        
        # Get total payments for this student
        total_paid = student.payments.aggregate(
            total=Coalesce(Sum('amount_paid'), Decimal('0.00'))
        )['total'] or Decimal('0.00')
        
        # Calculate balance
        balance = expected_amount - total_paid
        
        # Determine payment status
        if balance <= 0:
            status = 'Fully Paid'
        elif total_paid > 0:
            status = 'Partial Payment'
        else:
            status = 'No Payment'
        
        # Filter by payment status if specified
        if payment_status and payment_status != status:
            continue
        
        student_fee_data.append({
            'student': student,
            'expected_amount': expected_amount,
            'total_paid': total_paid,
            'balance': balance,
            'status': status
        })
        
        total_expected += expected_amount
        total_collected += total_paid
    
    # Calculate overall analytics
    total_pending = total_expected - total_collected
    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0
    
    # Sort students by balance (highest arrears first)
    student_fee_data.sort(key=lambda x: x['balance'], reverse=True)
    
    context = {
        'student_fee_data': student_fee_data,
        'search_query': search_query,
        'payment_status': payment_status,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'collection_rate': collection_rate,
        'total_students': len(student_fee_data),
    }
    
    return render(request, 'admin_portal/fees_list.html', context)


@login_required
@user_passes_test(is_staff_user)
def fee_structure_create(request):
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee structure created successfully!')
            return redirect('fee_list')
    else:
        form = FeeStructureForm()
    return render(request, 'fees/fee_structure_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_user)
def fee_structure_update(request, pk):
    fee_structure = get_object_or_404(FeeStructure, pk=pk)
    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=fee_structure)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee structure updated successfully!')
            return redirect('fee_list')
    else:
        form = FeeStructureForm(instance=fee_structure)
    return render(request, 'fees/fee_structure_form.html', {'form': form, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def fee_structure_delete(request, pk):
    fee_structure = get_object_or_404(FeeStructure, pk=pk)
    if request.method == 'POST':
        fee_structure.delete()
        messages.success(request, 'Fee structure deleted successfully!')
        return redirect('fee_list')
    return render(request, 'fees/fee_structure_confirm_delete.html', {'fee_structure': fee_structure})


@login_required
def student_fee_detail(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    
    # Check if user is parent - only allow access to their own child
    if not is_staff_user(request.user):
        parent_student = get_parent_student(request)
        if not parent_student or parent_student.id != student.id:
            messages.error(request, "You do not have permission to view this student's information.")
            return redirect('parent_dashboard')
    
    # Get fee structure for student's class
    try:
        fee_structure = FeeStructure.objects.get(class_level=student.class_level)
        total_required = fee_structure.amount_required
    except FeeStructure.DoesNotExist:
        fee_structure = None
        total_required = Decimal('0.00')
    
    # Get all payments for this student
    payments = Payment.objects.filter(student=student).order_by('date', 'created_at')
    
    # Calculate totals
    total_paid = payments.aggregate(
        total=Coalesce(Sum('amount_paid'), Decimal('0.00'))
    )['total'] or Decimal('0.00')
    
    balance = total_required - total_paid
    
    context = {
        'student': student,
        'fee_structure': fee_structure,
        'total_required': total_required,
        'total_paid': total_paid,
        'balance': balance,
        'payments': payments,
    }
    return render(request, 'fees/student_fee_detail.html', context)


@login_required
@user_passes_test(is_staff_user)  # Only staff can add payments
def add_payment(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    
    # Get fee structure for student's class
    try:
        fee_structure = FeeStructure.objects.get(class_level=student.class_level)
        total_required = fee_structure.amount_required
    except FeeStructure.DoesNotExist:
        total_required = Decimal('0.00')
    
    # Calculate current balance
    total_paid = Payment.objects.filter(student=student).aggregate(
        total=Coalesce(Sum('amount_paid'), Decimal('0.00'))
    )['total'] or Decimal('0.00')
    
    current_balance = total_required - total_paid
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student = student
            
            # Calculate balance after this payment
            new_balance = current_balance - payment.amount_paid
            payment.balance_after = new_balance
            payment.save()
            
            messages.success(request, f'Payment of KSh {payment.amount_paid} recorded successfully!')
            return redirect('student_fee_detail', student_id=student.id)
    else:
        form = PaymentForm(initial={'student': student})
    
    context = {
        'form': form,
        'student': student,
        'current_balance': current_balance,
        'total_required': total_required,
    }
    return render(request, 'fees/add_payment.html', context)


# ============================================================
# ATTENDANCE (STAFF)
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def attendance_list(request):
    records = Attendance.objects.select_related('student')
    student_q = request.GET.get('student', '')
    status_q = request.GET.get('status', '')
    if student_q:
        records = records.filter(student__admission_number__icontains=student_q)
    if status_q:
        records = records.filter(status=status_q)
    records = records.order_by('-date', 'student__admission_number')
    return render(request, 'attendance/attendance_list.html', {
        'records': records,
        'student_q': student_q,
        'status_q': status_q,
        'statuses': Attendance.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_staff_user)
def attendance_create(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance recorded.')
            return redirect('attendance_list')
    else:
        form = AttendanceForm()
    return render(request, 'attendance/attendance_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_user)
def attendance_update(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance updated.')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=record)
    return render(request, 'attendance/attendance_form.html', {'form': form, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def attendance_delete(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Attendance deleted.')
        return redirect('attendance_list')
    return render(request, 'attendance/attendance_confirm_delete.html', {'record': record})


# ============================================================
# 3. ACADEMIC / GRADES MODULE VIEWS
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def exam_list(request):
    exams = Exam.objects.all()
    return render(request, 'grades/exam_list.html', {'exams': exams})


@login_required
@user_passes_test(is_staff_user)
def exam_create(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam created successfully!')
            return redirect('exam_list')
    else:
        form = ExamForm()
    return render(request, 'grades/exam_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_user)
def exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam updated successfully!')
            return redirect('exam_list')
    else:
        form = ExamForm(instance=exam)
    return render(request, 'grades/exam_form.html', {'form': form, 'exam': exam, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == 'POST':
        exam.delete()
        messages.success(request, 'Exam deleted successfully!')
        return redirect('exam_list')
    return render(request, 'grades/exam_confirm_delete.html', {'exam': exam})


@login_required
@user_passes_test(is_staff_user)
def grade_entry(request):
    if request.method == 'POST':
        form = GradeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade entered successfully!')
            return redirect('grade_entry')
    else:
        form = GradeForm()
    
    # Get recent grades
    recent_grades = Grade.objects.all()[:10]
    
    context = {
        'form': form,
        'recent_grades': recent_grades,
    }
    return render(request, 'grades/grade_entry.html', context)


@login_required
@user_passes_test(is_staff_user)
def grade_update(request, pk):
    grade = get_object_or_404(Grade, pk=pk)
    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade)
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade updated successfully!')
            return redirect('grade_entry')
    else:
        form = GradeForm(instance=grade)
    return render(request, 'grades/grade_form.html', {'form': form, 'grade': grade, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def grade_delete(request, pk):
    grade = get_object_or_404(Grade, pk=pk)
    if request.method == 'POST':
        grade.delete()
        messages.success(request, 'Grade deleted successfully!')
        return redirect('grade_entry')
    return render(request, 'grades/grade_confirm_delete.html', {'grade': grade})


@login_required
def student_academic_report(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    
    # Check if user is parent - only allow access to their own child
    if not is_staff_user(request.user):
        parent_student = get_parent_student(request)
        if not parent_student or parent_student.id != student.id:
            messages.error(request, "You do not have permission to view this student's information.")
            return redirect('parent_dashboard')
    grades = Grade.objects.filter(student=student).select_related('subject', 'exam').order_by('exam', 'subject')
    
    # Group grades by exam
    exams_data = {}
    for grade in grades:
        exam_key = grade.exam.id
        if exam_key not in exams_data:
            exams_data[exam_key] = {
                'exam': grade.exam,
                'grades': []
            }
        exams_data[exam_key]['grades'].append(grade)
    
    # Calculate averages per exam
    for exam_data in exams_data.values():
        scores = [float(g.score) for g in exam_data['grades']]
        exam_data['average'] = sum(scores) / len(scores) if scores else 0

    # Prepare trend data
    exam_labels = [f"{data['exam'].term} {data['exam'].year}" for data in exams_data.values()]
    exam_averages = [data['average'] for data in exams_data.values()]
    
    context = {
        'student': student,
        'exams_data': exams_data.values(),
        'exam_labels': exam_labels,
        'exam_averages': exam_averages,
    }
    return render(request, 'grades/student_academic_report.html', context)


# ============================================================
# 4. ANNOUNCEMENT SYSTEM VIEWS
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def announcement_list(request):
    announcements = Announcement.objects.all()
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        announcements = announcements.filter(category=category_filter)
    
    # Get unique categories for filter
    categories = Announcement.CATEGORY_CHOICES
    
    context = {
        'announcements': announcements,
        'category_filter': category_filter,
        'categories': categories,
    }
    return render(request, 'announcements/announcement_list.html', context)


@login_required
@user_passes_test(is_staff_user)
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement created successfully!')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_user)
def announcement_update(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement updated successfully!')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'announcements/announcement_form.html', {'form': form, 'announcement': announcement, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
        return redirect('announcement_list')
    return render(request, 'announcements/announcement_confirm_delete.html', {'announcement': announcement})


@login_required
def announcement_view(request):
    """View for all users (parents and staff) to see announcements"""
    announcements = Announcement.objects.all()
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        announcements = announcements.filter(category=category_filter)
    
    categories = Announcement.CATEGORY_CHOICES
    
    context = {
        'announcements': announcements,
        'category_filter': category_filter,
        'categories': categories,
    }
    return render(request, 'announcements/announcement_view.html', context)


# ============================================================
# 5. COMPLAINTS MODULE VIEWS
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def complaint_list(request):
    complaints = Complaint.objects.all()
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    
    context = {
        'complaints': complaints,
        'status_filter': status_filter,
        'status_choices': Complaint.STATUS_CHOICES,
    }
    return render(request, 'complaints/complaint_list.html', context)


@login_required
def complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    threads = ComplaintThread.objects.filter(complaint=complaint).order_by('timestamp')
    is_staff = is_staff_user(request.user)
    
    if request.method == 'POST':
        # Handle thread reply
        thread_form = ComplaintThreadForm(request.POST, sender_type='Admin' if is_staff else 'Parent')
        if thread_form.is_valid():
            thread = thread_form.save(commit=False)
            thread.complaint = complaint
            thread.sender_type = 'Admin' if is_staff else 'Parent'
            thread.save()
            messages.success(request, 'Reply sent successfully!')
            if is_staff:
                return redirect('complaint_detail_admin', pk=complaint.id)
            else:
                return redirect('parent_complaint_detail', pk=complaint.id)
    else:
        thread_form = ComplaintThreadForm(sender_type='Admin' if is_staff else 'Parent')
    
    # Handle status update (admin only)
    if request.method == 'POST' and 'update_status' in request.POST and is_staff:
        new_status = request.POST.get('status')
        if new_status in dict(Complaint.STATUS_CHOICES):
            complaint.status = new_status
            complaint.save()
            messages.success(request, 'Status updated successfully!')
            return redirect('complaint_detail_admin', pk=complaint.id)
    
    context = {
        'complaint': complaint,
        'threads': threads,
        'thread_form': thread_form,
        'is_staff': is_staff,
    }
    
    # Use admin template for staff, parent template for parents
    template = 'complaints/complaint_detail.html' if is_staff else 'complaints/complaint_detail_parent.html'
    return render(request, template, context)


@login_required
def complaint_detail_parent(request, pk):
    """Dedicated view for parent complaint details"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    # Verify the parent has permission to view this complaint
    student = get_parent_student(request)
    if not student or complaint.student.id != student.id:
        messages.error(request, "You do not have permission to view this complaint.")
        return redirect('parent_complaints')
    
    threads = ComplaintThread.objects.filter(complaint=complaint).order_by('timestamp')
    
    if request.method == 'POST':
        # Handle thread reply
        thread_form = ComplaintThreadForm(request.POST, sender_type='Parent')
        if thread_form.is_valid():
            thread = thread_form.save(commit=False)
            thread.complaint = complaint
            thread.sender_type = 'Parent'
            thread.save()
            messages.success(request, 'Reply sent successfully!')
            return redirect('parent_complaint_detail', pk=complaint.id)
    else:
        thread_form = ComplaintThreadForm(sender_type='Parent')
    
    context = {
        'complaint': complaint,
        'threads': threads,
        'thread_form': thread_form,
        'is_staff': False,
    }
    
    return render(request, 'complaints/complaint_detail_parent.html', context)


@login_required
def complaint_create(request):
    is_parent = not is_staff_user(request.user)
    
    if request.method == 'POST':
        form = ComplaintForm(request.POST, is_parent=is_parent)
        if form.is_valid():
            complaint = form.save()
            messages.success(request, 'Complaint submitted successfully!')
            if is_parent:
                return redirect('parent_complaint_detail', pk=complaint.id)
            else:
                return redirect('complaint_list')
    else:
        form = ComplaintForm(is_parent=is_parent)
    
    template = 'complaints/complaint_form.html' if not is_parent else 'complaints/complaint_form_parent.html'
    return render(request, template, {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_user)
def complaint_update(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST':
        form = ComplaintForm(request.POST, instance=complaint, is_parent=False)
        if form.is_valid():
            form.save()
            messages.success(request, 'Complaint updated successfully!')
            return redirect('complaint_list')
    else:
        form = ComplaintForm(instance=complaint, is_parent=False)
    return render(request, 'complaints/complaint_form.html', {'form': form, 'complaint': complaint, 'action': 'Update'})


@login_required
@user_passes_test(is_staff_user)
def complaint_delete(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST':
        complaint.delete()
        messages.success(request, 'Complaint deleted successfully!')
        return redirect('complaint_list')
    return render(request, 'complaints/complaint_confirm_delete.html', {'complaint': complaint})

def parent_complaints(request):
    student = get_parent_student(request)
    if not student:
        messages.error(request, "Unable to find student information.")
        return redirect('parent_dashboard')
    complaints = Complaint.objects.filter(student=student).order_by('-created_at')
    return render(request, 'parent_portal/complaints.html', {'student': student, 'complaints': complaints})

# ===============================
# PARENT PORTAL VIEWS
# ===============================

def parent_children(request):
    student = get_parent_student(request)
    if not student:
        messages.error(request, "Unable to find student information.")
        return redirect('parent_dashboard')
    
    # Calculate student's age
    today = datetime.date.today()
    age = today.year - student.date_of_birth.year
    if today.month < student.date_of_birth.month or (today.month == student.date_of_birth.month and today.day < student.date_of_birth.day):
        age -= 1
    
    return render(request, 'parent_portal/student_detail.html', {'student': student, 'age': age})

def parent_grades(request):
    student = get_parent_student(request)
    if not student:
        messages.error(request, "Unable to find student information.")
        return redirect('parent_dashboard')
    grades = Grade.objects.filter(student=student).select_related('subject', 'exam').order_by('-exam__year', '-exam__term')
    return render(request, 'parent_portal/grades.html', {'student': student, 'grades': grades})

def parent_fees(request):
    student = get_parent_student(request)
    if not student:
        messages.error(request, "Unable to find student information.")
        return redirect('parent_dashboard')
    return redirect('student_fee_detail', student_id=student.id)

def parent_announcements(request):
    announcements = Announcement.objects.all().order_by('-is_pinned', '-created_at')[:10]
    return render(request, 'parent_portal/announcements.html', {'announcements': announcements})

def parent_complaints(request):
    student = get_parent_student(request)
    if not student:
        messages.error(request, "Unable to find student information.")
        return redirect('parent_dashboard')
    complaints = Complaint.objects.filter(student=student).order_by('-created_at')
    return render(request, 'parent_portal/complaints.html', {'student': student, 'complaints': complaints})


# ============================================================
# AUTHENTICATION VIEWS
# ============================================================
def home(request):
    """Home page - always redirects to login page"""
    # Force redirect to login page with explicit URL
    from django.http import HttpResponseRedirect
    print(f"DEBUG: Home view called, user authenticated: {request.user.is_authenticated}")
    # Log out the user first to prevent automatic redirects
    if request.user.is_authenticated:
        from django.contrib.auth import logout
        logout(request)
        print("DEBUG: User logged out")
    return HttpResponseRedirect('/login/')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = False
    
    def get_success_url(self):
        if is_staff_user(self.request.user):
            return '/admin-portal/'
        else:
            return '/parent-portal/'

# ============================================================
# DASHBOARD VIEWS
# ============================================================
@login_required
@user_passes_test(is_staff_user)
def admin_dashboard(request):
    context = {
        'students_count': Student.objects.count(),
        'fee_structures_count': FeeStructure.objects.count(),
        'exams_count': Exam.objects.count(),
        'announcements_count': Announcement.objects.count(),
        'complaints_count': Complaint.objects.filter(status='Pending').count(),
    }
    return render(request, 'admin_portal/dashboard.html', context)


@login_required
def parent_dashboard(request):
    """Parent dashboard - shows their child's information and summaries"""
    student = get_parent_student(request)

    # Fee summary
    total_required = Decimal('0.00')
    total_paid = Decimal('0.00')
    balance = Decimal('0.00')
    recent_payments = []

    # Academic summary
    recent_grades = []
    latest_exam = None
    avg_score = None

    # Attendance summary
    attendance_summary = {'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'total': 0}
    attendance_recent = []

    if student:
        fee_structure = FeeStructure.objects.filter(class_level=student.class_level).first()
        if fee_structure:
            total_required = fee_structure.amount_required
        total_paid = student.payments.aggregate(
            total=Coalesce(Sum('amount_paid'), Decimal('0.00'))
        )['total'] or Decimal('0.00')
        balance = total_required - total_paid
        recent_payments = student.payments.all()[:5]

        recent_grades = student.grades.select_related('exam', 'subject').order_by('-exam__year', '-exam__term')[:6]
        if recent_grades:
            latest_exam = recent_grades[0].exam
            latest_exam_grades = student.grades.filter(exam=latest_exam)
            if latest_exam_grades.exists():
                avg_score = latest_exam_grades.aggregate(
                    avg=Coalesce(Sum('score'), Decimal('0')) / len(latest_exam_grades)
                )['avg']

        # Attendance
        attendance_qs = student.attendance_records.order_by('-date')
        attendance_summary['total'] = attendance_qs.count()
        attendance_summary['present'] = attendance_qs.filter(status='Present').count()
        attendance_summary['absent'] = attendance_qs.filter(status='Absent').count()
        attendance_summary['late'] = attendance_qs.filter(status='Late').count()
        attendance_summary['excused'] = attendance_qs.filter(status='Excused').count()
        attendance_recent = attendance_qs[:7]

    recent_announcements = Announcement.objects.filter(is_pinned=True)[:3]

    context = {
        'student': student,
        'recent_announcements': recent_announcements,
        'recent_payments': recent_payments,
        'total_required': total_required,
        'total_paid': total_paid,
        'balance': balance,
        'recent_grades': recent_grades,
        'latest_exam': latest_exam,
        'avg_score': avg_score,
        'attendance_summary': attendance_summary,
        'attendance_recent': attendance_recent,
    }
    return render(request, 'parent_portal/dashboard.html', context)

def _normalize_msisdn(phone_number: str) -> str:
    """
    Convert Kenyan numbers into 2547XXXXXXXX format.
    Accepts: 07.., 7.., +2547.., 2547..
    """
    if not phone_number:
        return ""

    msisdn = str(phone_number).strip().replace(" ", "")
    if msisdn.startswith("+"):
        msisdn = msisdn[1:]

    if msisdn.startswith("0") and len(msisdn) >= 10:
        msisdn = "254" + msisdn[1:]
    elif msisdn.startswith("7") and len(msisdn) >= 9:
        msisdn = "254" + msisdn
    elif msisdn.startswith("254") and len(msisdn) >= 12:
        pass
    else:
        # Best-effort: if user entered without 254 and without leading 0.
        if not msisdn.startswith("254"):
            msisdn = "254" + msisdn.lstrip("0")

    return msisdn


def _mpesa_timestamp() -> str:
    # Daraja typically expects EAT-like timestamp format: YYYYMMDDHHMMSS
    try:
        from zoneinfo import ZoneInfo
        return timezone.now().astimezone(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
    except Exception:
        return timezone.now().strftime("%Y%m%d%H%M%S")


def _mpesa_password(timestamp: str) -> str:
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def _mpesa_access_token() -> str:
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        raise Exception("Missing MPESA_CONSUMER_KEY/MPESA_CONSUMER_SECRET in environment variables.")

    auth = base64.b64encode(
        f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode("utf-8")
    ).decode("utf-8")

    resp = requests.get(
        settings.MPESA_OAUTH_URL,
        headers={"Authorization": f"Basic {auth}"},
        timeout=30,
    )
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise Exception(f"Failed to obtain M-Pesa access token: {data}")
    return token


def initiate_stk_push(phone_number, amount, account_reference, transaction_desc, callback_url, mpesa_transaction):
    """
    Initiate M-Pesa STK Push using Safaricom Daraja API.
    Uses settings values from .env (see [`ujumbe360/settings.py`](ujumbe360/settings.py:1)).

    Note: callback_url parameter is kept for backward compatibility, but if
    settings.MPESA_CALLBACK_URL is set, it will be used.
    """
    msisdn = _normalize_msisdn(phone_number)
    if not msisdn:
        raise Exception("Invalid phone number")

    try:
        amount_int = int(Decimal(amount))
    except Exception:
        raise Exception("Invalid amount")

    if amount_int < 1:
        raise Exception("Amount must be at least 1")

    callback = getattr(settings, "MPESA_CALLBACK_URL", None) or callback_url
    if not callback:
        raise Exception("Missing callback URL")

    timestamp = _mpesa_timestamp()
    password = _mpesa_password(timestamp)
    token = _mpesa_access_token()

    payload = {
        "BusinessShortCode": str(settings.MPESA_SHORTCODE),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount_int,
        "PartyA": msisdn,
        "PartyB": str(settings.MPESA_SHORTCODE),
        "PhoneNumber": msisdn,
        "CallBackURL": callback,
        "AccountReference": str(account_reference)[:12] if account_reference else "Ujumbe360",
        "TransactionDesc": str(transaction_desc)[:50] if transaction_desc else "Payment",
    }

    resp = requests.post(
        settings.MPESA_STKPUSH_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    data = resp.json()

    # Store immediate response (helps debugging when Daraja rejects request)
    mpesa_transaction.result_code = data.get("ResponseCode") or mpesa_transaction.result_code
    mpesa_transaction.result_description = data.get("ResponseDescription") or mpesa_transaction.result_description
    mpesa_transaction.callback_data = {"stkpush_request": payload, "stkpush_response": data}
    mpesa_transaction.save(update_fields=["result_code", "result_description", "callback_data", "updated_at"])

    return data


@login_required
def initiate_mpesa_payment(request, student_id):
    """
    Existing form-based initiation (kept for your current UI).
    This now uses the correct public callback URL:
    https://clarice-zaniest-bettyann.ngrok-free.dev/api/mpesa/callback/
    """
    student = get_object_or_404(Student, pk=student_id)

    # Check if user is parent - only allow access to their own child
    if not is_staff_user(request.user):
        parent_student = get_parent_student(request)
        if not parent_student or parent_student.id != student.id:
            messages.error(request, "You do not have permission to view this student's information.")
            return redirect("parent_dashboard")

    if request.method != "POST":
        return redirect("student_fee_detail", student_id=student.id)

    phone_number = request.POST.get("phone_number")
    amount_raw = request.POST.get("amount")

    if not phone_number or not amount_raw:
        messages.error(request, "Phone number and amount are required.")
        return redirect("student_fee_detail", student_id=student.id)

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        messages.error(request, "Invalid amount specified.")
        return redirect("student_fee_detail", student_id=student.id)

    msisdn = _normalize_msisdn(phone_number)
    if not msisdn:
        messages.error(request, "Invalid phone number.")
        return redirect("student_fee_detail", student_id=student.id)

    mpesa_transaction = MPesaTransaction.objects.create(
        student=student,
        amount=amount,
        phone_number=msisdn,
        status="Pending",
    )

    try:
        stk_push_response = initiate_stk_push(
            phone_number=msisdn,
            amount=amount,
            account_reference=f"Student_{student.admission_number}",
            transaction_desc=f"School fees for {student.full_name}",
            callback_url=settings.MPESA_CALLBACK_URL,
            mpesa_transaction=mpesa_transaction,
        )

        if stk_push_response.get("ResponseCode") == "0":
            mpesa_transaction.merchant_request_id = stk_push_response.get("MerchantRequestID")
            mpesa_transaction.checkout_request_id = stk_push_response.get("CheckoutRequestID")
            mpesa_transaction.save(update_fields=["merchant_request_id", "checkout_request_id", "updated_at"])

            messages.success(request, "M-Pesa STK push sent to your phone. Please complete the payment.")
            return redirect("student_fee_detail", student_id=student.id)

        mpesa_transaction.status = "Failed"
        mpesa_transaction.result_code = stk_push_response.get("ResponseCode")
        mpesa_transaction.result_description = stk_push_response.get("ResponseDescription", "")
        mpesa_transaction.save(update_fields=["status", "result_code", "result_description", "updated_at"])

        messages.error(
            request,
            f'M-Pesa payment initiation failed: {stk_push_response.get("ResponseDescription", "Unknown error")}',
        )
        return redirect("student_fee_detail", student_id=student.id)

    except Exception as e:
        mpesa_transaction.status = "Failed"
        mpesa_transaction.result_description = str(e)
        mpesa_transaction.save(update_fields=["status", "result_description", "updated_at"])

        messages.error(request, "Payment initiation failed. Please try again.")
        return redirect("student_fee_detail", student_id=student.id)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mpesa_stkpush(request):
    """
    JSON/form endpoint for your modal UI.

    Initiation endpoint required by you:
    https://clarice-zaniest-bettyann.ngrok-free.dev/api/mpesa/stkpush/

    Accepts either JSON or form POST:
      - phone_number
      - amount
      - student_id (optional; required for staff; ignored for parent)
    """
    try:
        if request.content_type and "application/json" in request.content_type:
            payload_in = json.loads(request.body.decode("utf-8") or "{}")
        else:
            payload_in = request.POST

        phone_number = payload_in.get("phone_number")
        amount_raw = payload_in.get("amount")
        student_id = payload_in.get("student_id")

        if not phone_number or not amount_raw:
            return JsonResponse({"error": "phone_number and amount are required"}, status=400)

        try:
            amount = Decimal(str(amount_raw))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except Exception:
            return JsonResponse({"error": "Invalid amount"}, status=400)

        # Resolve student
        if is_staff_user(request.user):
            if not student_id:
                return JsonResponse({"error": "student_id is required for staff users"}, status=400)
            student = get_object_or_404(Student, pk=int(student_id))
        else:
            student = get_parent_student(request)
            if not student:
                return JsonResponse({"error": "Unable to resolve student for this parent account"}, status=400)

        msisdn = _normalize_msisdn(phone_number)
        if not msisdn:
            return JsonResponse({"error": "Invalid phone number"}, status=400)

        mpesa_transaction = MPesaTransaction.objects.create(
            student=student,
            amount=amount,
            phone_number=msisdn,
            status="Pending",
        )

        stk_push_response = initiate_stk_push(
            phone_number=msisdn,
            amount=amount,
            account_reference=f"Student_{student.admission_number}",
            transaction_desc=f"School fees for {student.full_name}",
            callback_url=settings.MPESA_CALLBACK_URL,
            mpesa_transaction=mpesa_transaction,
        )

        if stk_push_response.get("ResponseCode") == "0":
            mpesa_transaction.merchant_request_id = stk_push_response.get("MerchantRequestID")
            mpesa_transaction.checkout_request_id = stk_push_response.get("CheckoutRequestID")
            mpesa_transaction.save(update_fields=["merchant_request_id", "checkout_request_id", "updated_at"])

            return JsonResponse(
                {
                    "ok": True,
                    "transaction_id": mpesa_transaction.id,
                    "merchant_request_id": mpesa_transaction.merchant_request_id,
                    "checkout_request_id": mpesa_transaction.checkout_request_id,
                    "message": stk_push_response.get("CustomerMessage"),
                },
                status=200,
            )

        mpesa_transaction.status = "Failed"
        mpesa_transaction.result_code = stk_push_response.get("ResponseCode")
        mpesa_transaction.result_description = stk_push_response.get("ResponseDescription", "")
        mpesa_transaction.save(update_fields=["status", "result_code", "result_description", "updated_at"])

        return JsonResponse(
            {"ok": False, "transaction_id": mpesa_transaction.id, "error": mpesa_transaction.result_description},
            status=400,
        )

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """
    Daraja STK Push callback (public endpoint).

    Callback URL required by you:
    https://clarice-zaniest-bettyann.ngrok-free.dev/api/mpesa/callback/

    Daraja payload shape:
    {
      "Body": {
        "stkCallback": {
          "MerchantRequestID": "...",
          "CheckoutRequestID": "...",
          "ResultCode": 0,
          "ResultDesc": "...",
          "CallbackMetadata": { "Item": [ {"Name":"Amount","Value":...}, ... ] }
        }
      }
    }
    """
    try:
        callback_data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        # Always ACK to stop retries; store nothing if invalid
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    stk = (
        callback_data.get("Body", {})
        .get("stkCallback", {})
    )

    merchant_request_id = stk.get("MerchantRequestID")
    checkout_request_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    result_description = stk.get("ResultDesc")

    # Metadata items -> dict
    items = stk.get("CallbackMetadata", {}).get("Item", []) or []
    meta = {}
    for it in items:
        name = it.get("Name")
        if name:
            meta[name] = it.get("Value")

    amount = meta.get("Amount")
    receipt = meta.get("MpesaReceiptNumber")
    phone = meta.get("PhoneNumber")
    tx_date_raw = meta.get("TransactionDate")  # e.g. 20231209203045 (int)

    # Find transaction (checkout_request_id is typically unique per request)
    mpesa_transaction = None
    if checkout_request_id:
        mpesa_transaction = MPesaTransaction.objects.filter(checkout_request_id=checkout_request_id).first()
    if not mpesa_transaction and merchant_request_id and checkout_request_id:
        mpesa_transaction = MPesaTransaction.objects.filter(
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
        ).first()

    if not mpesa_transaction:
        # ACK anyway (Daraja expects HTTP 200); keep for debugging
        print(f"M-Pesa callback: Transaction not found. MerchantRequestID={merchant_request_id} CheckoutRequestID={checkout_request_id}")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    # Store callback data (always)
    mpesa_transaction.callback_data = callback_data
    mpesa_transaction.result_code = str(result_code) if result_code is not None else None
    mpesa_transaction.result_description = result_description

    # If already completed, ACK idempotently
    if mpesa_transaction.status == "Completed":
        mpesa_transaction.save(update_fields=["callback_data", "result_code", "result_description", "updated_at"])
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    # Success vs failure
    try:
        result_code_int = int(result_code)
    except Exception:
        result_code_int = None

    if result_code_int == 0:
        mpesa_transaction.status = "Completed"
        if receipt:
            mpesa_transaction.mpesa_receipt_number = str(receipt)
        if phone:
            mpesa_transaction.phone_number = str(phone)

        # Parse TransactionDate
        if tx_date_raw:
            try:
                tx_dt = datetime.datetime.strptime(str(int(tx_date_raw)), "%Y%m%d%H%M%S")
                # Store as naive (project USE_TZ=True, Django will interpret if timezone-aware is required)
                mpesa_transaction.transaction_date = tx_dt
            except Exception:
                pass

        mpesa_transaction.save()

        # Create Payment record only once (idempotent)
        if not Payment.objects.filter(mpesa_transaction=mpesa_transaction).exists():
            Payment.objects.create(
                student=mpesa_transaction.student,
                amount_paid=mpesa_transaction.amount,
                date=(mpesa_transaction.transaction_date.date() if mpesa_transaction.transaction_date else datetime.date.today()),
                balance_after=calculate_balance_after_payment(mpesa_transaction.student, mpesa_transaction.amount),
                payment_method="M-Pesa",
                mpesa_transaction=mpesa_transaction,
            )

        print(f"M-Pesa payment successful: {mpesa_transaction.mpesa_receipt_number}")

    else:
        # Common cancel code is 1032
        mpesa_transaction.status = "Cancelled" if result_code_int == 1032 else "Failed"
        mpesa_transaction.save()
        print(f"M-Pesa payment not completed: {result_description} (code={result_code})")

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


def calculate_balance_after_payment(student, amount_paid):
    """Calculate student's balance after payment"""
    try:
        fee_structure = FeeStructure.objects.get(class_level=student.class_level)
        total_required = fee_structure.amount_required
    except FeeStructure.DoesNotExist:
        total_required = Decimal('0.00')
    
    total_paid = Payment.objects.filter(student=student).aggregate(
        total=Coalesce(Sum('amount_paid'), Decimal('0.00'))
    )['total'] or Decimal('0.00')
    
    # Add the current payment to total paid
    total_paid += amount_paid
    
    balance = total_required - total_paid
    return max(balance, Decimal('0.00'))


@login_required
def mpesa_payment_status(request, transaction_id):
    """Check M-Pesa payment status (AJAX endpoint)"""
    try:
        mpesa_transaction = MPesaTransaction.objects.get(id=transaction_id)
        return JsonResponse({
            'status': mpesa_transaction.status,
            'amount': str(mpesa_transaction.amount),
            'phone_number': mpesa_transaction.phone_number,
            'created_at': mpesa_transaction.created_at.isoformat(),
            'is_successful': mpesa_transaction.is_successful
        })
    except MPesaTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)
