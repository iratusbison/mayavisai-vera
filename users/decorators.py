from django.shortcuts import redirect

from functools import wraps

def staff_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'staff' not in request.session:
            return redirect('stafflogin')  # Redirect to the staff login page
        return view_func(request, *args, **kwargs)
    return wrapper

def member_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'member' not in request.session:
            return redirect('memberlogin')  # Redirect to the staff login page
        return view_func(request, *args, **kwargs)
    return wrapper

