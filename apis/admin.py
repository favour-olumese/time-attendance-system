from django import forms
from django.contrib import admin
from .models import User, FingerprintMapping, Course, Department, Faculty
# Register your models here.

# admin.site.register(User)
admin.site.register(FingerprintMapping)
admin.site.register(Course)
admin.site.register(Department)
admin.site.register(Faculty)


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
            'faculty',
            'department',
            ]

    class Media:
        js = ('admin/js/user_form.js',)  # Reference custom JS

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.pk is None:  # New user
            user.set_password(user.last_name)
        if commit:
            user.save()
        return user


class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    add_form = UserAdminForm

    model = User

    list_display = ('email', 'first_name', 'last_name', 'user_role', 'is_staff')
    list_filter = ('user_role', 'faculty', 'department', 'is_staff')
    ordering = ('email',)

    # Hide password fields from the admin form
    fieldsets = (
        (None, {
            'fields': ('user_role', 'first_name', 'last_name', 'other_name', 'email', 'matric_number', 'level', 'faculty', 'department', 'is_active', 'is_staff', 'is_superuser')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('user_role', 'first_name', 'last_name', 'other_name', 'email', 'matric_number', 'level', 'faculty', 'department'),
        }),
    )

    search_fields = ('email', 'matric_number', 'first_name', 'last_name')

admin.site.register(User, UserAdmin)