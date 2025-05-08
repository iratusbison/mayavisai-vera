from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from .userprofile import UserProfile
from .member import Member

class Staff(models.Model):
    username = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    unique_number = models.PositiveIntegerField(null=True)
    is_active = models.BooleanField(default=True)
    is_restricted = models.BooleanField(default=False)
    is_restricted_gym = models.BooleanField(default=False)
    user_profiles = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='subaccounts', null=True)

    def save(self, *args, **kwargs):
        # Set staff restrictions based on the linked UserProfile's restrictions
        if self.user_profiles:
            self.is_restricted = self.user_profiles.is_restricted
            self.is_restricted_gym = self.user_profiles.is_restricted_gym

        # Set unique number based on user profile
        if not self.unique_number:
            last_member = Member.objects.filter(user_profile=self.user_profiles).order_by('-unique_number').first()
            if last_member:
                self.unique_number = last_member.unique_number + 1
            else:
                self.unique_number = 1

        # If the password is not already hashed, hash it
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)

        super(Staff, self).save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def get_members(self):
        # Retrieve all members related to the user profiles this staff is associated with
        return Member.objects.filter(user_profile__in=self.user_profiles.all())

    def __str__(self):
        return f"{self.username}"


from django.utils import timezone

class StaffAttendance(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time_in = models.TimeField(default=timezone.now)
    time_out = models.TimeField(null=True, blank=True)
    present = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff.username} - {self.date} - {self.time_in} - {self.time_out}"




