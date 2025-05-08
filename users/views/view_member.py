from django.shortcuts import get_object_or_404
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from users.forms import MemberForm, MemberSelectForm

from datetime import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.utils import timezone

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from users.decorators import member_login_required

from users.models.userprofile import UserProfile
from users.models.member import Member
from users.models.attendance import Attendance
from users.models.payment import Payment
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest



@login_required
def add_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)
            member.user_profile = request.user.userprofile

            # Check for duplicate phone
            if Member.objects.filter(user_profile=member.user_profile, phone=member.phone).exists():
                existing_member = Member.objects.filter(user_profile=member.user_profile, phone=member.phone).first()
                messages.error(request, f"Member with this phone ({existing_member.name} - {existing_member.unique_number} - {existing_member.reg_no}) already exists.")

            # Check for duplicate registration number
            elif member.reg_no and Member.objects.filter(user_profile=member.user_profile, reg_no=member.reg_no).exists():
                existing_member = Member.objects.filter(user_profile=member.user_profile, reg_no=member.reg_no).first()
                messages.error(request, f"Member with this registration number ({existing_member.name} - {existing_member.unique_number} - {existing_member.reg_no}) already exists.")
            else:
                member.save()
                return redirect('member_list')
    else:
        form = MemberForm()
    return render(request, 'add_member.html', {'form': form})


@login_required
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot edit archived or personal archived member.")
        return redirect('member_detail', pk=pk)

    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            updated_member = form.save(commit=False)
            # Check if another member with the same phone exists for this UserProfile
            if Member.objects.filter(user_profile=updated_member.user_profile, phone=updated_member.phone).exclude(pk=member.pk).exists():
                messages.error(request, "A member with this phone already exists in your profile.")

            # Check if reg_no is filled and another member with the same reg_no exists for this UserProfile
            elif updated_member.reg_no and Member.objects.filter(user_profile=updated_member.user_profile, reg_no=updated_member.reg_no).exclude(pk=member.pk).exists():
                messages.error(request, "A member with this registration number already exists in your profile.")
            else:
                updated_member.save()
                return redirect('member_list')
        else:
            print(form.errors)
    else:
        form = MemberForm(instance=member)
    return render(request, 'add_member.html', {'form': form})

@login_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot delete archived or personal archived member.")
        return redirect('member_detail', pk=pk)

    if request.method == 'POST':
        member.delete()
        return redirect('member_list')
    return render(request, 'member_confirm_delete.html', {'member': member})

from django.db.models import Q
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from django.db.models import Q
from django.utils.timezone import now


@login_required
def member_list(request):
    user_profile = request.user.userprofile
    query = request.GET.get('q', '')  # Get the search query from the request
    members = Member.objects.filter(
        user_profile=user_profile,
        archived=False,
        personal_archived=False
    )

    # Get sorting parameters from the request
    sort_by = request.GET.get("sort_by", "reg_no")  # Default sort by 'reg_no'
    order = request.GET.get("order", "asc")  # Default order is 'asc'

    # Apply sorting for registration number or expiry date
    if sort_by == "expiry_date":
        if order == "asc":
            members = members.order_by("payment__expiry_date")  # Replace `payment__expiry_date` if needed
        elif order == "desc":
            members = members.order_by("-payment__expiry_date")  # Replace `payment__expiry_date` if needed
    else:
        if order == "asc":
            members = members.order_by(sort_by)
        elif order == "desc":
            members = members.order_by(f"-{sort_by}")

    # Apply the search query if present
    if query:
        members = members.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(reg_no__icontains=query) |
            Q(unique_number__icontains=query)
        )

    active_members = []
    inactive_members = []
    today = now().date()

    for member in members:
        # Assuming the most recent payment is where expiry_date is relevant
        recent_payment = member.payment_set.exclude(status='holding').order_by('-payment_date').first()
        if recent_payment and recent_payment.expiry_date >= today:
            active_members.append((member, recent_payment))
        else:
            inactive_members.append((member, recent_payment))

    context = {
        'user_profile': user_profile,
        'active_members': active_members,
        'inactive_members': inactive_members,
        'total_active_members': len(active_members),
        'total_inactive_members': len(inactive_members),
        'total_members': len(active_members) + len(inactive_members),
        'search_query': query,  # Pass the search query back to the template
        "sort_by": sort_by,
        "order": order,
        "order_for_reg_no": "asc" if order == "desc" and sort_by == "reg_no" else "desc",
        "order_for_expiry_date": "asc" if order == "desc" and sort_by == "expiry_date" else "desc",
    }
    return render(request, 'member_list.html', context)


@login_required
def archive_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        member.archived = True
        member.save()
        # Optionally, you can add a success message
        messages.success(request, 'Member archived successfully.')
    return redirect('member_detail', pk=member_id)
'''
@login_required
def personal_archive_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        member.personal_archived = True
        member.save()
        # Optionally, you can add a success message
        messages.success(request, '(personal)Member archived successfully.')
    return redirect('member_detail', pk=member_id)
'''
@login_required
def personal_archive_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        member.personal_archived = True
        member.save()
        # Optionally, you can add a success message
        messages.success(request, '(personal)Member archived successfully.')
    return redirect('member_detail', pk=member_id)


@login_required
def personal_unarchive_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        member.personal_archived = False
        member.save()
        # Optionally, you can add a success message
        messages.success(request, '(personal)Member unarchived successfully.')
    return redirect('member_detail', pk=member_id)

@login_required
def unarchive_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)

    if request.method == 'POST':
        # Transfer ownership of the member to the user who initiated the unarchive action
        member.user_profile = request.user.userprofile
        member.archived = False
        member.save()

        # Optionally, you can add a success message
        messages.success(request, 'Member unarchived and transferred to you successfully.')
        return redirect('member_detail', pk=member_id)

    # If the request method is not POST, it's likely a GET request
    # In this case, you can return a message informing the user about the action they are about to take
    messages.info(request, 'Are you sure you want to unarchive this member and transfer ownership to you?')

    # Redirect back to the member_detail page for the archived member
    return redirect('member_detail', pk=member_id)

@login_required
def member_detail(request, pk):
    # Filter member based on the current user's UserProfile
    user_profile = request.user.userprofile
    member = get_object_or_404(Member, pk=pk)

    # Check if the member is archived and allow all users to view archived members
    if member.archived:
        return render(request, 'member_detail.html', {'member': member, 'member_id': pk})

    # If the member is not archived, only allow the owner to view the details
    elif member.user_profile == user_profile:
        attendances = Attendance.objects.filter(member=member)
        payment = Payment.objects.filter(member=member).order_by('-payment_date').first()
        return render(request, 'member_detail.html', {'member': member, 'attendances': attendances, 'payment': payment, 'member_id': pk})

    # If the member is not archived and the user is not the owner, return a permission denied message or redirect
    else:
        # You can customize this part based on your requirements, like showing a permission denied message or redirecting
        return HttpResponse("Permission Denied")

'''
@login_required
def personal_unarchive_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == 'POST':
        member.personal_archived = False
        member.save()
        # Optionally, you can add a success message
        messages.success(request, '(personal)Member unarchived successfully.')
    return redirect('member_detail', pk=member_id)
'''
@login_required
def personal_archive_list(request):
    user_profile = request.user.userprofile
    personal_archived_members = Member.objects.filter(user_profile=user_profile, personal_archived=True)
    return render(request, 'personal_archive_list.html', {'personal_archived_members': personal_archived_members})

@login_required
def archive_list(request):
    archived_members = Member.objects.filter(archived=True)
    return render(request, 'archive_list.html', {'archived_members': archived_members})

from django.views import View
from django.contrib.auth.hashers import check_password

class MemberLogin(View):
    def get(self, request):
        return render(request, 'memberlogin.html')

    def post(self, request):
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        error_message = None

        if not phone or not password:
            error_message = "Please fill out all fields."
        else:
            members = Member.objects.filter(phone=phone)
            if members.exists():
                # Attempt to authenticate each member
                for member in members:
                    if member.check_password(password):
                        request.session['member_id'] = member.id
                        return redirect('memberdashboard', member_id=member.id)
                error_message = "Invalid password for the provided phone."
            else:
                error_message = "Member not found with this phone."

        data = {
            'error': error_message,
            'phone': phone
        }
        return render(request, 'memberlogin.html', data)


def memberlogout(request):
    request.session.clear()
    return redirect('memberlogin')




@member_login_required
def memberdashboard(request, member_id):
    # Get the member object based on the provided member_id
    member = get_object_or_404(Member, pk=member_id)

    # Retrieve associated user profiles
    user_profiles = UserProfile.objects.filter(members=member)

    # Get attendance records for the member
    attendances = Attendance.objects.filter(member=member).order_by('-date')

    # Get the most recent payment details for the member, if available
    payment = Payment.objects.filter(member=member).order_by('-payment_date').first()

    context = {
        'member': member,
        'user_profiles': user_profiles,
        'attendances': attendances,
        'payment': payment,
    }

    return render(request, 'memberdashboard.html', context)



'''

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import qrcode
from io import BytesIO
from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from PIL import Image, ImageDraw, ImageFont
#from PIL import Image as PilImage, ImageDraw, ImageFont

import qrcode

@login_required
def generate_qr_code(request, member_id):
    user_profile = request.user.userprofile
    member = get_object_or_404(Member, pk=member_id, user_profile=user_profile)

    # Generate the full URL for the member detail page
    qr_data = request.build_absolute_uri(f"/members/{member_id}/")  # Full URL for the member detail page

    # Create a QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Generate the QR code image
    qr_img = qr.make_image(fill='black', back_color='white').convert('RGB')

    # Set up a larger image with space for the text below the QR code
    qr_width, qr_height = qr_img.size
    total_height = qr_height + 100  # Adding space for the text below (adjust as necessary)

    # Create a new blank image (white background) large enough for the QR code and text
    final_img = Image.new('RGB', (qr_width, total_height), 'white')

    # Paste the QR code onto the new image (at the top)
    final_img.paste(qr_img, (0, 0))

    # Add custom text below the QR code (member.name, member.number, and userprofile.username)
    draw = ImageDraw.Draw(final_img)

    # Load a default font or a specific one (Pillow may require a .ttf font file path)
    font = ImageFont.load_default()  # You can use a custom font if desired

    # Prepare the text content
    text = f"{user_profile.user.username}\nName: {member.name}\nNumber: {member.unique_number}\n "

    # Define where the text will be positioned (below the QR code)
    text_position = (10, qr_height + 10)  # Position it slightly below the QR code

    # Draw the text onto the image
    draw.text(text_position, text, font=font, fill='black')

    # Save the image to a buffer
    buffer = BytesIO()
    final_img.save(buffer, format='PNG')
    buffer.seek(0)

    # Send the image as an HTTP response
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="member_{member_id}_qr.png"'
    return response

'''
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import qrcode
from io import BytesIO
from PIL import Image as PilImage, ImageDraw, ImageFont  # Renamed import

@login_required
def generate_qr_code(request, member_id):
    user_profile = request.user.userprofile
    member = get_object_or_404(Member, pk=member_id, user_profile=user_profile)

    # Generate the full URL for the member detail page
    qr_data = request.build_absolute_uri(f"/members/{member_id}/")  # Full URL for the member detail page

    # Create a QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Generate the QR code image
    qr_img = qr.make_image(fill='black', back_color='white').convert('RGB')

    # Set up a larger image with space for the text and decorations
    qr_width, qr_height = qr_img.size
    padding = 30  # Space around the QR code
    text_height = 100  # Space reserved for text
    total_height = qr_height + text_height + padding * 2  # Add padding around the QR code and text

    # Create a new blank image (white background) large enough for the QR code, padding, and text
    final_img = PilImage.new('RGB', (qr_width + padding * 2, total_height), 'white')  # Using PilImage.new()

    # Paste the QR code onto the new image (with padding)
    final_img.paste(qr_img, (padding, padding))

    # Add a border around the QR code for decoration
    draw = ImageDraw.Draw(final_img)
    border_color = 'black'
    draw.rectangle(
        [padding - 10, padding - 10, padding + qr_width + 10, padding + qr_height + 10],
        outline=border_color,
        width=5  # Border thickness
    )

    # Add custom text below the QR code (member.name, member.number, and userprofile.username)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Change this to a valid .ttf font path on your server
    font = ImageFont.truetype(font_path, size=24)  # Using a larger font size

    # Prepare the text content
    text = f"{user_profile.user.username}\nName: {member.name}\nID: {member.unique_number}"

    # Define the text size and position (center-aligned)
    text_width, _ = draw.textsize(text, font=font)
    text_position = ((qr_width + padding * 2 - text_width) // 2, qr_height + padding + 10)  # Centered text below QR code

    # Draw the text onto the image
    draw.text(text_position, text, font=font, fill='black')

    # Save the image to a buffer
    buffer = BytesIO()
    final_img.save(buffer, format='PNG')
    buffer.seek(0)

    # Send the image as an HTTP response
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="member_{member_id}_qr.png"'
    return response

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

@login_required
def scan_qr_code(request):
    return render(request, 'scan_qr_code.html')



from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak  # Import PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.utils import ImageReader
from django.conf import settings
import os
from reportlab.platypus import Image  # Import the Image class from platypus
from reportlab.lib.units import inch  # For setting the image size

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image  # Correct import
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.http import HttpResponse
import os
from django.conf import settings

@login_required
def generate_member_report_pdf(request):
    # Query all members under the user profile
    user_profile = request.user.userprofile
    members = Member.objects.filter(user_profile=user_profile, personal_archived=False)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="member_report.pdf"'

    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    centered_style = styles['Heading2']
    centered_style.alignment = 1  # Center alignment
    normal_style = styles['BodyText']

    # Iterate over members
    for member in members:
        elements.append(Paragraph(f"Member : {member.name}", centered_style))
        elements.append(Paragraph(f"ID : {member.unique_number}", centered_style))
        elements.append(Paragraph(f"Reg No : {member.reg_no}", centered_style))

        elements.append(Spacer(1, 0.2 * inch))

        # Add member image if it exists
        if member.image:
            image_path = os.path.join(settings.MEDIA_ROOT, str(member.image))
            if os.path.exists(image_path):
                elements.append(Image(image_path, width=2 * inch, height=2 * inch))  # Correct use of Image

        elements.append(Spacer(1, 0.2 * inch))

        # Member details section
        elements.append(Paragraph("<b>Member Details</b>", styles['Heading3']))
        data = [
            ['Name', member.name],
            ['Gender', member.gender],
            ['Phone', member.phone],
            ['Email', member.email],
            ['DOB', member.DOB.strftime("%d-%m-%Y")],
            ['Medical History', member.medical_history],
            ['Registration Date', member.registration_date.strftime("%d-%m-%Y")],
            ['Address', member.address],
        ]
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))

        # Payment details section
        payments = Payment.objects.filter(member=member)
        elements.append(Paragraph("<b>Payment History</b>", styles['Heading3']))
        if payments.exists():
            data = [['Payment Type', 'Amount', 'Payment Date', 'Expiry Date']]
            for payment in payments:
                data.append([payment.payment_type, payment.amount, payment.payment_date.strftime("%d-%m-%Y"), payment.expiry_date.strftime("%d-%m-%Y")])
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No payment history available.", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Add space between members or add new page
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("<b>------------------------------------</b>", centered_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Page break between members
        elements.append(PageBreak())

    # Build the PDF document
    doc.build(elements)
    return response



@login_required
def archived_generate_member_report_pdf(request):
    # Query all members under the user profile
    user_profile = request.user.userprofile
    members = Member.objects.filter(user_profile=user_profile, personal_archived=True)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="member_report.pdf"'

    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    centered_style = styles['Heading2']
    centered_style.alignment = TA_CENTER
    normal_style = styles['BodyText']

    # Iterate over members
    for member in members:
        # Member header section
        elements.append(Paragraph(f"Member : {member.name}", centered_style))
        elements.append(Paragraph(f"ID : {member.unique_number}", centered_style))
        elements.append(Paragraph(f"Reg No : {member.reg_no}", centered_style))

        elements.append(Spacer(1, 0.2 * inch))

        # Member details section
        elements.append(Paragraph("<b>Member Details</b>", styles['Heading3']))
        data = [
            ['Name', member.name],
            ['Gender', member.gender],
            ['Phone', member.phone],
            ['Email', member.email],
            ['DOB', member.DOB.strftime("%d-%m-%Y")],
            ['Medical History', member.medical_history],
            ['Registration Date', member.registration_date.strftime("%d-%m-%Y")],
            ['Address', member.address],
        ]
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))

        # Payment details section
        payments = Payment.objects.filter(member=member)
        elements.append(Paragraph("<b>Payment History</b>", styles['Heading3']))
        if payments.exists():
            data = [['Payment Type', 'Amount', 'Payment Date']]
            for payment in payments:
                data.append([payment.payment_type, payment.amount, payment.payment_date.strftime("%d-%m-%Y")])
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No payment history available.", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Attendance details section

     # attendances = Attendance.objects.filter(member=member)
       # elements.append(Paragraph("<b>Attendance History</b>", styles['Heading3']))
        #if attendances.exists():
         #   data = [['Date', 'Time In', 'Time Out']]
           # for attendance in attendances:
               # data.append([attendance.date.strftime("%Y-%m-%d"), attendance.time_in, attendance.time_out])
           # table = Table(data)
           # table.setStyle(TableStyle([
               # ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
               # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
               # ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
              #  ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
              #  ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
              #  ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
              #  ('GRID', (0, 0), (-1, -1), 1, colors.black),
            #]))
           # elements.append(table)
        ##else:
            #elements.append(Paragraph("No attendance records available.", normal_style))


        # Add space between members or add new page
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("<b>------------------------------------</b>", centered_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Page break between members
        elements.append(PageBreak())

    # Build the PDF document
    doc.build(elements)
    return response

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

@login_required
def generate_member_card(request, member_id):
    # Get the member object
    member = get_object_or_404(Member, id=member_id)
    user_profile = request.user.userprofile

    # Create a PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="member_card_{member.name}.pdf"'

    # Create a byte buffer for PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Add title (centered)
    title_style = styles['Heading1']
    title_style.alignment = TA_CENTER
    title = Paragraph(user_profile.user.username, title_style)
    elements.append(title)

    # Add location (centered, new line at commas)
    location_style = styles['Normal']
    location_style.alignment = TA_CENTER
    location_text = user_profile.location.replace(', ', ',<br/>')
    location = Paragraph(location_text, location_style)
    elements.append(location)

    elements.append(Spacer(1, 20))  # Space between title and QR code

    # Generate QR code
    qr_data = request.build_absolute_uri(f"/members/{member_id}/")
    qr_img = qrcode.make(qr_data)

    # Save QR code to a BytesIO object
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Add QR code to the PDF (make it larger)
    qr_code_img = Image(qr_buffer, 150, 150)  # Increased size of QR code
    elements.append(qr_code_img)

    elements.append(Spacer(1, 20))  # Space between QR and member details

    # Check if member has an image, if not, create a default icon
    if member.image:
        member_img = PilImage.open(member.image.path)
        member_img = member_img.resize((100, 100), PilImage.ANTIALIAS)  # Resize the image
    else:
        # Create a default profile icon
        member_img = create_default_icon()

    # Save member image to BytesIO (convert to round)
    member_buffer = BytesIO()
    member_img = make_round_image(member_img)  # Create a round profile picture
    member_img.save(member_buffer, format='PNG')
    member_buffer.seek(0)

    # Add member image to the PDF (positioned in the right corner)
    member_image_pdf = Image(member_buffer, 70, 70)  # Smaller member image size
    member_image_pdf.hAlign = 'RIGHT'  # Align to right
    elements.append(member_image_pdf)

    elements.append(Spacer(1, 20))  # Space before member details

    # Create a table with all member details
    data = [
        ['ID', member.unique_number],  # Header
        ['Name', member.name],
        ['Email', member.email or 'N/A'],
        ['Phone', member.phone or 'N/A'],
        ['Emergency Number', member.emergency_number or 'N/A'],
        ['Registration No', member.reg_no or 'N/A'],
        ['Gender', member.get_gender_display()],
        ['Date of Birth', member.DOB or 'N/A'],
        ['Address', member.address or 'N/A'],
    ]

    # Add table with some styling
    table = Table(data, colWidths=[120, 280])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Build the PDF document
    doc.build(elements)

    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response

def create_default_icon():
    """Create a default profile icon as an image with a better design."""
    # Create a blank image with a transparent background
    icon_size = (100, 100)
    icon = PilImage.new('RGBA', icon_size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(icon)

    # Draw a more stylized head and shoulders silhouette
    head_color = (70, 130, 180)  # Steel blue color
    shoulder_color = (100, 149, 237)  # Cornflower blue color

    # Head
    draw.ellipse((30, 10, 70, 50), fill=head_color)  # Head
    # Shoulders
    draw.rectangle((20, 50, 80, 100), fill=shoulder_color)  # Shoulders

    return icon

def make_round_image(image):
    """Convert a PIL Image to a round image."""
    # Create a mask for the image
    mask = PilImage.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + image.size, fill=255)

    # Apply the mask to the image
    round_image = PilImage.new('RGBA', image.size)
    round_image.paste(image, (0, 0), mask)
    return round_image

