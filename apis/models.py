from django.db import models
from django.utils import timezone

# User Roles
from django.core.exceptions import ValidationError

class User(models.Model):
    USER_ROLES = (
        ('Student', 'Student'),
        ('Lecturer', 'Lecturer'),
    )

    UserID = models.AutoField(primary_key=True)
    FirstName = models.CharField(max_length=50)
    LastName = models.CharField(max_length=50)
    OtherName = models.CharField(max_length=50, blank=True, null=True)
    MatricNumber = models.CharField(max_length=20, unique=True, blank=True, null=True)  # For students only
    Email = models.EmailField(unique=True)
    Level = models.CharField(max_length=20, blank=True, null=True)  # For students only
    Department = models.CharField(max_length=100)
    Faculty = models.CharField(max_length=100)
    User_Role = models.CharField(max_length=10, choices=USER_ROLES)

    def __str__(self):
        return f"{self.FirstName} {self.LastName} ({self.User_Role})"

    def clean(self):
        # Conditional validation for Student
        if self.User_Role == 'Student':
            if not self.MatricNumber:
                raise ValidationError({'MatricNumber': "Matric Number is required for students."})
            if not self.Level:
                raise ValidationError({'Level': "Level is required for students."})
            
        # Prevent MatricNumber or Level for Lecturers
        elif self.User_Role == 'Lecturer':
            if self.MatricNumber:
                raise ValidationError({'MatricNumber': "Lecturers should not have Matric Numbers."})
            if self.Level:
                raise ValidationError({'Level': "Lecturers should not have a Level."})


class FingerprintMapping(models.Model):
    matric_number = models.CharField(max_length=20, unique=True)
    fingerprint_id = models.IntegerField(unique=True)  # R307 slot ID (0–1000)

    def __str__(self):
        return f"{self.matric_number} → Slot {self.fingerprint_id}"

    def get_user(self):
        return User.objects.get(MatricNumber=self.matric_number)


"""
class Course(models.Model):
    CourseID = models.AutoField(primary_key=True)
    CourseName = models.CharField(max_length=100)
    CourseCode = models.CharField(max_length=20, unique=True)  # For validation

    def __str__(self):
        return self.CourseName

class Enrollment(models.Model):
    EnrolmentID = models.AutoField(primary_key=True)
    Student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'User_Role': 'Student'})
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Semester = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.Student} enrolled in {self.Course}"

class ClassSession(models.Model):
    ClassSessionID = models.AutoField(primary_key=True)
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Lecturer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'User_Role': 'Lecturer'})
    SessionDateTime = models.DateTimeField(default=timezone.now)
    IsActive = models.BooleanField(default=False)
    SessionEndTime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.Course.CourseName} by {self.Lecturer} on {self.SessionDateTime}"

class AttendanceLog(models.Model):
    LogID = models.AutoField(primary_key=True)
    ClassSession = models.ForeignKey(ClassSession, on_delete=models.CASCADE)
    Student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'User_Role': 'Student'})
    ScanTimestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Student} attended {self.ClassSession}"

class AttendanceScore(models.Model):
    ScoreID = models.AutoField(primary_key=True)
    Student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'User_Role': 'Student'})
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    Semester = models.CharField(max_length=20)
    CalculatedScore = models.FloatField(default=0)

    def __str__(self):
        return f"{self.Student}: {self.CalculatedScore} in {self.Course}"
"""