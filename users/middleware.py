
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout
from users.models.userprofile import UserProfile

class CheckIfUserFrozenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                user_profile = request.user.userprofile
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=request.user)

            if user_profile.is_frozen:
                messages.error(request, 'Your account has been frozen. Please contact support.')
                logout(request)
                return redirect('login')

        response = self.get_response(request)
        return response

from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout
from users.models.staff import Staff
'''
class CheckIfStaffInactiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        staff_id = request.session.get('staff_id')  # Use session or token for identifying staff login
        if staff_id:
            try:
                staff_member = Staff.objects.get(id=staff_id)
                # Check if the staff member is inactive
                if not staff_member.is_active:
                    messages.error(request, 'Your staff account is inactive. Please contact support.')
                    # Log the staff member out (remove session data)
                    request.session.flush()
                    return redirect('staff_login')  # Redirect to the staff login page
            except Staff.DoesNotExist:
                # In case the staff member is not found, clear the session
                request.session.flush()
                return redirect('staff_login')

        response = self.get_response(request)
        return response

'''
from django.contrib import messages
from django.shortcuts import redirect
from users.models.staff import Staff

class CheckIfStaffInactiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get staff_id from session to check if the staff member is logged in
        staff_id = request.session.get('staff_id')

        if staff_id:
            try:
                # Fetch the staff member object using the ID stored in the session
                staff_member = Staff.objects.get(id=staff_id)

                # If the staff member is inactive, log them out
                if not staff_member.is_active:
                    # Display an error message
                    messages.error(request, 'Your staff account is inactive. Please contact support.')

                    # Flush the session to log out the staff member
                    request.session.flush()

                    # Redirect to the staff login page
                    return redirect('staff_login')
            except Staff.DoesNotExist:
                # If the staff member does not exist, flush session and redirect to login
                request.session.flush()
                return redirect('staff_login')

        # Proceed with the request if the staff is still active
        response = self.get_response(request)
        return response
