from django.db import models
from users.models.userprofile import UserProfile


class ESection(models.Model):
    name = models.CharField(max_length=100, null=True)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    esection = models.ForeignKey(ESection, on_delete=models.CASCADE, null=True)
    user_profile = models.ForeignKey('UserProfile', on_delete=models.CASCADE)

    def __str__(self):
        return self.description
