from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# ============================================================
# 1. STUDENT MANAGEMENT MODULE
# ============================================================
class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    admission_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=20)
    class_level = models.CharField(max_length=50)  # e.g., "Form 1", "Form 2", "Grade 1"
    stream = models.CharField(max_length=50, blank=True)  # e.g., "A", "B", "East"
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['class_level', 'stream', 'first_name', 'last_name']
    
    def __str__(self):
        return f"{self.admission_number} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


# ============================================================
# 2. FEES MODULE
# ============================================================
class FeeStructure(models.Model):
    class_level = models.CharField(max_length=50)
    amount_required = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['class_level']
        ordering = ['class_level']
    
    def __str__(self):
        return f"{self.class_level} - KSh {self.amount_required}"


class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateField()
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.student.admission_number} - KSh {self.amount_paid} on {self.date}"


# ============================================================
# 3. ACADEMIC / GRADES MODULE
# ============================================================
class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Exam(models.Model):
    name = models.CharField(max_length=100)
    term = models.CharField(max_length=50)  # e.g., "Term 1", "Term 2", "Term 3"
    year = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-year', 'term', 'name']
        unique_together = ['name', 'term', 'year']
    
    def __str__(self):
        return f"{self.name} - {self.term} {self.year}"


class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='grades')
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_letter = models.CharField(max_length=2, blank=True)  # A, A-, B+, B, etc.
    teacher_comment = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'subject', 'exam']
        ordering = ['exam', 'subject', 'student']
    
    def __str__(self):
        return f"{self.student.admission_number} - {self.subject.name} - {self.score}%"
    
    def save(self, *args, **kwargs):
        # Auto-calculate grade letter based on score
        if self.score is not None:
            score = float(self.score)
            if score >= 80:
                self.grade_letter = 'A'
            elif score >= 75:
                self.grade_letter = 'A-'
            elif score >= 70:
                self.grade_letter = 'B+'
            elif score >= 65:
                self.grade_letter = 'B'
            elif score >= 60:
                self.grade_letter = 'B-'
            elif score >= 55:
                self.grade_letter = 'C+'
            elif score >= 50:
                self.grade_letter = 'C'
            elif score >= 45:
                self.grade_letter = 'C-'
            elif score >= 40:
                self.grade_letter = 'D+'
            elif score >= 35:
                self.grade_letter = 'D'
            else:
                self.grade_letter = 'E'
        super().save(*args, **kwargs)


# ============================================================
# Attendance
# ============================================================
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Excused', 'Excused'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date', 'student']

    def __str__(self):
        return f"{self.student.admission_number} - {self.date} - {self.status}"


# ============================================================
# 4. ANNOUNCEMENT SYSTEM
# ============================================================
class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('General', 'General'),
        ('Academic', 'Academic'),
        ('Fees', 'Fees'),
        ('Events', 'Events'),
        ('Urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        return self.title


# ============================================================
# 5. COMPLAINTS MODULE
# ============================================================
class Complaint(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Review', 'In Review'),
        ('Resolved', 'Resolved'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='complaints')
    parent_name = models.CharField(max_length=100 , blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.admission_number} - {self.subject} ({self.status})"


class ComplaintThread(models.Model):
    SENDER_TYPE_CHOICES = [
        ('Parent', 'Parent'),
        ('Admin', 'Admin'),
    ]
    
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='threads')
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.complaint.subject} - {self.sender_type} - {self.timestamp}"
