from django import forms
from .models import CourseEnrollment, Course, CurrentSemester

class StudentEnrollmentForm(forms.Form):
    matric_number = forms.CharField(label="Enter Matric Number")


class LecturerEnrollmentForm(forms.Form):
    email = forms.EmailField(label="Enter your work email address")


class CourseEnrollmentForm(forms.ModelForm):
    class Meta:
        model = CourseEnrollment
        fields = ['course']

    def __init__(self, *args, **kwargs):
        # We need the user to perform validation checks
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.user:
            # If no user is provided, we can't proceed
            self.fields['course'].queryset = Course.objects.none()
            return
            
        try:
            # Store current semester for use in the clean method
            self.current_semester = CurrentSemester.objects.select_related('semester').first().semester
            # Filter courses to only show those available this semester and for the student's department
            self.fields['course'].queryset = Course.objects.filter(
                available_semesters=self.current_semester,
                departments=self.user.department,
                minimum_level__lte=self.user.level
            ).distinct()
        except (CurrentSemester.DoesNotExist, AttributeError):
            self.current_semester = None
            self.fields['course'].queryset = Course.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        student = self.user
        semester = self.current_semester

        # Ensure all required data is present before validation
        if not (course and student and semester):
            # This will be caught by field-level validation, but it's a good safeguard
            raise forms.ValidationError("Could not validate the enrollment. Missing data.")

        # Check for duplicate enrollment
        if CourseEnrollment.objects.filter(student=student, course=course, semester=semester).exists():
            self.add_error('course', f"You are already enrolled in {course.course_code}.")

        # Check if student's level is sufficient
        if student.level and int(student.level) < int(course.minimum_level):
            self.add_error('course', 
                f"Your level ({student.level}) is not high enough for this course. "
                f"Minimum level required: {course.minimum_level}."
            )

        return cleaned_data