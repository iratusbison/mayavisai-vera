from django.test import TestCase, Client
from django.urls import reverse
from .models import Member, Payment, Attendance, UserProfile
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime

class PaymentViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.user_profile = UserProfile.objects.create(user=self.user)
        self.member = Member.objects.create(name="John Doe", unique_number="12345", user_profile=self.user_profile)
        self.client.login(username='testuser', password='12345')

    def test_add_payment(self):
        response = self.client.post(reverse('add_payment', args=[self.member.id]), {
            'payment_type': 'monthly',
            'amount': 100.00,
            'payment_date': '2023-05-01'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful payment addition
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.first()
        self.assertEqual(payment.member, self.member)

    def test_payment_list_all(self):
        Payment.objects.create(member=self.member, payment_type='monthly', amount=100.00, payment_date=timezone.now().date())
        response = self.client.get(reverse('payment_list_all'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')

    def test_generate_pdf_receipt(self):
        payment = Payment.objects.create(member=self.member, payment_type='monthly', amount=100.00, payment_date=timezone.now().date())
        response = self.client.get(reverse('generate_pdf_receipt', args=[payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="receipt_{payment.receipt_id}.pdf"')

class AttendanceViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.user_profile = UserProfile.objects.create(user=self.user)
        self.member = Member.objects.create(name="John Doe", unique_number="12345", user_profile=self.user_profile)
        self.client.login(username='testuser', password='12345')

    def test_mark_attendance(self):
        response = self.client.post(reverse('mark_attendance'), {'identifier': self.member.unique_number})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Attendance.objects.count(), 1)
        attendance = Attendance.objects.first()
        self.assertEqual(attendance.member, self.member)

    def test_attendance_list(self):
        Attendance.objects.create(member=self.member, date=timezone.now().date(), present=True)
        response = self.client.get(reverse('attendance_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
