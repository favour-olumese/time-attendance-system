from django.db import models
from django.core.exceptions import ValidationError
from smart_selects.db_fields import ChainedForeignKey # For linking two fields
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import RegexValidator

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


class Semester(models.Model):
    SEMESTER_CHOICES = [
        ("First", "First Semester"),
        ("Second", "Second Semester"),
    ]

    name = models.CharField(max_length=10, choices=SEMESTER_CHOICES)

    session = models.CharField(
        max_length=9,  # "2024/2025" is 9 characters
        validators=[
            RegexValidator(
                regex=r'^\d{4}/\d{4}$',
                message="Session must be in the format 'YYYY/YYYY'."
            )
        ]
    )

    def __str__(self):
        return f"{self.name} Semester {self.session}"


class CurrentSemester(models.Model):
    semester = models.OneToOneField(Semester, on_delete=models.CASCADE)

    def __str__(self):
        return f"Current: {self.semester}"
   

class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20, unique=True)
    departments = models.ManyToManyField('Department', related_name='courses')
    minimum_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    available_semesters = models.ManyToManyField(Semester, related_name='offered_courses')
    lecturers = models.ManyToManyField(
        'User',
        limit_choices_to={'user_role': 'Lecturer'},
        related_name='assigned_courses',
        blank=True
    )

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class UserManager(BaseUserManager):
    """
    Creates a password automatically from the lowercase last–name
    if none is supplied.
    """

    def create_user(self, email, last_name=None, matric_number=None, password=None, **extra_fields):
        if not email and not matric_number:
            raise ValueError("A user must have either an email or matric number.")

        email = self.normalize_email(email)
        password = password or (last_name.lower() if last_name else 'default123')

        # Remove fields explicitly passed from extra_fields
        extra_fields.setdefault('matric_number', matric_number)
        extra_fields.setdefault('last_name', last_name)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Use Django's built-in hasher
        user.save(using=self._db)
        return user


    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_role", "Admin")  # User role of super users

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
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

    is_staff     = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)
    objects = UserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_role} - {self.department})"

    def save(self, *args, **kwargs):
        # Normalize email to lowercase
        if self.email:
            self.email = self.email.strip().lower()

        # Title case the names
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        if self.other_name:
            self.other_name = self.other_name.title()

        super().save(*args, **kwargs)

    @property
    def get_full_name(self):
        """Returns the user's full name."""
        return f"{self.first_name} {self.last_name}"

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


class CourseEnrollment(models.Model):
    enrolmentID = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("student", "course", "semester")

    def __str__(self):
        return f"{self.student} - {self.course} ({self.semester if self.semester_id else 'No semester'})"


class AttendanceSession(models.Model):
    """
    Represents a single, live attendance session for a class.
    Created when a lecturer starts a class, and closed when they end it.
    """
    session_id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Lecturer'})
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    
    # Timestamps to track the session duration
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True) # Set when lecturer ends the session

    # A flag to know if students can currently mark their attendance
    is_active = models.BooleanField(default=True)

    def __str__(self):
        status = "Active" if self.is_active else "Ended"
        return f"Session for {self.course.course_code} on {self.start_time.strftime('%Y-%m-%d')} ({status})"


class AttendanceRecord(models.Model):
    """
    A record of a single student's attendance in a specific session.
    """
    record_id = models.AutoField(primary_key=True)
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="attendees")
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_role': 'Student'})
    
    # Timestamp of when the student's fingerprint was scanned
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Field for the "mark accrued" as mentioned in your requirements
    marks_awarded = models.PositiveSmallIntegerField(default=1, help_text="Marks awarded for this attendance.")

    class Meta:
        # A student can only have one attendance record per session
        unique_together = ("session", "student")

    def __str__(self):
        return f"{self.student} attended session {self.session.session_id}"
"""
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