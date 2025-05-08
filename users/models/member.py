from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from PIL import Image, ExifTags
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.core.exceptions import ValidationError
from .userprofile import UserProfile
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import PermissionDenied

class Member(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='members', null=True)
    name = models.CharField(max_length=100)
    reg_no = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    GENDERS = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    gender = models.CharField(max_length=20, choices=GENDERS, null=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20)
    emergency_number = models.CharField(max_length=20, null=True)
    registration_date = models.DateField(auto_now_add=True)
    DOB = models.DateField(null=True)
    address = models.CharField(max_length=250, null=True)
    password = models.CharField(max_length=100, null=True)

    unique_number = models.PositiveIntegerField(null=True)
    image = models.ImageField(upload_to='pic/', null=True, blank=True)
    weight = models.CharField(max_length=30,null=True,blank=True)
    height= models.CharField(max_length=30,null=True,blank=True)
    exercise_history = models.CharField(max_length=300,null=True,blank=True)
    medications = models.CharField(max_length=500, null=True, blank=True)
    surgeries = models.CharField(max_length=400, blank=True, null=True)

    heart_disease = models.CharField(max_length=500, blank=True, null=True)
    medical_history = models.CharField(max_length=250, null=True)
    allergies = models.CharField(max_length=300, blank=True,null=True,default=None)
    blood_pressure = models.CharField(max_length=100, choices=[
        ('low', 'Low'),
        ('high', 'High'),
        ('normal', 'Normal')
    ], blank=True, null=True)
    diabetes = models.CharField(max_length=100, choices=[
        ('low', 'Low'),
        ('high', 'High'),
        ('normal', 'Normal')
    ], blank=True, null=True)
    arthritis = models.CharField(max_length=100, choices=[
        ('no','No'),
        ('ligament_injuries','Ligament_Injuries'),
        ('muscle_injuries','Muscle_Injuries'),
        ('tendon_injuries','Tendon_Injuries'),

    ],null=True, blank=True)

    archived = models.BooleanField(default=False)
    personal_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.unique_number} - {self.name}"






    def save(self, *args, **kwargs):
    # Check if the user is restricted
     if self.user_profile and self.user_profile.is_restricted_gym:
        raise PermissionDenied("This profile is restricted from creating or modifying data.")

    # Assign the unique number if it's not already set
     if not self.unique_number:
        last_member = Member.objects.filter(user_profile=self.user_profile).order_by('-unique_number').first()
        if last_member and last_member.unique_number is not None:
            self.unique_number = last_member.unique_number + 1
        else:
            self.unique_number = 1


    # Assign reg_no if it's not manually set
     if not self.reg_no:
        last_reg_no = Member.objects.aggregate(models.Max('reg_no'))['reg_no__max']
        self.reg_no = last_reg_no + 1 if last_reg_no else 1


       # Process the image if it exists
     if self.image:
        img = Image.open(self.image)
        exif = img._getexif()
        if exif:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif_orientation = exif.get(orientation)
            if exif_orientation == 3:
                img = img.rotate(180, expand=True)
            elif exif_orientation == 6:
                img = img.rotate(270, expand=True)
            elif exif_orientation == 8:
                img = img.rotate(90, expand=True)

        # Compress and resize the image
        img.thumbnail((200, 200))
        output = BytesIO()
        quality = 85
        while True:
            output.seek(0)
            img.save(output, format='JPEG', quality=quality)
            size_kb = output.tell() / 1024
            if size_kb <= 20 or quality <= 10:
                break
            quality -= 5

        output.seek(0)
        self.image = InMemoryUploadedFile(output, 'ImageField', f"{self.image.name.split('.')[0]}.jpg", 'image/jpeg', sys.getsizeof(output), None)

    # Check if the password needs hashing
     if not self.id or not check_password(self.password, self.password):
        self.password = make_password(self.password)

    # Now save the model with the compressed image
     super().save(*args, **kwargs)


'''
    # Handle archiving history
     if self.pk is not None:
        orig = Member.objects.get(pk=self.pk)
        if orig.archived != self.archived:
            if self.archived:
                ArchivedMemberHistory.objects.create(member=self, archived_by=self.user_profile.user)
            else:
                latest_entry = ArchivedMemberHistory.objects.filter(member=self).latest('archived_date')
                latest_entry.unarchived_by = self.user_profile.user
                latest_entry.unarchived_date = timezone.now()
                latest_entry.save()
'''
