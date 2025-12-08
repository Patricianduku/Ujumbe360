from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import Student

User = get_user_model()


class AdmissionNumberBackend(ModelBackend):
    """
    Custom authentication backend:
    - Staff: username + password (standard)
    - Parents: student's admission_number as username AND parent_phone as password
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Staff or existing users: normal check
        if username and password:
            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                # fall through to parent admission login
                pass

        # Parent flow: username is admission_number, password is parent phone
        if username and password:
            try:
                student = Student.objects.get(admission_number=username, parent_phone=password)
            except Student.DoesNotExist:
                return None

            parent_username = student.admission_number  # keep username equal to admission number
            user, created = User.objects.get_or_create(
                username=parent_username,
                defaults={
                    "email": f"{parent_username}@ujumbe360.local",
                    "first_name": student.parent_name.split()[0] if student.parent_name else "",
                    "last_name": " ".join(student.parent_name.split()[1:]) if len(student.parent_name.split()) > 1 else "",
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            # Always sync password to parent phone so updated phone works
            user.set_password(student.parent_phone)
            user.is_staff = False
            user.is_superuser = False
            user.save()

            # Store admission number for scoping
            if request:
                request.session["student_admission_number"] = student.admission_number

            return user

        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

