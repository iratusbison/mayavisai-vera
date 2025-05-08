from django.shortcuts import get_object_or_404
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
import random
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.units import mm
from datetime import datetime
from django.utils.timezone import make_aware
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.contrib import messages
from django.utils import timezone
from django.db.models import Max
from django.shortcuts import  render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm

from users.models.userprofile import UserProfile


def index(request):
    return render(request, 'minimal/index.html')



from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from users.models.userprofile import UserProfile
from users.forms import CustomUserCreationForm



def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Disable user login until admin approval
            user.save()

            # Create UserProfile instance
            #bio = request.POST.get('bio')
            location = request.POST.get('location')
            #birth_date = request.POST.get('birth_date')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            management_type = form.cleaned_data.get('management_type')

            if not phone or not location or not email:
                messages.error(request, 'All additional fields ( location,  email, phone) are required.')
                user.delete()  # Remove the user if additional fields are missing
                return render(request, 'signup.html', {'form': form})

            try:
                # Create the UserProfile and set the appropriate restriction
                user_profile = UserProfile.objects.create(
                    user=user,

                    location=location,

                    phone=phone,
                    email=email,
                    is_restricted=(management_type == 'gym'),
                    is_restricted_gym=(management_type == 'room_booking')
                )
            except ValidationError as e:
                messages.error(request, f'Error creating profile: {e.message}')
                user.delete()  # Remove the user if profile creation fails
                return render(request, 'signup.html', {'form': form})

            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)

            messages.success(request, f'Account created successfully for {username}. Your account is pending approval.')
            return redirect('pending_approval')
        else:
            errors = form.errors.as_data()
            for field, field_errors in errors.items():
                for error in field_errors:
                    if error.code == 'required':
                        messages.error(request, f'{field} is required.')
                    elif error.code == 'invalid':
                        messages.error(request, f'Invalid value for {field}.')
                    elif error.code == 'unique':
                        messages.error(request, f'{field} already exists.')
                    else:
                        messages.error(request, f'Error in {field}: {error.message}')
    else:
        form = CustomUserCreationForm()

    return render(request, 'signup.html', {'form': form})


'''
@login_required
def profile(request):
    #try:
        user_profile = request.user.userprofile
    #except UserProfile.DoesNotExist:
        # If UserProfile does not exist, create it
        #user_profile = UserProfile.objects.create(user=request.user)
        return render(request, 'profile.html', {'user_profile': user_profile})
'''

from users.forms import SubAccountForm
#from users.models.userprofile import SubAccount

@login_required
def profile(request):
    user_profile = request.user.userprofile
    subaccounts = user_profile.subaccounts.all()

    if request.method == 'POST':
        form = SubAccountForm(request.POST)
        if form.is_valid():
            subaccount = form.save(commit=False)
            subaccount.user_profile = user_profile
            subaccount.save()
            messages.success(request, 'Subaccount created successfully!')
            return redirect('profile')
    else:
        form = SubAccountForm()

    return render(request, 'profile.html', {'user_profile': user_profile, 'subaccounts': subaccounts, 'form': form})
'''
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            user_profile = UserProfile.objects.get(user=user)
            if user_profile.is_frozen:
                messages.error(request, 'Your account has been frozen. Please contact support.')
                return redirect('login')
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return redirect('login')
    return render(request, 'login.html')
'''

from users.models.staff import Staff

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from users.models.userprofile import UserProfile
from users.models.staff import Staff

def user_login(request):
     # Check if the user is already logged in
    if request.user.is_authenticated:
        try:
            # If the logged-in user is a main UserProfile
            user_profile = UserProfile.objects.get(user=request.user)

            # Check if the user is restricted
            if user_profile.is_restricted:
                return redirect('dashboard')  # Member Management System dashboard
            if user_profile.is_restricted_gym:
                return redirect('bdashboard')  # Room Booking Management System dashboard

        except UserProfile.DoesNotExist:
            pass

        # Check if a staff member is already logged in via session
    staff_id = request.session.get('staff')
    if staff_id:
        try:
            staff = Staff.objects.get(id=staff_id)

            # Check if the staff member is restricted
            if staff.is_restricted:
                return redirect('staffdashboard')  # Staff dashboard
            if staff.is_restricted_gym:
                return redirect('sbdashboard')  # Gym-specific dashboard

        except Staff.DoesNotExist:
            # Clear the session if the staff ID is invalid
            del request.session['staff']




    # If the user is not logged in, continue with the login process
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Try to authenticate as a main user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                user_profile = UserProfile.objects.get(user=user)

                # Check if the user profile is frozen
                if user_profile.is_frozen:
                    messages.error(request, 'Your account has been frozen due to inactivity or other issues. Please contact support for assistance.')
                    return redirect('login')
                if not user.is_active:  # Check if user is approved by admin
                    messages.error(request, 'Your account is pending approval by the admin. You will be notified once your account is approved.')
                    return redirect('pending_approval')

                # Log in the user before checking restrictions
                login(request, user)

                # Check if the user is restricted
                if user_profile.is_restricted:
                    messages.info(request, 'You are logged in to the Member Management System dashboard.')
                    return redirect('dashboard')

                # Check if the user is restricted specifically for gym-related features
                if user_profile.is_restricted_gym:
                    messages.info(request, 'You are logged in to the Room Booking Management System dashboard')
                    return redirect('bdashboard')

                # If no restrictions, proceed as normal
                messages.success(request, 'Logged in successfully!')
                return redirect('dashboard')

            except UserProfile.DoesNotExist:
                messages.error(request, 'UserProfile not found. Please contact support if you believe this is an error.')
                return redirect('login')

        # If not a main user, try to authenticate as a subaccount (Staff)
        try:
            subaccount = Staff.objects.get(username=username)

            # Check if the staff account is active
            if not subaccount.is_active:
                messages.error(request, 'Your staff account is currently inactive. Please contact support to activate your account.')
                return redirect('login')

            # Check the staff member's password
            if subaccount.check_password(password):
                # Set a session to identify this subaccount
                request.session['staff'] = subaccount.id

                # Check if the staff member is restricted
                if subaccount.is_restricted:
                    messages.info(request, 'You have been redirected to the main dashboard.')
                    return redirect('staffdashboard')

                # Check if the staff member is restricted specifically for gym
                if subaccount.is_restricted_gym:
                    messages.info(request, 'You have been redirected to the gym dashboard.')
                    return redirect('sbdashboard')

                # Log in the staff member manually by setting up the session
                messages.success(request, f'Logged in successfully as staff: {subaccount.username}.')
                return redirect('staffdashboard')

            else:
                messages.error(request, 'Invalid password for the staff account. Please check your password and try again.')
                return redirect('login')

        except Staff.DoesNotExist:
            messages.error(request, 'Staff account with this username does not exist. Please check the username and try again.')
            return redirect('login')

    return render(request, 'login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')


def pending_approval(request):
    return render(request, 'pending_approval.html')


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from users.forms import UserProfileEditForm

@login_required
def edit_profile(request):
    user_profile = request.user.userprofile

    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')  # Redirect to the profile page after successful update
    else:
        form = UserProfileEditForm(instance=user_profile)

    return render(request, 'edit_profile.html', {'form': form})








'''



from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from users.models.userprofile import UserProfile
from users.models.staff import Staff

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        # Check if user is a staff or a user profile
        try:
            user_profile = UserProfile.objects.get(user=request.user)

            if user_profile.is_frozen:
                return Response({'detail': 'Your account is frozen. Contact support.'}, status=status.HTTP_403_FORBIDDEN)

            if user_profile.is_restricted:
                response.data['dashboard'] = 'member_dashboard'

            elif user_profile.is_restricted_gym:
                response.data['dashboard'] = 'gym_dashboard'

            else:
                response.data['dashboard'] = 'general_dashboard'

        except UserProfile.DoesNotExist:
            # Handle staff login here
            staff_id = request.session.get('staff')
            if staff_id:
                staff = Staff.objects.get(id=staff_id)
                if staff.is_restricted:
                    response.data['dashboard'] = 'staff_dashboard'
                elif staff.is_restricted_gym:
                    response.data['dashboard'] = 'gym_staff_dashboard'

        return response








'''


