from django.db import models
from django.contrib.auth.models import User
from users.models.userprofile import UserProfile

class Room(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='rooms', null=True)
    room_number = models.CharField(max_length=50, null=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.room_number

    def save(self, *args, **kwargs):
        if self.user_profile and self.user_profile.is_restricted:
            raise PermissionError("This profile is restricted from creating or modifying rooms.")
        super(Room, self).save(*args, **kwargs)


class Booking(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='bookings', null=True)
    user_specific_id = models.PositiveIntegerField(default=1)
    rooms = models.ManyToManyField(Room)
    name = models.CharField(max_length=50, null=True)
    address = models.CharField(max_length=500, null=True)
    phone = models.BigIntegerField(null=True)
    aadhar = models.BigIntegerField(null=True)
    email = models.EmailField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    checkin_datetime = models.DateTimeField(null=True)
    checkout_datetime = models.DateTimeField(null=True)
    persons = models.CharField(max_length=50, null=True)
    payment = {
        ('upi','UPI'),
        ('cash', 'Cash'),
        ('debit/credit_card','Debit/Credit_Card'),
        ('netbanking','NetBanking'),
    }
    payment = models.CharField(max_length=20, choices=payment , null=True)

    REASON_CHOICES = [
        ('marriage', 'Marriage'),
        ('tour', 'Tour'),
        ('official_work', 'Official_Work'),
        ('other', 'Other'),
    ]

    reason = models.CharField(max_length=20, choices=REASON_CHOICES, null=True)

    def save(self, *args, **kwargs):
        # Check if the user profile is restricted
        if self.user_profile and self.user_profile.is_restricted:
            raise PermissionError("This profile is restricted from creating or modifying bookings.")

        # Logic for auto-incrementing user-specific booking ID
        if not self.pk:  # New object
            last_booking = Booking.objects.filter(user_profile=self.user_profile).order_by('user_specific_id').last()
            if last_booking:
                self.user_specific_id = last_booking.user_specific_id + 1
            else:
                self.user_specific_id = 1
        super(Booking, self).save(*args, **kwargs)