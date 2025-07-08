from django import forms
from django.contrib import admin
from .models import User, FingerprintMapping
# Register your models here.

# admin.site.register(User)
admin.site.register(FingerprintMapping)


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [ # Reordered the display of user form fields
            'user_role',
            'first_name',
            'last_name',
            'other_name',
            'email',
            'matric_number',
            'level',
            'department',
            'faculty',
            ]

    class Media:
        js = ('admin/js/user_form.js',)  # Reference custom JS


class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm

admin.site.register(User, UserAdmin)