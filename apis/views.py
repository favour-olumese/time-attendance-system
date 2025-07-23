from .models import FingerprintMapping, User, CurrentSemester, CourseEnrollment
from django.contrib.auth import authenticate, login
from .forms import StudentEnrollmentForm, LecturerEnrollmentForm, CourseEnrollmentForm
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from .models import CourseEnrollment, CurrentSemester
from .forms import CourseEnrollmentForm
from django.contrib.auth.decorators import login_required

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