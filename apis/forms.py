from django import forms
from .models import User

class StudentEnrollmentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(User_Role='Student'),
        label="Select Student (by Matric Number)",
        to_field_name='MatricNumber'
    )

class LecturerEnrollmentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(User_Role='Lecturer'),
        label="Select Lecturer (by Email)",
        to_field_name='Email'
    )