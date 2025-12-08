from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from decimal import Decimal

from .models import (
    Student, FeeStructure, Payment, Subject, Exam, Grade, Attendance,
    Announcement, Complaint, ComplaintThread
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
    fee_structures = FeeStructure.objects.all()
    return render(request, 'fees/fee_list.html', {'fee_structures': fee_structures})


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
                return redirect('complaint_detail', pk=complaint.id)
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
def complaint_create(request):
    is_parent = not is_staff_user(request.user)
    
    if request.method == 'POST':
        form = ComplaintForm(request.POST, is_parent=is_parent)
        if form.is_valid():
            complaint = form.save()
            messages.success(request, 'Complaint submitted successfully!')
            if is_parent:
                return redirect('complaint_detail', pk=complaint.id)
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
    parent_name = request.user.get_full_name()

    complaints = Complaint.objects.filter(parent_name=parent_name)

    return render(request, 'parents/complaints_list.html', {
        'complaints': complaints
    })

# ===============================
# PARENT PORTAL VIEWS
# ===============================

def parent_children(request):
    return render(request, 'parent_portal/reports.html')

def parent_grades(request):
    return render(request, 'parent_portal/grades.html')

def parent_fees(request):
    return render(request, 'parent_portal/fees.html')

def parent_announcements(request):
    return render(request, 'parent_portal/announcements.html')

def parent_complaints(request):
    return render(request, 'parent_portal/complaints.html')


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
    
    def post(self, request, *args, **kwargs):
        login_type = request.POST.get('login_type', 'staff')
        admission_number = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Parent login: admission number + parent phone/password
        if login_type == 'parent':
            from django.contrib.auth import authenticate, login
            user = authenticate(request, username=admission_number, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome! Logged in with admission number: {admission_number}')
                if is_staff_user(user):
                    return redirect('admin_dashboard')
                else:
                    return redirect('parent_dashboard')
            else:
                messages.error(request, 'Invalid admission number or parent phone. Please check and try again.')
                return render(request, self.template_name, {'form': self.get_form()})
        
        # Staff login: username and password required
        if login_type == 'staff' and password:
            return super().post(request, *args, **kwargs)
        
        # Fallback: try standard authentication
        return super().post(request, *args, **kwargs)
    
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
