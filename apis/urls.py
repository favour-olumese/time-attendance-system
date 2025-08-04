from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='login'),
    path('enroll/student/', views.enroll_student_fingerprint, name='enroll-student-fingerprint'),
    path('enroll/lecturer/', views.enroll_lecturer_fingerprint, name='enroll-lecturer-fingerprint'),

    # ONLY STUDENTS
    path('course/enroll/', views.enroll_in_course, name='enroll-course'),
    
    # ONLY LECTURERS
    path('attendance/mark/', views.mark_attendance, name='api-mark-attendance'),
    path('attendance/my-courses/', views.lecturer_course_list, name='lecturer_course_list'),
    path('attendance/course/<int:course_id>/', views.course_attendance_detail, name='course_attendance_detail'),
    path('attendance/course/<int:course_id>/download/', views.download_attendance_summary, name='download_attendance_summary'),

    # JSON GET
    path('enroll/next_slot/', views.get_next_free_slot, name='get-next-slot'),
    path('check_matric/<str:matric_number>/', views.check_matric_enrolled, name='check-matric'),
    path('check_email/<str:email>/', views.check_lecturer_email_enrolled, name='check-email'),

    # JSON POST
    path('session/start/', views.start_session, name='api-start-session'),
    path('session/end/', views.end_session, name='api-end-session'),
]
