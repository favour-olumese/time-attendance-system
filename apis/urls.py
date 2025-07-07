from django.urls import path
from . import views

urlpatterns = [
    path('enroll/student/', views.enroll_student, name='enroll-student'),
    path('enroll/lecturer/', views.enroll_lecturer, name='enroll-lecturer'),
    path('enroll/next_slot/', views.get_next_free_slot, name='get-next-slot'),
    path('check_matric/<str:matric_number>/', views.check_matric_enrolled, name='check-matric'),
    path('check_email/<str:email>/', views.check_lecturer_email_enrolled, name='check-email'),
]
