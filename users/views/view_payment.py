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
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import user_passes_test
from users.forms import MemberForm, PaymentForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from datetime import date, timedelta
from users.models.attendance import Attendance
from users.models.userprofile import UserProfile
from users.models.payment import Payment
from users.models.member import Member
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

@login_required
def add_payment(request, member_id):
    member = get_object_or_404(Member, pk=member_id, user_profile=request.user.userprofile)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot add payment to archived or personal archived member.")
        return redirect('member_detail', pk=member_id)

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
            return redirect('member_detail', pk=member_id)
    else:
        form = PaymentForm()
    return render(request, 'add_payment.html', {'form': form, 'member': member})

@login_required
def payment_holding_list(request):
    payments = Payment.objects.filter(status='holding', member__user_profile=request.user.userprofile)
    return render(request, 'payment_holding_list.html', {'payments': payments})

@login_required
def mark_payment_complete(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, member__user_profile=request.user.userprofile)
    payment.status = 'completed'
    payment.save()
    return redirect('payment_holding_list')

@login_required
def payment_list_all(request):
    user_profile = request.user.userprofile

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
        payments = Payment.objects.filter(
            member__user_profile=user_profile,
            payment_date__range=(start_date, end_date),
            status='completed'
        ).order_by('member', '-payment_date')
        total_payment = payments.aggregate(Sum('amount'))['amount__sum']
    else:
        payments = Payment.objects.filter(
            member__user_profile=user_profile,
            status='completed'
        ).order_by('member', '-payment_date')
        total_payment = None

    members = Member.objects.filter(user_profile=user_profile).distinct().order_by('name')

    context = {
        'payments': payments,
        'members': members,
        'start_date': start_date,
        'end_date': end_date,
        'total_payment': total_payment,
    }

    if request.GET.get('format') == 'pdf':
        return payment_list_all_pdf(request, context)
    elif request.GET.get('format') == 'excel':
        return generate_excel_payment_list_all(context)

    return render(request, 'payment_list_all.html', context)


@login_required
def member_payment_details(request, member_id):
    member = get_object_or_404(Member, pk=member_id, user_profile=request.user.userprofile)

    if member.archived or member.personal_archived:
        messages.error(request, "Cannot view payment details for archived or personal archived member.")
        return redirect('member_detail', pk=member_id)

    payments = Payment.objects.filter(member=member, status='completed').order_by('-payment_date')

    return render(request, 'member_payment_details.html', {'member': member, 'payments': payments})











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
def generate_pdf_receipt(request, payment_id, member_id):
    # Retrieve payment details
    payment = get_object_or_404(Payment, pk=payment_id)
    user_profile = payment.member.user_profile

    # Ensure the receipt_id is generated and saved
    if payment.receipt_id is None:
        payment.save()

    # Create PDF document
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.receipt_id}.pdf"'

    # Define custom receipt size
    receipt_width, receipt_height = 210 * mm, 297 * mm  # Example size, adjust as needed

    # Create PDF document with custom size
    doc = SimpleDocTemplate(response, pagesize=(receipt_width, receipt_height))

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = 1  # Center alignment
    detail_style = styles["Normal"]
    detail_style.alignment = 1
    centered_style = ParagraphStyle(name='Centered', fontSize=10,alignment=1)

    # Create elements list
    elements = []

    # Add title and details with spacing
    elements.append(Paragraph(user_profile.user.username, title_style))
    elements.append(Spacer(1, 6))  # Spacer for spacing
    location_parts = user_profile.location.split(',')
    for part in location_parts:
        elements.append(Paragraph(part.strip(), centered_style))

    elements.append(Spacer(1, 24))   # Larger spacer before the table

    # Create data for the table
    data = [
       # ["Receipt ID:", f"{payment.receipt_id}"],
        ["Payment ID:", f"{payment.pay_id}"],
        ["Member:", f"{payment.member.name}"],
        ["ID Number:", f"{payment.member.unique_number}"],
        ["Batch:", f"{payment.batch}"],
        ["Payment Type:", f"{payment.payment_type}"],
        ["Amount:", f"Rs: {payment.amount}"],
        ["Expiry Date:", f"{payment.expiry_date.strftime('%B %d, %Y')}"],
        ["Payment Date:", f"{payment.payment_date.strftime('%B %d, %Y')}"],
    ]

    # Create a table and set its style
    table = Table(data, colWidths=[50 * mm, 80 * mm])  # Adjust colWidths as needed
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # Set font size
    ]))

    # Add the table to the elements list
    elements.append(table)

    # Add a blank line for spacing
    elements.append(Spacer(1, 12))

    # Add decorative elements
    elements.append(Spacer(1, 12))  # Spacer for additional spacing

    # Add "Generated Signature"
    unique_code = random.randint(1000, 9999)
    unique_code_style = ParagraphStyle(name='UniqueCode', fontSize=6)
    unique_code_paragraph = Paragraph(str(unique_code), unique_code_style)
    elements.append(unique_code_paragraph)

    # Add footer with current date
    current_date = datetime.now().strftime("%B %d, %Y")
    elements.append(Spacer(1, 12))  # Spacer for spacing before footer
    elements.append(Paragraph(f"Issued on: {current_date}", styles['Normal']))
    elements.append(Paragraph("Use this QR code to easily check in, check out, and access your member details in our system!", styles['Normal']))
 # Generate QR code
    qr_data = request.build_absolute_uri(f"/members/{member_id}/")
    qr_img = qrcode.make(qr_data)

    # Save QR code to a BytesIO object
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Add QR code to the PDF (make it larger)
    qr_code_img = Image(qr_buffer, 250, 250)  # Increased size of QR code
    elements.append(qr_code_img)
    # Build the PDF document
    doc.build(elements)

    return response



@login_required
def payment_list_all_pdf(request, context):
    start_date = context['start_date']
    end_date = context['end_date']

    if start_date and end_date:
        payments = context['payments']
        total_payment = context['total_payment']

        # Create PDF document
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="payment_list_all.pdf"'

        # Create PDF content
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        title = Paragraph("<b>Payment List - All Members</b>", title_style)
        elements.append(title)

        # Table data
        data = []
        for payment in payments:
            data.append([payment.pay_id, payment.member.name, payment.payment_type, str(payment.amount), payment.payment_date.strftime('%Y-%m-%d')])

        # Column headers
        column_headers = ["payment ID","Member Name", "Payment Type", "Amount", "Payment Date"]
        data.insert(0, column_headers)

        # Create table
        table = Table(data)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                   ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                   ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                   ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                   ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                   ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                   ('GRID', (0, 0), (-1, -1), 1, colors.black)]))

        elements.append(table)

        # Total payment
        if total_payment:
            total = f"<b>Total Payment: Rs {total_payment}</b>"
            total_paragraph = Paragraph(total)
            elements.append(total_paragraph)

        # Footer with current date
        current_date = datetime.now().strftime("%B %d, %Y")
        footer = f"Issued on: {current_date}"
        footer_paragraph = Paragraph(footer)
        elements.append(footer_paragraph)

        doc.build(elements)

        return response
    else:
        return HttpResponseBadRequest("Please provide both start_date and end_date.")

import csv

def generate_excel_payment_list_all(context):
    # Generate Excel file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payment_list_all.csv"'

    # Write CSV content
    writer = csv.writer(response)
    writer.writerow(['payment ID','Member', 'Payment Type', 'Amount', 'Payment Date'])

    total_payment = context.get('total_payment')
    if total_payment is not None:
        writer.writerow(['Total Payment', total_payment])

    for payment in context['payments']:
        writer.writerow([payment.pay_id, payment.member.name, payment.payment_type, payment.amount, payment.payment_date])

    return response

from users.forms import PaymentEditForm

@login_required
def edit_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, member__user_profile=request.user.userprofile)

    if request.method == 'POST':
        form = PaymentEditForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            return redirect('member_payment_details', member_id=payment.member.id)
    else:
        form = PaymentEditForm(instance=payment)

    return render(request, 'edit_payment.html', {'form': form, 'payment': payment})
