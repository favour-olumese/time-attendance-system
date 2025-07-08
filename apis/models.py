from django.db import models

# User Roles
from django.core.exceptions import ValidationError

class User(models.Model):
    """
    The User Model for students and lecturers.
    """
    
    USER_ROLES = (
        ('Student', 'Student'),
        ('Lecturer', 'Lecturer'),
    )

    user_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    other_name = models.CharField(max_length=50, blank=True, null=True)
    matric_number = models.CharField(max_length=20, unique=True, blank=True, null=True)  # For students only
    email = models.EmailField(unique=True)
    level = models.CharField(max_length=20, blank=True, null=True)  # For students only
    department = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    user_role = models.CharField(max_length=10, choices=USER_ROLES)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_role})"

    def clean(self):
        """
        This ensures the matric numbers and level is mandatory for students,
        but is not allowed for lecturers.
        """

        # Conditional validation for Student
        if self.user_role == 'Student':
            if not self.matric_number:
                raise ValidationError({'matric_number': "Matric Number is required for students."})
            if not self.level:
                raise ValidationError({'level': "Level is required for students."})
            
        # Prevent matric_number or level for Lecturers
        elif self.user_role == 'Lecturer':
            if self.matric_number:
                raise ValidationError({'matric_number': "Lecturers should not have Matric Numbers."})
            if self.level:
                raise ValidationError({'level': "Lecturers should not have a Level."})


class FingerprintMapping(models.Model):
    """
    Maps fingerprints to users.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fingerprint_id = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.user} → Slot {self.fingerprint_id}"


"""
class Course(models.Model):
    CourseID = models.AutoField(primary_key=True)
    CourseName = models.CharField(max_length=100)
    CourseCode = models.CharField(max_length=20, unique=True)  # For validation

    def __str__(self):
        return self.CourseName

class Enrollment(models.Model):
    EnrolmentID = models.AutoField(primary_key=True)
    Student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Student'})
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Semester = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.Student} enrolled in {self.Course}"

class ClassSession(models.Model):
    ClassSessionID = models.AutoField(primary_key=True)
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Lecturer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Lecturer'})
    SessionDateTime = models.DateTimeField(default=timezone.now)
    IsActive = models.BooleanField(default=False)
    SessionEndTime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.Course.CourseName} by {self.Lecturer} on {self.SessionDateTime}"

class AttendanceLog(models.Model):
    LogID = models.AutoField(primary_key=True)
    ClassSession = models.ForeignKey(ClassSession, on_delete=models.CASCADE)
    Student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Student'})
    ScanTimestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Student} attended {self.ClassSession}"

class AttendanceScore(models.Model):
    ScoreID = models.AutoField(primary_key=True)
    Student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Student'})
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Semester = models.CharField(max_length=20)
    CalculatedScore = models.FloatField(default=0)

    def __str__(self):
        return f"{self.Student}: {self.CalculatedScore} in {self.Course}"
"""