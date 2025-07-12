from django.db import models
from django.core.exceptions import ValidationError
from smart_selects.db_fields import ChainedForeignKey # For linking two fields

LEVEL_CHOICES = [(str(lvl), f"{lvl} Level") for lvl in range(100, 700, 100)]


class Faculty(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Faculties"

    def __str__(self):
            return f"{self.name}"

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.faculty})"
    

class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20, unique=True)
    departments = models.ManyToManyField('Department', related_name='courses')
    minimum_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    lecturers = models.ManyToManyField(
        'User',
        limit_choices_to={'user_role': 'Lecturer'},
        related_name='assigned_courses',
        blank=True
    )

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


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
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, null=True, blank=True)  # For students only
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    department = ChainedForeignKey(
        Department,
        chained_field="faculty",
        chained_model_field="faculty",
        show_all=False,
        auto_choose=True,
        sort=True,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
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
    course_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20, unique=True)  # For validation
    // Make a course accessible to a student based on department and minimum level
    // Courses should be assigned to lecturers on the backend

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