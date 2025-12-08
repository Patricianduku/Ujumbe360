from django import forms
from .models import (
    Student, FeeStructure, Payment, Subject, Exam, Grade, Attendance,
    Announcement, Complaint, ComplaintThread
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Row, Column

# ============================================================
# 1. STUDENT MANAGEMENT FORMS
# ============================================================
class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'admission_number', 'first_name', 'last_name', 'gender',
            'date_of_birth', 'parent_name', 'parent_phone',
            'class_level', 'stream'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('admission_number', css_class='form-group col-md-6 mb-3'),
                Column('first_name', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('last_name', css_class='form-group col-md-6 mb-3'),
                Column('gender', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('date_of_birth', css_class='form-group col-md-6 mb-3'),
                Column('parent_name', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('parent_phone', css_class='form-group col-md-6 mb-3'),
                Column('class_level', css_class='form-group col-md-6 mb-3'),
            ),
            'stream',
        )
        self.helper.add_input(Submit('submit', 'Save Student', css_class='btn btn-primary'))


# ============================================================
# 2. FEES MODULE FORMS
# ============================================================
class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['class_level', 'amount_required']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Fee Structure', css_class='btn btn-primary'))


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['student', 'amount_paid', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Add Payment', css_class='btn btn-primary'))


# ============================================================
# 3. ACADEMIC / GRADES MODULE FORMS
# ============================================================
class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Subject', css_class='btn btn-primary'))


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'term', 'year']
        widgets = {
            'year': forms.NumberInput(attrs={'min': 2020, 'max': 2100}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Exam', css_class='btn btn-primary'))


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'subject', 'exam', 'score', 'teacher_comment']
        widgets = {
            'score': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 0.01}),
            'teacher_comment': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'student',
            Row(
                Column('subject', css_class='form-group col-md-6 mb-3'),
                Column('exam', css_class='form-group col-md-6 mb-3'),
            ),
            'score',
            'teacher_comment',
        )
        self.helper.add_input(Submit('submit', 'Save Grade', css_class='btn btn-primary'))


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'date', 'status', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Attendance', css_class='btn btn-primary'))


# ============================================================
# 4. ANNOUNCEMENT SYSTEM FORMS
# ============================================================
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'message', 'category', 'is_pinned']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Announcement', css_class='btn btn-primary'))


# ============================================================
# 5. COMPLAINTS MODULE FORMS
# ============================================================
class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['student', 'parent_name', 'subject', 'message', 'status']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        is_parent = kwargs.pop('is_parent', False)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        # Parents can't change status
        if is_parent:
            self.fields.pop('status', None)
        
        self.helper.add_input(Submit('submit', 'Submit Complaint', css_class='btn btn-primary'))


class ComplaintThreadForm(forms.ModelForm):
    class Meta:
        model = ComplaintThread
        fields = ['message', 'sender_type']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        sender_type = kwargs.pop('sender_type', 'Admin')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        # Set sender type based on user
        if sender_type:
            self.fields['sender_type'].initial = sender_type
            self.fields['sender_type'].widget = forms.HiddenInput()
        
        self.helper.add_input(Submit('submit', 'Send Reply', css_class='btn btn-primary'))
