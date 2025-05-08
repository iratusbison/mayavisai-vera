from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from users.models.viber import Viber
from users.forms import ViberSignupForm, ViberEditForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from django.shortcuts import get_object_or_404

def viber_signup(request):
    if request.method == 'POST':
        form = ViberSignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created successfully for {user.username}")
            return redirect('viber_profile')
        
        else:
            # Specific error messages
            error_messages = {
                'username': "Username is invalid or already taken.",
                'email': "Email is invalid or already taken.",
                'password1': "Password is invalid. Ensure it meets all requirements.",
                'password2': "Password confirmation does not match.",
                'image': "There was an issue with the image upload."
            }
            for field, message in error_messages.items():
                if field in form.errors:
                    messages.error(request, message)

            # Catch-all for other errors
            if not any(form.errors):
                messages.error(request, "There was an issue with your signup. Please check the form for errors.")
    else:
        form = ViberSignupForm()

    return render(request, 'viber_signup.html', {'form': form})


def viber_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('viber_profile')
        else:
            if not User.objects.filter(username=username).exists():
                messages.error(request, "Username does not exist.")
            else:
                messages.error(request, "Password is incorrect. Please try again.")
    return render(request, 'viber_login.html')



@login_required
def viber_profile(request):
    viber = Viber.objects.get(user=request.user)
    bmr = viber.calculate_bmr()
    tdees = viber.calculate_all_tdees()
    macros_and_water = viber.calculate_macros_and_water()
    
    # Format the BMR and TDEE values to 2 decimal places
    context = {
        'viber': viber,
        'bmr': round(bmr, 2) if bmr else None,
        'tdees': {
            level: {
                'calories': round(tdee['calories'], 2),
                'carbs_grams': round(tdee['carbs_grams'], 2),
                'protein_grams': round(tdee['protein_grams'], 2),
                'fat_grams': round(tdee['fat_grams'], 2)
            } for level, tdee in tdees.items()
        } if tdees else None,
        'water_needs_ml': round(macros_and_water['water_needs_ml'], 2) if macros_and_water['water_needs_ml'] else None
    }
    
    return render(request, 'viber_profile.html', context)

    
    
@login_required
def viber_edit_profile(request):
    viber = get_object_or_404(Viber, user=request.user)
    
    if request.method == 'POST':
        form = ViberEditForm(request.POST, request.FILES, instance=viber)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('viber_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ViberEditForm(instance=viber)
    
    return render(request, 'viber_edit_profile.html', {'form': form})
