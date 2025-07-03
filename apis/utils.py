from .models import FingerprintMapping

def get_next_available_slot_id(max_slots=1000):
    used_ids = set(FingerprintMapping.objects.values_list('fingerprint_id', flat=True))
    for i in range(max_slots):
        if i not in used_ids:
            return i
    raise Exception("No available fingerprint slots.")
