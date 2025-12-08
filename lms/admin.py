from django.contrib import admin
from .models import (
    Student, FeeStructure, Payment, Subject, Exam, Grade, Attendance,
    Announcement, Complaint, ComplaintThread
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'first_name', 'last_name', 'class_level', 'stream', 'parent_name', 'parent_phone']
    list_filter = ['class_level', 'gender', 'stream']
    search_fields = ['admission_number', 'first_name', 'last_name', 'parent_name', 'parent_phone']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ['class_level', 'amount_required']
    search_fields = ['class_level']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['student', 'amount_paid', 'date', 'balance_after']
    list_filter = ['date']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name']
    date_hierarchy = 'date'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'term', 'year']
    list_filter = ['term', 'year']
    search_fields = ['name']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'exam', 'score', 'grade_letter']
    list_filter = ['exam', 'subject', 'grade_letter']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name', 'subject__name']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'status', 'remarks']
    list_filter = ['status', 'date']
    search_fields = ['student__admission_number', 'student__first_name', 'student__last_name', 'remarks']
    date_hierarchy = 'date'


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_pinned', 'created_at']
    list_filter = ['category', 'is_pinned', 'created_at']
    search_fields = ['title', 'message']
    date_hierarchy = 'created_at'


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['student', 'parent_name', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['student__admission_number', 'parent_name', 'subject', 'message']
    date_hierarchy = 'created_at'


@admin.register(ComplaintThread)
class ComplaintThreadAdmin(admin.ModelAdmin):
    list_display = ['complaint', 'sender_type', 'timestamp']
    list_filter = ['sender_type', 'timestamp']
    search_fields = ['complaint__subject', 'message']
    date_hierarchy = 'timestamp'
