from django import forms
from users.models.expense import ESection, Expense
from users.models.member import Member
from users.models.payment import Payment
from users.models.attendance import Attendance
from django.forms.widgets import DateInput
from users.models.staff import Staff
#from users.models.userprofile import SubAccount
from django.contrib.auth.hashers import make_password
from django.contrib.auth.forms import UserCreationForm
from users.models.userprofile import UserProfile



class PaymentEditForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_type', 'programme', 'batch', 'amount', 'payment_date', 'custom_expiry_date', 'status', 'pay_id']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'custom_expiry_date': forms.DateInput(attrs={'type': 'date'})  # Add widget for custom_expiry_date
        }



class UserProfileEditForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'email', 'location']
        widgets = {
            'phone': forms.NumberInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }


class MemberSelectForm(forms.Form):
    members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select Members"
    )
    message_template = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter message template here...',
            'rows': 4,
            'cols': 50
        }),
        required=True,
        label="Message Template"
    )
# Custom form to include management type
class CustomUserCreationForm(UserCreationForm):
    MANAGEMENT_CHOICES = [
        ('gym', 'Gym Management'),
        ('room_booking', 'Room Booking Management'),
    ]
    management_type = forms.ChoiceField(choices=MANAGEMENT_CHOICES, label='Select Management Type')

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('management_type',)



class SubAccountForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['username', 'email', 'password']

    def save(self, commit=True):
        subaccount = super().save(commit=False)
        subaccount.password = make_password(self.cleaned_data['password'])
        if commit:
            subaccount.save()
        return subaccount

class StaffSignUpForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['username', 'phone', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [ 'name', 'reg_no', 'gender', 'email', 'phone', 'emergency_number',  'DOB', 'address',  'image', 'weight', 'height', 'exercise_history', 'medications', 'surgeries', 'heart_disease', 'medical_history', 'allergies', 'blood_pressure', 'diabetes', 'arthritis']
        widgets = {
            'DOB': forms.DateInput(attrs={'type': 'date'})
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_type', 'programme', 'amount', 'payment_date', 'batch', 'custom_expiry_date', 'pay_id']  # Include custom_expiry_date in form
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'custom_expiry_date': forms.DateInput(attrs={'type': 'date'})  # Add widget for custom_expiry_date
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['member', 'date', 'present']

class ESectionForm(forms.ModelForm):
    class Meta:
        model = ESection
        fields = ['name']

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['description', 'amount', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from users.models.viber import Viber

class ViberSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)
    bio = forms.CharField(widget=forms.Textarea, required=False)
    location = forms.CharField(max_length=500, required=False)
    birth_date = forms.DateField(required=False, widget=forms.SelectDateWidget(years=range(1900, 2100)))
    gender = forms.ChoiceField(choices=Viber.GENDERS, required=False)
    image = forms.ImageField(required=False)
    weight = forms.CharField(max_length=30, required=False)
    height = forms.CharField(max_length=30, required=False)
    exercise_history = forms.CharField(max_length=300, required=False)
    medications = forms.CharField(max_length=500, required=False)
    surgeries = forms.CharField(max_length=400, required=False)
    heart_disease = forms.CharField(max_length=500, required=False)
    medical_history = forms.CharField(max_length=250, required=False)
    allergies = forms.CharField(max_length=300, required=False)
    blood_pressure = forms.ChoiceField(choices=[
        ('low', 'Low'),
        ('high', 'High'),
        ('normal', 'Normal')
    ], required=False)
    diabetes = forms.ChoiceField(choices=[
        ('low', 'Low'),
        ('high', 'High'),
        ('normal', 'Normal')
    ], required=False)
    arthritis = forms.ChoiceField(choices=[
        ('no', 'No'),
        ('ligament_injuries', 'Ligament Injuries'),
        ('muscle_injuries', 'Muscle Injuries'),
        ('tendon_injuries', 'Tendon Injuries')
    ], required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2', 'bio', 'location', 'birth_date',
                  'gender', 'image', 'weight', 'height', 'exercise_history', 'medications', 'surgeries',
                  'heart_disease', 'medical_history', 'allergies', 'blood_pressure', 'diabetes', 'arthritis')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def save(self, commit=True):
        user = super(ViberSignupForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            viber = Viber.objects.create(
                user=user,
                bio=self.cleaned_data.get('bio'),
                location=self.cleaned_data.get('location'),
                birth_date=self.cleaned_data.get('birth_date'),
                gender=self.cleaned_data.get('gender'),
                email=self.cleaned_data.get('email'),
                phone=self.cleaned_data.get('phone'),
                image=self.cleaned_data.get('image'),
                weight=self.cleaned_data.get('weight'),
                height=self.cleaned_data.get('height'),
                exercise_history=self.cleaned_data.get('exercise_history'),
                medications=self.cleaned_data.get('medications'),
                surgeries=self.cleaned_data.get('surgeries'),
                heart_disease=self.cleaned_data.get('heart_disease'),
                medical_history=self.cleaned_data.get('medical_history'),
                allergies=self.cleaned_data.get('allergies'),
                blood_pressure=self.cleaned_data.get('blood_pressure'),
                diabetes=self.cleaned_data.get('diabetes'),
                arthritis=self.cleaned_data.get('arthritis')
            )
        return user

class ViberEditForm(forms.ModelForm):
    class Meta:
        model = Viber
        fields = ['bio', 'location', 'birth_date', 'gender', 'email', 'phone', 'image', 'weight', 'height', 'exercise_history', 'medications', 'surgeries', 'heart_disease', 'medical_history', 'allergies', 'blood_pressure', 'diabetes', 'arthritis']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }