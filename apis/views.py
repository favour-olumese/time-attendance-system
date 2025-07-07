from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FingerprintMapping, User
from .utils import get_next_available_slot_id
from .forms import StudentEnrollmentForm, LecturerEnrollmentForm
from django.shortcuts import render
from django.http import JsonResponse


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
        user = User.objects.get(MatricNumber=matric_number)
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
                user = User.objects.get(MatricNumber=matric_number)
                FingerprintMapping.objects.create(user=user, fingerprint_id=int(slot))
                return JsonResponse({"status": "success", "message": "Enrollment completed."})
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

    else:
        form = StudentEnrollmentForm()

    return render(request, 'enroll_form.html', {'form': form, 'role': 'Student'})


def check_lecturer_email_enrolled(request, email):
    try:
        user = User.objects.get(Email=email)
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
                user = User.objects.get(Email=email)
                FingerprintMapping.objects.create(user=user, fingerprint_id=int(slot))
                return JsonResponse({"status": "success", "message": "Enrollment completed."})
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

    else:
        form = LecturerEnrollmentForm()

    return render(request, 'enroll_form.html', {'form': form, 'role': 'Lecturer'})