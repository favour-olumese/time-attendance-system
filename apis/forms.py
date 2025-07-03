from django import forms
from .models import User

class StudentEnrollmentForm(forms.Form):
    matric_number = forms.CharField(label="Enter Matric Number")


class LecturerEnrollmentForm(forms.Form):
    email = forms.EmailField(label="Enter your work email address")