from django.shortcuts import render, redirect, get_object_or_404
from users.models.staff import Staff, StaffAttendance
from users.models.payment import Payment
from users.forms import PaymentForm
from django.views import View
from users.decorators import staff_login_required
from users.models.member import Member
from django.contrib.auth.decorators import login_required
from users.forms import StaffSignUpForm
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib import messages
import pytz
from datetime import datetime


from django.core.exceptions import PermissionDenied
from django.utils import timezone

from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from users.forms import MemberForm
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from users.models.member import Member
from users.models.attendance import Attendance  # Import Attendance model if used
from users.decorators import staff_login_required

from django.utils import timezone
import pytz
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.utils import timezone
import pytz

from django.utils import timezone
import pytz
from django.contrib import messages


@staff_login_required
def staff_mark_attendance(request):
    # Get the logged-in staff from the session
    staff_id = request.session.get('staff')
    staff = Staff.objects.get(id=staff_id)

    today = timezone.now().date()
    local_tz = pytz.timezone('Asia/Kolkata')
    current_time = timezone.now().astimezone(local_tz).time()

    # Count today's attendance for the staff
    staff_total_attendance_today = StaffAttendance.objects.filter(date=today, staff=staff).count()

    if request.method == 'POST':
        # Attendance logic remains the same
        attendance_record = StaffAttendance.objects.filter(staff=staff, date=today).first()

        if attendance_record:
            if attendance_record.time_out is None:
                attendance_record.time_out = current_time
                attendance_record.save()
                messages.success(request, f"Time out marked for {staff.username}")
            else:
                messages.error(request, f"Attendance already fully marked for {staff.username}")
        else:
            attendance = StaffAttendance(staff=staff, present=True, date=today, time_in=current_time)
            attendance.save()
            staff_total_attendance_today += 1
            messages.success(request, f"Time in marked for {staff.username}")

    return render(request, 'staff_mark_attendance.html', {'staff_total_attendance_today': staff_total_attendance_today})

@login_required
def staff_attendance_list(request):
    user_profile = request.user.userprofile  # Get the logged-in user's profile

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        attendances = StaffAttendance.objects.filter(
            date__range=(start_date, end_date),
            staff__user_profiles=user_profile  # Only retrieve attendance for staff under the current user profile
        ).select_related('staff').order_by('staff__username', 'date')
    else:
        attendances = StaffAttendance.objects.filter(
            staff__user_profiles=user_profile  # Only retrieve attendance for staff under the current user profile
        ).select_related('staff').order_by('staff__username', 'date')

    total_attendance = attendances.count()

    return render(request, 'staff_attendance_list.html', {
        'attendances': attendances,
        'total_attendance': total_attendance
    })