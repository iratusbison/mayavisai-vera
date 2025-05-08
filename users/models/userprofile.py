from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_restricted = models.BooleanField(default=False)
    is_restricted_gym = models.BooleanField(default=False)
    #member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='user_profile_members', null=True)
    phone = models.BigIntegerField(null=True)
    #aadhar = models.BigIntegerField(null=True)
    email = models.EmailField(null=True)
    #bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=500, blank=True)
    #birth_date = models.DateField(null=True, blank=True)
    is_frozen = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username



