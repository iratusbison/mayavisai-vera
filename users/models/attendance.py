from django.db import models

from django.utils import timezone

from .member import Member


class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    time_in = models.TimeField(default=timezone.now)  # In-time for attendance
    time_out = models.TimeField(null=True, blank=True)  # Out-time for attendance
    present = models.BooleanField(default=False)  # Mark present/absent

    def __str__(self):
        return f"{self.member.name} - {self.date} In: {self.time_in} Out: {self.time_out or 'Not marked'}"
