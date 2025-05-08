from django.db import models
from django.contrib.auth.models import User
from datetime import date
from django.utils import timezone
from datetime import timedelta
from PIL import Image, ExifTags
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.core.exceptions import ValidationError


class Viber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    is_frozen = models.BooleanField(default=False)
    GENDERS = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    gender = models.CharField(max_length=20, choices=GENDERS, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    registration_date = models.DateField(auto_now_add=True)
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


    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if not self.unique_number:
            last_viber = Viber.objects.order_by('-unique_number').first()
            if last_viber:
                self.unique_number = last_viber.unique_number + 1
            else:
                self.unique_number = 1

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

        super(Viber, self).save(*args, **kwargs)

    def calculate_age(self):
        if self.birth_date:
            today = date.today()
            age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            return age
        return None

    def calculate_bmr(self):
        age = self.calculate_age()
        if not age:
            return None

        weight_kg = float(self.weight) if self.weight else None
        height_cm = float(self.height) if self.height else None

        if weight_kg and height_cm:
            if self.gender == 'male':
                return 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
            elif self.gender == 'female':
                return 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
        return None

    def calculate_tdee(self, activity_level):
        bmr = self.calculate_bmr()
        if not bmr:
            return None

        activity_multipliers = {
            'sedentary': 1.2,
            'lightly_active': 1.375,
            'moderately_active': 1.55,
            'very_active': 1.725,
            'super_active': 1.9,
        }

        multiplier = activity_multipliers.get(activity_level, 1.2)
        return bmr * multiplier

    def calculate_all_tdees(self):
        activity_levels = {
            'Sedentary': 1.2,
            'Lightly Active': 1.375,
            'Moderately Active': 1.55,
            'Very Active': 1.725,
            'Super Active': 1.9,
        }
        bmr = self.calculate_bmr()
        tdees = {}
        if bmr:
            for level, multiplier in activity_levels.items():
                tdees[level] = bmr * multiplier

                # Calculate macronutrients
                tdee = tdees[level]
                carbs = tdee * 0.50 / 4  # 50% of calories from carbs (4 calories per gram)
                protein = tdee * 0.20 / 4  # 20% of calories from protein (4 calories per gram)
                fat = tdee * 0.30 / 9  # 30% of calories from fat (9 calories per gram)

                tdees[level] = {
                    'calories': tdee,
                    'carbs_grams': carbs,
                    'protein_grams': protein,
                    'fat_grams': fat
                }

        return tdees

    def calculate_water_needs(self):
        # A simple guideline is to drink 30-35 ml of water per kg of body weight
        weight_kg = float(self.weight) if self.weight else None
        if weight_kg:
            return weight_kg * 30  # Water needs in ml
        return None

    def calculate_macros_and_water(self):
        tdees = self.calculate_all_tdees()
        water_needs = self.calculate_water_needs()
        results = {'tdees': tdees, 'water_needs_ml': water_needs}
        return results
'''
    def calculate_tdee(self, activity_level):
        bmr = self.calculate_bmr()
        if not bmr:
            return None

        activity_multipliers = {
            'sedentary': 1.2,
            'lightly_active': 1.375,
            'moderately_active': 1.55,
            'very_active': 1.725,
            'super_active': 1.9,
        }

        multiplier = activity_multipliers.get(activity_level, 1.2)  # Default to sedentary if unknown activity level
        return bmr * multiplier

    def calculate_all_tdees(self):
        activity_levels = {
            'Sedentary': 1.2,
            'Lightly Active': 1.375,
            'Moderately Active': 1.55,
            'Very Active': 1.725,
            'Super Active': 1.9,
        }
        bmr = self.calculate_bmr()
        tdees = {}
        if bmr:
            for level, multiplier in activity_levels.items():
                tdees[level] = bmr * multiplier
        return tdees
'''