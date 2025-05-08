from django.shortcuts import render, redirect, get_object_or_404
from users.models.staff import Staff, StaffAttendance
from users.models.payment import Payment
from users.forms import PaymentForm
from django.views import View
from users.decorators import staff_login_required
from users.models.member import Member
from django.contrib.auth.decorators import login_required
from users.forms import StaffSignUpForm

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password

from django.contrib import messages
from django.db import IntegrityError

@login_required
def staff_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_profile = request.user.userprofile

        # Basic validation
        if not username or not phone or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect('staff_signup')

        # Check if a staff member with the same email already exists
        if Staff.objects.filter(email=email).exists():
            messages.error(request, "A staff member with this email already exists.")
            return redirect('staff_signup')

        # Check if a staff member with the same username already exists
        if Staff.objects.filter(username=username).exists():
            messages.error(request, "A staff member with this username already exists.")
            return redirect('staff_signup')

        try:
            hashed_password = make_password(password)
            staff = Staff.objects.create(
                username=username,
                phone=phone,
                email=email,
                password=hashed_password,
                user_profiles=user_profile
            )
            messages.success(request, "Staff account created successfully.")
            return redirect('staff_list')  # Redirect to the staff list or any other page
        except IntegrityError:
            messages.error(request, "An error occurred during staff signup. Please try again.")
            return redirect('staff_signup')

    return render(request, 'staff_signup.html')

@login_required
def staff_list(request):
    user_profile = request.user.userprofile
    staffs = Staff.objects.filter(user_profiles=user_profile)
    return render(request, 'staff_list.html', {'staffs': staffs})

'''
class StaffLogin(View):
    def get(self, request):
        return render(request, 'stafflogin.html')

    def post(self, request):
        postData = request.POST
        email = postData.get('email')
        password = postData.get('password')

        error_message = None

        if not email or not password:
            error_message = "Please fill out all fields."
        else:
            try:
                staff = Staff.objects.get(email=email)
                if staff.check_password(password):
                    # Log in the staff by saving their ID in the session
                    request.session['staff'] = staff.id
                    return redirect('staffdashboard')  # Replace with actual dashboard view name
                else:
                    error_message = "Invalid credentials. Please try again."
            except Staff.DoesNotExist:
                error_message = "Email not registered. Please sign up."

        data = {
            'error': error_message,
            'email': email
        }
        return render(request, 'stafflogin.html', data)
'''
def stafflogout(request):
    request.session.clear()
    return redirect('login')

from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib import messages
import pytz
from datetime import datetime

from datetime import datetime, timedelta
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

@staff_login_required
def smember_list(request):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance

    # Gather member data related to this user profile
    members = Member.objects.filter(user_profile=user_profile, archived=False, personal_archived=False)

    active_members = []
    inactive_members = []
    for member in members:
        recent_payment = member.payment_set.exclude(status='holding').order_by('-payment_date').first()
        if recent_payment and recent_payment.expiry_date >= timezone.now().date():
            active_members.append((member, recent_payment))
        else:
            inactive_members.append((member, recent_payment))

    total_active_members = len(active_members)
    total_inactive_members = len(inactive_members)
    total_members = total_active_members + total_inactive_members

    # Calculate total attendance for today
    total_attendance_today = Attendance.objects.filter(date=timezone.now().date(), member__user_profile=user_profile).count()

    # Count personal archived members
    personal_archived_members = members.filter(personal_archived=True).count()

    context = {
        'active_members': active_members,
        'inactive_members': inactive_members,
        'total_active_members': total_active_members,
        'total_inactive_members': total_inactive_members,
        'total_members': total_members,
        'total_attendance_today': total_attendance_today,
        'personal_archived_members': personal_archived_members,
        'user_profile': user_profile,
    }
    return render(request, 'smember_list.html', context)


# Member addition for staff
@staff_login_required
def sadd_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)
            # Fetch staff and related UserProfile
            staff_id = request.session.get('staff')
            staff = get_object_or_404(Staff, id=staff_id)
            user_profile = staff.user_profiles

            # Validate uniqueness of phone and registration number within the UserProfile
            if Member.objects.filter(user_profile=user_profile, phone=member.phone).exists():
                form.add_error('phone', "A member with this phone already exists in your profile.")
            elif member.reg_no and Member.objects.filter(user_profile=user_profile, reg_no=member.reg_no).exists():
                form.add_error('reg_no', "A member with this registration number already exists in your profile.")
            else:
                member.user_profile = user_profile
                member.save()
                return redirect('smember_list')
    else:
        form = MemberForm()

    return render(request, 'sadd_member.html', {'form': form})

@staff_login_required
def smember_update(request, pk):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)
    user_profile = staff.user_profiles

    member = get_object_or_404(Member, pk=pk, user_profile=user_profile)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot edit archived or personal archived member.")
        return redirect('smember_detail', pk=pk)

    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            updated_member = form.save(commit=False)
            # Check if another member with the same phone exists for this UserProfile
            if Member.objects.filter(user_profile=user_profile, phone=updated_member.phone).exclude(pk=member.pk).exists():
                form.add_error('phone', "A member with this phone already exists in your profile.")
            # Check if reg_no is filled and another member with the same reg_no exists for this UserProfile
            elif updated_member.reg_no and Member.objects.filter(user_profile=user_profile, reg_no=updated_member.reg_no).exclude(pk=member.pk).exists():
                form.add_error('reg_no', "A member with this registration number already exists in your profile.")
            else:
                updated_member.save()
                return redirect('smember_detail' ,pk=pk)
    else:
        form = MemberForm(instance=member)

    return render(request, 'sadd_member.html', {'form': form, 'member': member, 'is_update': True})


'''
@staff_login_required
def sadd_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)

            # Ensure that the staff's user profile is used to assign the member
            staff_id = request.session.get('staff')
            staff = get_object_or_404(Staff, id=staff_id)
            user_profile = staff.user_profiles  # Single UserProfile instance

            # Check if the email already exists for this UserProfile
            if Member.objects.filter(email=member.email, user_profile=user_profile).exists():
                form.add_error('email', 'A member with this email already exists in your profile.')
                return render(request, 'sadd_member.html', {'form': form})

            member.user_profile = user_profile
            member.save()
            return redirect('smember_list')
    else:
        form = MemberForm()
    return render(request, 'sadd_member.html', {'form': form})
'''


@staff_login_required
def spersonal_archive_list(request):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    personal_archived_members = Member.objects.filter(user_profile=staff.user_profiles, personal_archived=True)
    return render(request, 'spersonal_archive_list.html', {'personal_archived_members': personal_archived_members})
@staff_login_required
def smark_attendance(request):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles

    today = timezone.now().date()
    local_tz = pytz.timezone('Asia/Kolkata')
    current_time = timezone.now().astimezone(local_tz).time()

    total_attendance_today = Attendance.objects.filter(date=today, member__user_profile=user_profile).count()
    member_image = None  # Initialize member image variable

    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        if identifier:
            try:
                # Attempt to find the member by name first
                member = Member.objects.get(name=identifier, user_profile=user_profile)
            except Member.DoesNotExist:
                member = None

                # If the identifier is a digit, search by unique_number and reg_no
                if identifier.isdigit():
                    try:
                        member = Member.objects.get(unique_number=identifier, user_profile=user_profile)
                    except Member.DoesNotExist:
                        member = None

                    # Try reg_no if unique_number search fails
                    if member is None:
                        try:
                            member = Member.objects.get(reg_no=identifier, user_profile=user_profile)
                        except Member.DoesNotExist:
                            member = None
                else:
                    # If identifier is not a digit, try phone
                    try:
                        member = Member.objects.get(phone=identifier, user_profile=user_profile)
                    except Member.DoesNotExist:
                        member = None

            # If no member found
            if member is None:
                messages.error(request, "Member not found.")
                return render(request, 'smark_attendance.html', {'total_attendance_today': total_attendance_today})

            # Save the member image for later use in the template
            member_image = member.image.url if member.image else None

            if member.archived or member.personal_archived:
                messages.error(request, "Cannot mark attendance for archived or personal archived member.")
                return render(request, 'smark_attendance.html', {'total_attendance_today': total_attendance_today, 'member_image': member_image})

            # Check for an incomplete record from yesterday
            yesterday = today - timedelta(days=1)
            previous_attendance = Attendance.objects.filter(member=member, date=yesterday).first()

            if previous_attendance and not previous_attendance.time_out:
                previous_attendance.time_out = timezone.now().replace(hour=21, minute=0).time()  # default time-out as 9 PM
                previous_attendance.save()

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

    return render(request, 'smark_attendance.html', {
        'total_attendance_today': total_attendance_today,
        'member_image': member_image  # Pass the member image URL to the template
    })
@staff_login_required
def sattendance_list(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles

    # Prepare filter for attendance query
    filter_kwargs = {'member__user_profile': user_profile}
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        filter_kwargs.update({'date__range': (start_date, end_date)})

    # Use prefetch_related to fetch payments in one query
    attendances = Attendance.objects.filter(**filter_kwargs).select_related('member').prefetch_related(
        'member__payment_set').order_by('date', 'time_in', 'member__name')

    today = timezone.now().date()
    attendance_with_expiry = []

    # Process payments for each attendance, which is pre-fetched
    for attendance in attendances:
        latest_payment = None
        for payment in attendance.member.payment_set.all():
            if payment.status == 'completed':
                if latest_payment is None or payment.expiry_date > latest_payment.expiry_date:
                    latest_payment = payment

        if latest_payment:
            days_until_expiry = (latest_payment.expiry_date - today).days
            if days_until_expiry <= 7:
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

    return render(request, 'sattendance_list.html', {
        'attendances': attendances,
        'total_attendance': total_attendance,
        'attendance_with_expiry': attendance_with_expiry
    })


@staff_login_required
def sadd_payment(request, member_id):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    member = get_object_or_404(Member, pk=member_id, user_profile=staff.user_profiles)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot add payment to archived or personal archived member.")
        return redirect('smember_detail', pk=member_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.member = member
            if 'hold_payment' in request.POST:
                payment.status = 'holding'
            else:
                payment.status = 'completed'
            payment.save()
            return redirect('smember_detail', pk=member_id)
    else:
        form = PaymentForm()
    return render(request, 'sadd_payment.html', {'form': form, 'member': member})
@staff_login_required
def spayment_holding_list(request):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    payments = Payment.objects.filter(status='holding', member__user_profile=staff.user_profiles)
    return render(request, 'spayment_holding_list.html', {'payments': payments})
@staff_login_required
def spersonal_archive_member(request, member_id):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    member = get_object_or_404(Member, pk=member_id, user_profile=staff.user_profiles)

    if request.method == 'POST':
        member.personal_archived = True
        member.save()
        messages.success(request, '(personal)Member archived successfully.')

    return redirect('smember_detail', pk=member_id)
@staff_login_required
def spersonal_unarchive_member(request, member_id):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    member = get_object_or_404(Member, pk=member_id, user_profile=staff.user_profiles)

    if request.method == 'POST':
        member.personal_archived = False
        member.save()
        messages.success(request, '(personal)Member unarchived successfully.')

    return redirect('smember_detail', pk=member_id)
@staff_login_required
def smember_detail(request, pk):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance

    # Filter member based on the staff's associated UserProfile
    member = get_object_or_404(Member, pk=pk, user_profile=user_profile)

    if member.archived:
        return render(request, 'smember_detail.html', {'member': member, 'member_id': pk})

    elif member.user_profile == user_profile:
        attendances = Attendance.objects.filter(member=member)
        payment = Payment.objects.filter(member=member).order_by('-payment_date').first()
        return render(request, 'smember_detail.html', {'member': member, 'attendances': attendances, 'payment': payment, 'member_id': pk})

    else:
        return HttpResponse("Permission Denied")


from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
import pytz
from datetime import timedelta, datetime

@staff_login_required  # Ensures only staff can access
def staff_qr_mark_attendance_by_scan(request):
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles

    today = timezone.now().date()
    local_tz = pytz.timezone('Asia/Kolkata')
    current_time = timezone.now().astimezone(local_tz).time()

    # Minimum time gap to prevent double marking
    MINIMUM_TIME_GAP = timedelta(minutes=1)

    if request.method == 'POST':
        qr_data = request.POST.get('qr_data')

        if qr_data:
            try:
                # Extract the member ID from the QR data (URL)
                member_id = qr_data.split('/')[-2]  # Assuming URL format is like '/members/<member_id>/'
                member = get_object_or_404(Member, pk=member_id, user_profile=user_profile)
            except (ValueError, Member.DoesNotExist):
                messages.error(request, "Invalid QR code or member not found.")
                return render(request, 'staff_scan_qr_attendance.html')

            if member.archived or member.personal_archived:
                messages.error(request, "Cannot mark attendance for archived or personal archived member.")
                return render(request, 'staff_scan_qr_attendance.html')

            # Check for an incomplete record from yesterday
            yesterday = today - timedelta(days=1)
            previous_attendance = Attendance.objects.filter(member=member, date=yesterday).first()

            if previous_attendance and not previous_attendance.time_out:
                previous_attendance.time_out = timezone.now().replace(hour=21, minute=0).time()  # Default time-out at 9 PM
                previous_attendance.save()

            # Check if today's attendance has been marked
            attendance_today = Attendance.objects.filter(member=member, date=today).first()

            if attendance_today:
                # Ensure both datetimes are timezone-aware
                time_in_datetime = timezone.make_aware(datetime.combine(today, attendance_today.time_in), local_tz)
                current_datetime = timezone.now()

                # Check if sufficient time (e.g., 1 minute) has passed before marking time-out
                if current_datetime - time_in_datetime >= MINIMUM_TIME_GAP:
                    if not attendance_today.time_out:
                        attendance_today.time_out = current_time
                        attendance_today.save()
                        messages.success(request, f"Out time marked for {member.name}.")
                    else:
                        messages.error(request, f"Attendance already marked for {member.name}.")
                else:
                    messages.error(request, "Too soon to mark time-out. Please wait 1 minute before marking again.")
            else:
                # Mark today's time-in
                Attendance.objects.create(member=member, time_in=current_time, present=True, date=today)
                messages.success(request, f"In time marked for {member.name}.")

            # Check for payment expiry
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
            messages.error(request, "No QR data provided.")

    return render(request, 'staff_scan_qr_attendance.html')




import os
import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from PIL import Image as PilImage, ImageDraw
from django.contrib.auth.decorators import login_required
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import random

from django.utils import timezone

@staff_login_required
def generate_pdf_receipt_for_staff(request, payment_id, member_id):
    # Retrieve staff details from session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve payment and member details
    payment = get_object_or_404(Payment, pk=payment_id, member__id=member_id)
    user_profile = payment.member.user_profile

    # Ensure the staff has access to the member's user profile
    if user_profile != staff.user_profiles:
        return HttpResponse("Permission Denied", status=403)

    # Ensure the receipt_id is generated and saved
    if payment.receipt_id is None:
        payment.save()

    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.receipt_id}.pdf"'

    # Define custom receipt size
    receipt_width, receipt_height = 210 * mm, 297 * mm
    doc = SimpleDocTemplate(response, pagesize=(receipt_width, receipt_height))

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = 1
    centered_style = ParagraphStyle(name='Centered', fontSize=10, alignment=1)

    # Elements to build PDF
    elements = []

    # Add title with user profile details
    elements.append(Paragraph(user_profile.user.username, title_style))
    elements.append(Spacer(1, 6))



    # Split and add location parts
    location_parts = user_profile.location.split(',')
    for part in location_parts:
        elements.append(Paragraph(part.strip(), centered_style))

    elements.append(Spacer(1, 24))

    # Create data for the table
    data = [
        ["Payment ID:", f"{payment.pay_id}"],
        ["Member:", f"{payment.member.name}"],
        ["ID Number:", f"{payment.member.unique_number}"],
        ["Batch:", f"{payment.batch}"],
        ["Payment Type:", f"{payment.payment_type}"],
        ["Amount:", f"Rs: {payment.amount}"],
        ["Expiry Date:", f"{payment.expiry_date.strftime('%B %d, %Y')}"],
        ["Payment Date:", f"{payment.payment_date.strftime('%B %d, %Y')}"],
    ]

    # Create and style table
    table = Table(data, colWidths=[50 * mm, 80 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
    ]))

    # Add the table and spacing elements
    elements.append(table)
    elements.append(Spacer(1, 12))

     # Add staff name as generated by
    elements.append(Paragraph(f"Generated by: {staff.username}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Add footer information
    current_date = timezone.now().strftime("%B %d, %Y")
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Issued on: {current_date}", styles['Normal']))
    elements.append(Paragraph("Use this QR code to access your member details and to mark your attendances!", styles['Normal']))



    # Generate QR code
    qr_data = request.build_absolute_uri(f"/members/{member_id}/")
    qr_img = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Add larger QR code
    qr_code_img = Image(qr_buffer, 250, 250)
    elements.append(qr_code_img)

    # Build the PDF document
    doc.build(elements)

    return response






@staff_login_required
def staff_member_payment_details(request, member_id):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the member, ensuring the member is associated with this staff's user profile
    member = get_object_or_404(Member, pk=member_id, user_profile=staff.user_profiles)


    # Check if the member is archived or personally archived
    if member.archived or member.personal_archived:
        messages.error(request, "Cannot view payment details for archived or personal archived member.")
        return redirect('member_detail', pk=member_id)

    # Retrieve completed payments for this member
    payments = Payment.objects.filter(member=member, status='completed').order_by('-payment_date')

    return render(request, 'staff_member_payment_details.html', {'member': member, 'payments': payments})

