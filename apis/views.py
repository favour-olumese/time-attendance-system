import csv
import json
from .models import FingerprintMapping, User, CurrentSemester, CourseEnrollment, Course, AttendanceSession, AttendanceRecord
from django.contrib.auth import authenticate, login
from .forms import StudentEnrollmentForm, LecturerEnrollmentForm, CourseEnrollmentForm
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q # Import Count and Q for annotations
from django.http import HttpResponse

def get_next_free_slot_value():
    used = FingerprintMapping.objects.values_list('fingerprint_id', flat=True)
    for i in range(1, 1001):
        if i not in used:
            return i
    return None


def get_next_free_slot(request):
    slot = get_next_free_slot_value()
    if slot:
        return JsonResponse({"slot": slot})
    return JsonResponse({"error": "No available slots"}, status=400)


def check_matric_enrolled(request, matric_number):
    try:
        user = User.objects.get(matric_number=matric_number)
        fingerprint_exists = FingerprintMapping.objects.filter(user=user).exists()
        return JsonResponse({"fingerprint_exists": fingerprint_exists, "user_exists": True})
    except User.DoesNotExist:
        return JsonResponse({"fingerprint_exists": False, "user_exists": False})


def enroll_student(request):
    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST)
        if form.is_valid():
            matric_number = form.cleaned_data['matric_number']
            slot = request.POST.get("slot_id")

            if not slot:
                return JsonResponse({"error": "Missing slot ID"}, status=400)

            try:
                user = User.objects.get(matric_number=matric_number)
                FingerprintMapping.objects.create(user=user, fingerprint_id=int(slot))
                return JsonResponse({"status": "success", "message": "Enrollment completed."})
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

    else:
        form = StudentEnrollmentForm()

    return render(request, 'enroll_fingerprint.html', {'form': form, 'role': 'Student'})


def check_lecturer_email_enrolled(request, email):
    try:
        user = User.objects.get(email=email)
        fingerprint_exists = FingerprintMapping.objects.filter(user=user).exists()
        return JsonResponse({"fingerprint_exists": fingerprint_exists, "user_exists": True})
    except User.DoesNotExist:
        return JsonResponse({"fingerprint_exists": False, "user_exists": False})


def enroll_lecturer(request):
    if request.method == 'POST':
        form = LecturerEnrollmentForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            slot = request.POST.get("slot_id")

            if not slot:
                return JsonResponse({"error": "Missing slot ID"}, status=400)

            try:
                user = User.objects.get(email=email)
                FingerprintMapping.objects.create(user=user, fingerprint_id=int(slot))
                return JsonResponse({"status": "success", "message": "Enrollment completed."})
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

    else:
        form = LecturerEnrollmentForm()

    return render(request, 'enroll_fingerprint.html', {'form': form, 'role': 'Lecturer'})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')  # email or matric_number
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}")
            return redirect('dashboard')  # or any success page
        else:
            messages.error(request, "Invalid login credentials.")
    
    return render(request, 'registration/login.html')


def dashboard(request):
    return render(request, 'dashboard.html')


@login_required 
def enroll_in_course(request):
    if request.user.user_role != 'Student':
        messages.error(request, "Only students can enroll in courses.")
        return redirect('dashboard')

    # Get current semester once
    try:
        current_semester = CurrentSemester.objects.select_related('semester').first().semester
    except (CurrentSemester.DoesNotExist, AttributeError):
        messages.error(request, "Current semester is not set. Please contact admin.")
        return redirect('dashboard')

    if request.method == "POST":
        # Pass the user to the form
        form = CourseEnrollmentForm(request.POST, user=request.user)
        if form.is_valid():
            # All validation is done, we can now create the object
            enrollment = form.save(commit=False)
            enrollment.student = request.user
            enrollment.semester = current_semester
            enrollment.save()

            messages.success(request, f"Successfully enrolled in {enrollment.course.course_code}!")
            return redirect('enroll-course')
        else:
            # Form errors will be displayed automatically by the template
            # We can add a generic error message if we want
            messages.error(request, "Please correct the errors below.")
    else:
        # Pass the user to the form for the initial GET request as well
        form = CourseEnrollmentForm(user=request.user)

    # Get already enrolled courses to display on the page
    enrolled_courses = CourseEnrollment.objects.filter(
        student=request.user, 
        semester=current_semester
    ).select_related('course')

    return render(request, 'enroll_course.html', {
        'form': form,
        'enrolled_courses': enrolled_courses
    })


@csrf_exempt # Disable CSRF for API requests from the scanner
def start_session(request):
    """
    API Endpoint to start an attendance session.
    Expected POST data: {"fingerprint_id": 123, "course_code": "CSC101"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        course_code = data.get('course_code')

        if not fingerprint_id or not course_code:
            return JsonResponse({'error': 'fingerprint_id and course_code are required.'}, status=400)

        # 1. Identify the user and verify they are a lecturer
        lecturer = User.objects.get(fingerprintmapping__fingerprint_id=fingerprint_id, user_role='Lecturer')

        # 2. Check if the lecturer is already running a session
        if AttendanceSession.objects.filter(lecturer=lecturer, is_active=True).exists():
            return JsonResponse({'error': 'You already have an active session. Please end it first.'}, status=409)

        # 3. Validate that the course exists and is assigned to this lecturer
        course = lecturer.assigned_courses.get(course_code__iexact=course_code)

        # 4. Get the current semester
        current = CurrentSemester.objects.select_related('semester').first()
        if not current or not current.semester:
            return JsonResponse({'error': 'System error: Current semester is not set.'}, status=500)

        # 5. Create and save the new attendance session
        session = AttendanceSession.objects.create(
            course=course,
            lecturer=lecturer,
            semester=current.semester,
            is_active=True
        )

        return JsonResponse({
            'message': 'Attendance session started successfully!',
            'session_id': session.session_id,
            'course': course.course_name,
            'lecturer': str(lecturer)
        }, status=201)

    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid fingerprint or user is not a lecturer.'}, status=403)
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Invalid course code or you are not assigned to this course.'}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@csrf_exempt
def mark_attendance(request):
    """
    API Endpoint for a student to mark attendance.
    Expected POST data: {"fingerprint_id": 456, "course_code": "CSC101"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        course_code = data.get('course_code')

        if not fingerprint_id or not course_code:
            return JsonResponse({'error': 'fingerprint_id and course_code are required.'}, status=400)

        # 1. Find the currently active session for the given course
        active_session = AttendanceSession.objects.get(course__course_code__iexact=course_code, is_active=True)
        
        # 2. Identify the student
        student = User.objects.get(fingerprintmapping__fingerprint_id=fingerprint_id, user_role='Student')
        
        # 3. Verify the student is enrolled in this course for the current semester
        is_enrolled = CourseEnrollment.objects.filter(
            student=student, 
            course=active_session.course,
            semester=active_session.semester
        ).exists()

        if not is_enrolled:
            return JsonResponse({'error': f'Access Denied: You are not enrolled in {active_session.course.course_code}.'}, status=403)

        # 4. Create the attendance record. get_or_create prevents duplicates.
        record, created = AttendanceRecord.objects.get_or_create(
            session=active_session,
            student=student
        )

        if created:
            return JsonResponse({
                'message': 'Attendance marked successfully!',
                'student': str(student),
                'course': active_session.course.course_code,
                'time': record.timestamp.strftime('%H:%M:%S')
            }, status=201)
        else:
            return JsonResponse({'message': 'You have already marked your attendance for this session.'}, status=200)

    except AttendanceSession.DoesNotExist:
        return JsonResponse({'error': 'No active attendance session found for this course or session has ended.'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid fingerprint or user is not a student.'}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@csrf_exempt
def end_session(request):
    """
    API Endpoint to end an attendance session.
    Expected POST data: {"fingerprint_id": 123}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')

        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required.'}, status=400)

        # 1. Identify the lecturer
        lecturer = User.objects.get(fingerprintmapping__fingerprint_id=fingerprint_id, user_role='Lecturer')

        # 2. Find the session they started that is currently active
        session_to_end = AttendanceSession.objects.get(lecturer=lecturer, is_active=True)

        # 3. Close the session
        session_to_end.is_active = False
        session_to_end.end_time = timezone.now()
        session_to_end.save()

        # 4. Get total attendance count for feedback
        attendance_count = AttendanceRecord.objects.filter(session=session_to_end).count()

        return JsonResponse({
            'message': 'Session ended successfully.',
            'course': session_to_end.course.course_code,
            'total_students_marked': attendance_count
        }, status=200)

    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid fingerprint or user is not a lecturer.'}, status=403)
    except AttendanceSession.DoesNotExist:
        return JsonResponse({'error': 'You do not have an active session to end.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@login_required
def lecturer_course_list(request):
    """
    Displays a list of all courses assigned to the logged-in lecturer.
    """
    # Ensure the user is a lecturer
    if request.user.user_role != 'Lecturer':
        messages.error(request, "You do not have permission to view this page.")
        return redirect('dashboard')

    # Get all courses assigned to this lecturer
    courses = request.user.assigned_courses.all().order_by('course_code')

    context = {
        'courses': courses,
    }
    return render(request, 'attendance/lecturer_course_list.html', context)


@login_required
def course_attendance_detail(request, course_id):
    """
    Displays all attendance sessions and records for a specific course.
    """
    # Ensure the user is a lecturer
    if request.user.user_role != 'Lecturer':
        messages.error(request, "You do not have permission to view this page.")
        return redirect('dashboard')

    # Get the course, but also verify the logged-in lecturer is assigned to it.
    # get_object_or_404 is great will raise a 404 error if the course
    # doesn't exist OR if the current user is not in the 'lecturers' list for that course.
    course = get_object_or_404(Course, pk=course_id, lecturers=request.user)

    # GET DETAILED SESSION LOG

    # Get all attendance sessions for this course, newest first.
    # prefetch_related get all related attendance records
    # and student details in a minimal number of database queries. This avoids the N+1 problem.
    sessions = AttendanceSession.objects.filter(course=course).order_by('-start_time').prefetch_related('attendees__student')

    # CALCULATE ATTENDANCE SUMMARY

    # Get the total number of sessions held for this course.
    total_sessions_count = sessions.count()

    attendance_summary = []
    if total_sessions_count > 0:
        # Get all students enrolled in the course.
        # We use distinct() because a student might be enrolled via multiple departments sharing a course.
        enrolled_students = User.objects.filter(courseenrollment__course=course).distinct()

        # Annotate each student with the count of their attendance records for this specific course.
        # The filter inside Count() is crucial to ensure we only count attendance for this course.
        students_with_attendance = enrolled_students.annotate(
            attended_count=Count(
                'attendancerecord',
                filter=Q(attendancerecord__session__course=course)
            )
        )

        # Build the summary data list for the template
        for student in students_with_attendance:
            percentage = (student.attended_count / total_sessions_count) * 100
            attendance_summary.append({
                'student': student,
                'attended_count': student.attended_count,
                'percentage': percentage,
            })

    context = {
        'course': course,
        'sessions': sessions,
        'total_sessions_count': total_sessions_count,
        'attendance_summary': attendance_summary,
    }
    return render(request, 'attendance/course_attendance_detail.html', context)


@login_required
def download_attendance_summary(request, course_id):
    """
    Handles the logic to generate and download an attendance summary as a CSV file.
    """
    # Ensure the user is a lecturer assigned to this course.
    if request.user.user_role != 'Lecturer':
        messages.error(request, "Permission denied.")
        return redirect('dashboard')
    
    course = get_object_or_404(Course, pk=course_id, lecturers=request.user)

    # Data Calculation
    total_sessions_count = AttendanceSession.objects.filter(course=course).count()

    if total_sessions_count == 0:
        messages.error(request, "No attendance data to download for this course.")
        return redirect('course_attendance_detail', course_id=course.pk)

    enrolled_students = User.objects.filter(courseenrollment__course=course).distinct()
    students_with_attendance = enrolled_students.annotate(
        attended_count=Count('attendancerecord', filter=Q(attendancerecord__session__course=course))
    )

    # CSV Generation
    # Create the HttpResponse object with the appropriate CSV headers.
    response = HttpResponse(content_type='text/csv')
    # This header tells the browser to treat the response as a file attachment.
    response['Content-Disposition'] = f'attachment; filename="attendance_summary_{course.course_code}.csv"'

    writer = csv.writer(response)

    # Write the header row for the CSV file.
    writer.writerow(['Student Name', 'Matric Number', 'Classes Attended', 'Total Classes', 'Attendance Score (%)'])

    # Write data rows
    for student in students_with_attendance:
        percentage = (student.attended_count / total_sessions_count) * 100
        writer.writerow([
            student.get_full_name,
            student.matric_number,
            student.attended_count,
            total_sessions_count,
            f'{percentage:.1f}'  # Format percentage to one decimal place
        ])

    return response