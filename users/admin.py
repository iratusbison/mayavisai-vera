from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.crypto import get_random_string
from .models.userprofile import UserProfile
from .models.viber import Viber
from .models.member import Member
from .models.attendance import Attendance
from .models.payment import Payment
from .models.staff import Staff, StaffAttendance
from .models.booking import Room, Booking
from django import forms
from django.contrib.auth.hashers import make_password

class SubAccountAdminForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = '__all__'

    def save(self, commit=True):
        instance = super(SubAccountAdminForm, self).save(commit=False)
        if instance.password and not instance.password.startswith('pbkdf2_'):
            instance.password = make_password(instance.password)
        if commit:
            instance.save()
        return instance

class SubAccountAdmin(admin.ModelAdmin):
    form = SubAccountAdminForm

admin.site.register(Staff, SubAccountAdmin)
admin.site.register(StaffAttendance)
admin.site.register(UserProfile)
#admin.site.register(Viber)
admin.site.register(Member)
admin.site.register(Attendance)
admin.site.register(Payment)
#admin.site.register(Staff)
admin.site.register(Room)
admin.site.register(Booking)

# Defining the reset_password action
def reset_password(modeladmin, request, queryset):
    for user in queryset:
        new_password = get_random_string(8)  # Generate a new random password
        user.set_password(new_password)
        user.save()
        modeladmin.message_user(request, f"Password for {user.username} has been reset to: {new_password}")

reset_password.short_description = "Reset password for selected users"

# Customizing the UserAdmin class to include the reset_password action
class UserAdmin(BaseUserAdmin):
    actions = [reset_password]

# Unregistering the original User admin and registering the customized one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
