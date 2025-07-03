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
    for i in range(1, 128):
        if i not in used:
            return i
    return None


def get_next_free_slot(request):
    slot = get_next_free_slot_value()
    if slot:
        return JsonResponse({"slot": slot})
    return JsonResponse({"error": "No available slots"}, status=400)


def enroll_student(request):
    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            slot = request.POST.get("slot_id")

            if not slot:
                return JsonResponse({"error": "Missing slot ID"}, status=400)

            # Save mapping assuming ESP32 enrollment already succeeded
            FingerprintMapping.objects.create(user=user, fingerprint_id=int(slot))
            return JsonResponse({"status": "success", "message": "Enrollment completed."})
    else:
        form = StudentEnrollmentForm()

    return render(request, 'enroll_form.html', {'form': form, 'role': 'Student'})


def enroll_lecturer(request):
    if request.method == 'POST':
        form = LecturerEnrollmentForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            slot = get_next_free_slot()
            # Call ESP32 and save, same as before
    else:
        form = LecturerEnrollmentForm()
    return render(request, 'enroll_form.html', {'form': form, 'role': 'Lecturer'})