from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import csv
from django.utils import timezone
from users.models.attendance import Attendance
from users.models.userprofile import UserProfile
from users.models.payment import Payment
from django.contrib.auth.decorators import login_required
from users.models.member import Member
from django.utils import timezone
import pytz
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from datetime import datetime
from users.forms import AttendanceForm
from datetime import datetime, timedelta

@login_required
def mark_attendance(request):
    user_profile = request.user.userprofile
    today = timezone.now().date()
    local_tz = pytz.timezone('Asia/Kolkata')
    current_time = timezone.now().astimezone(local_tz).time()
    total_attendance_today = Attendance.objects.filter(date=today, member__user_profile=user_profile).count()
    member_image = None  # Initialize member image variable

    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        if identifier:
            try:
                member = Member.objects.get(name=identifier, user_profile=user_profile)
            except Member.DoesNotExist:
                member = None
                if identifier.isdigit():
                    try:
                        member = Member.objects.get(unique_number=identifier, user_profile=user_profile)
                    except Member.DoesNotExist:
                        member = None
                    if member is None:
                        try:
                            member = Member.objects.get(reg_no=identifier, user_profile=user_profile)
                        except Member.DoesNotExist:
                            member = None
                else:
                    try:
                        member = Member.objects.get(phone=identifier, user_profile=user_profile)
                    except Member.DoesNotExist:
                        member = None

            # If no member found
            if member is None:
                messages.error(request, "Member not found.")
                return render(request, 'mark_attendance.html', {'total_attendance_today': total_attendance_today})

            # Save the member image for later use in the template
            member_image = member.image.url if member.image else None

            if member.archived or member.personal_archived:
                messages.error(request, "Cannot mark attendance for archived or personal archived member.")
                return render(request, 'mark_attendance.html', {'total_attendance_today': total_attendance_today})

            # Check for an incomplete record from yesterday
            yesterday = today - timedelta(days=1)
            previous_attendance = Attendance.objects.filter(member=member, date=yesterday).first()

            if previous_attendance and not previous_attendance.time_out:
                # Keep the time-out as None instead of setting a default 9 PM time
                previous_attendance.time_out = None
                previous_attendance.save()


            #if previous_attendance and not previous_attendance.time_out:
                #previous_attendance.time_out = timezone.now().replace(hour=21, minute=0).time()  # default time-out as 9 PM
                #previous_attendance.save()

            # Check if today's attendance has been marked
            attendance_today = Attendance.objects.filter(member=member, date=today).first()

            if attendance_today:
                if not attendance_today.time_out:
                    attendance_today.time_out = current_time
                    attendance_today.save()
                    messages.success(request, f"Out time marked for {member.name}.")
                else:
                    messages.error(request, f"Attendance already marked for {member.name}.")
            else:
                # Mark today's time-in
                Attendance.objects.create(member=member, time_in=current_time, present=True, date=today)
                total_attendance_today += 1
                messages.success(request, f"In time marked for {member.name}.")

            # Handle expiry check for payments
            latest_payment = member.payment_set.filter(status='completed').order_by('-expiry_date').first()
            if latest_payment:
                expiry_date_exceeded = latest_payment.expiry_date < today
                formatted_expiry_date = latest_payment.expiry_date.strftime("%d/%m/%Y")
                if expiry_date_exceeded:
                    messages.add_message(request, messages.INFO, f"{member.name} payment expiry date: {formatted_expiry_date}", extra_tags="expired")
                else:
                    messages.add_message(request, messages.INFO, f"{member.name} payment expiry date: {formatted_expiry_date}", extra_tags="valid")
            else:
                messages.warning(request, f"{member.name} - No payment details found for this member.")
        else:
            messages.error(request, "No identifier provided.")

    return render(request, 'mark_attendance.html', {
        'total_attendance_today': total_attendance_today,
        'member_image': member_image  # Pass the member image URL to the template
    })


@login_required
def attendance_list(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    user_profile = request.user.userprofile

    # Prepare filter query
    filter_kwargs = {'member__user_profile': user_profile}
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        filter_kwargs.update({'date__range': (start_date, end_date)})

    # Use prefetch_related to reduce query count (fetch payments in a single query)
    attendances = Attendance.objects.filter(**filter_kwargs).select_related('member').prefetch_related(
        'member__payment_set').order_by('date', 'time_in')

    # Process the payments (pre-fetched)
    today = timezone.now().date()
    attendance_with_expiry = []

    for attendance in attendances:
        latest_payment = None
        for payment in attendance.member.payment_set.all():
            if payment.status == 'completed':
                if latest_payment is None or payment.expiry_date > latest_payment.expiry_date:
                    latest_payment = payment

        if latest_payment:
            days_until_expiry = (latest_payment.expiry_date - today).days
            if days_until_expiry <= 7:  # If expiry date is within the next 7 days
                if days_until_expiry < 0:
                    expiry_status = "Expired"
                elif days_until_expiry <= 5:
                    expiry_status = f"Expiring in {days_until_expiry} days"
                else:
                    expiry_status = f"Due in {days_until_expiry} days"
            else:
                expiry_status = "Valid"
            attendance_with_expiry.append((attendance, latest_payment.expiry_date, expiry_status))
        else:
            attendance_with_expiry.append((attendance, None, "No payment details"))

    total_attendance = attendances.count()

    return render(request, 'attendance_list.html', {
        'attendances': attendances,
        'total_attendance': total_attendance,
        'attendance_with_expiry': attendance_with_expiry
    })



@login_required
def member_attendance_details(request, member_id):
    # Retrieve the member object
    member = get_object_or_404(Member, pk=member_id, user_profile=request.user.userprofile)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot view attendance details for archived or personal archived member.")
        return redirect('member_detail', pk=member_id)

    # Get the date range from the request, if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Set the default date range to the current month if no range is provided
    if not start_date or not end_date:
        start_date = timezone.now().replace(day=1).date()
        end_date = timezone.now().date()
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Filter attendance records based on the date range
    attendances = Attendance.objects.filter(member=member, date__range=(start_date, end_date))

    # Count presents and absents
    total_present = attendances.filter(present=True).count()
    total_absent = attendances.filter(present=False).count()

    attendance_with_expiry = []
    today = timezone.now().date()
    latest_payment = member.payment_set.filter(status='completed').order_by('-expiry_date').first()

    for attendance in attendances:
        if latest_payment:
            days_until_expiry = (latest_payment.expiry_date - today).days
            if days_until_expiry <= 7:  # If expiry date is within the next 7 days
                if days_until_expiry < 0:
                    expiry_status = "Expired"
                elif days_until_expiry <= 2:
                    expiry_status = f"Due in {days_until_expiry} days"
                else:
                    expiry_status = f"Expiring in {days_until_expiry} days"
            else:
                expiry_status = "Valid"
            attendance_with_expiry.append((attendance, latest_payment.expiry_date, expiry_status))
        else:
            attendance_with_expiry.append((attendance, None, "No payment details"))

    return render(request, 'member_attendance_details.html', {
        'member': member,
        'attendances': attendance_with_expiry,
        'total_present': total_present,
        'total_absent': total_absent,
        'start_date': start_date,
        'end_date': end_date
    })







from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
import pytz
from datetime import timedelta

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib import messages
from datetime import timedelta, datetime
import pytz

@login_required
def qr_mark_attendance_by_scan(request):
    user_profile = request.user.userprofile
    today = timezone.now().date()
    local_tz = pytz.timezone('Asia/Kolkata')
    current_time = timezone.now().astimezone(local_tz).time()

    MINIMUM_TIME_GAP = timedelta(minutes=1)  # Set a minimum 1-minute gap between time-in and time-out

    if request.method == 'POST':
        qr_data = request.POST.get('qr_data')

        if qr_data:
            try:
                # Extract the member ID from the QR data (URL)
                member_id = qr_data.split('/')[-2]  # Assuming URL format is like '/members/<member_id>/'
                member = get_object_or_404(Member, pk=member_id, user_profile=user_profile)
            except (ValueError, Member.DoesNotExist):
                messages.error(request, "Invalid QR code or member not found.")
                return render(request, 'scan_qr_attendance.html')

            if member.archived or member.personal_archived:
                messages.error(request, "Cannot mark attendance for archived or personal archived member.")
                return render(request, 'scan_qr_attendance.html')

            # Check for an incomplete record from yesterday
            yesterday = today - timedelta(days=1)
            previous_attendance = Attendance.objects.filter(member=member, date=yesterday).first()

            if previous_attendance and not previous_attendance.time_out:
                # Keep the time-out as None instead of setting a default 9 PM time
                previous_attendance.time_out = None
                previous_attendance.save()


            #if previous_attendance and not previous_attendance.time_out:
                #previous_attendance.time_out = timezone.now().replace(hour=21, minute=0).time()  # Default time-out at 9 PM
                #previous_attendance.save()

            # Check if today's attendance has been marked
            attendance_today = Attendance.objects.filter(member=member, date=today).first()

            if attendance_today:
                # Make sure both datetimes are timezone-aware
                time_in_datetime = timezone.make_aware(datetime.combine(today, attendance_today.time_in), local_tz)
                current_datetime = timezone.now()

                if current_datetime - time_in_datetime >= MINIMUM_TIME_GAP:
                    # Enough time has passed, mark time-out
                    if not attendance_today.time_out:
                        attendance_today.time_out = current_time
                        attendance_today.save()
                        messages.success(request, f"Out time marked for {member.name}.")
                    else:
                        messages.error(request, f"Attendance already marked for {member.name}.")
                else:
                    # Not enough time has passed, prevent marking time-out
                    messages.error(request, "Too soon to mark time-out. Try again after 1 minute.")
            else:
                # Mark today's time-in
                Attendance.objects.create(member=member, time_in=current_time, present=True, date=today)
                messages.success(request, f"In time marked for {member.name}.")
        else:
            messages.error(request, "No QR data provided.")

    return render(request, 'scan_qr_attendance.html')



