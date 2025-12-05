from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Student, Parent, Fee, Exam, Grade, Announcement, Complaint

admin.site.register(Student)
admin.site.register(Parent)
admin.site.register(Fee)
admin.site.register(Exam)
admin.site.register(Grade)
admin.site.register(Announcement)
admin.site.register(Complaint)
