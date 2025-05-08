from django.db import models
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from .member import Member


class Payment(models.Model):
    PROGRAMME_CHOICES = [
        ('cardio','Cardio'),
        ('strength training','Strength Training'),
        ('strength training & cardio','Strength Training & Cardio'),
        ('personal training', 'Personal Training'),
        ('custom program','Custom Program')
    ]
    MEMBER_TYPES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('halfyearly', 'Half-Yearly'),
        ('annual', 'Annual'),
        ('custom', 'Custom')
    ]
    BATCH = [
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('custom batch', 'Custom Batch')
    ]
    STATUS_CHOICES = [

        ('completed', 'Completed'),
        ('holding', 'Holding')
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=MEMBER_TYPES)
    programme = models.CharField(max_length = 40, choices=PROGRAMME_CHOICES, null=True)
    batch = models.CharField(max_length=20, choices=BATCH, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    expiry_date = models.DateField(null=True)
    custom_expiry_date = models.DateField(null=True, blank=True)
    receipt_id = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='completed')

    pay_id = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):


        if self.payment_type == 'monthly':
            self.expiry_date = self.payment_date + timedelta(days=30) - timedelta(days=1)
        elif self.payment_type == 'quarterly':
            self.expiry_date = self.payment_date + timedelta(days=90) - timedelta(days=1)
        elif self.payment_type == 'halfyearly':
            self.expiry_date = self.payment_date + timedelta(days=180) - timedelta(days=1)
        elif self.payment_type == 'annual':
            self.expiry_date = self.payment_date + timedelta(days=365) - timedelta(days=1)

        # If custom_expiry_date is provided, use it instead of calculating expiry_date
        if self.payment_type == 'custom' and self.custom_expiry_date:
            self.expiry_date = self.custom_expiry_date

        # Generate serial receipt_id specific to each user profile if not already set
        if self.receipt_id is None:
            user_profile = self.member.user_profile
            last_payment = Payment.objects.filter(member__user_profile=user_profile).order_by('-receipt_id').first()
            if last_payment and last_payment.receipt_id:
                self.receipt_id = last_payment.receipt_id + 1
            else:
                self.receipt_id = 1

         # Set payment_id if not provided
        if self.pay_id is None:
            last_pay_id = Payment.objects.aggregate(models.Max('pay_id'))['pay_id__max']
            self.pay_id = last_pay_id + 1 if last_pay_id else 1

        super().save(*args, **kwargs)


    def clean(self):
        if self.payment_type == 'custom' and not self.custom_expiry_date:
            raise ValidationError({'custom_expiry_date': 'Custom expiry date is required for custom payment type.'})

        if self.payment_date and self.custom_expiry_date and self.custom_expiry_date < self.payment_date:
            raise ValidationError({'custom_expiry_date': 'Custom expiry date cannot be before the payment date.'})

    def __str__(self):
        return f"{self.member.name}'s-{self.member.unique_number}- {self.payment_type} payment"

