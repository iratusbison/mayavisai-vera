import datetime
from django.shortcuts import render, redirect, get_object_or_404
from users.models.booking import Room, Booking, UserProfile
from datetime import datetime, timedelta
from django.db.models import Sum
from django.utils import timezone as djtimezone
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from reportlab.lib.pagesizes import letter, A4
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from django.utils.timezone import make_aware
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm



@login_required
def add_room(request):
    if request.method == 'POST':
        room_number = request.POST.get('room_number')
        Room.objects.create(
            room_number=room_number,
            user_profile=request.user.userprofile,
        )
        return redirect('room_list')
    return render(request, 'room_add.html')

@login_required(login_url='/login')
def room_list(request):
    user_profile = request.user.userprofile
    rooms = Room.objects.filter(user_profile = user_profile)
    now = djtimezone.now()
    for room in rooms:
        bookings = Booking.objects.filter(rooms=room, checkout_datetime__gte=now)
        if bookings.exists():
            room.is_available = False
            room.booking = bookings.first()
        else:
            room.is_available = True
            room.booking = None
    return render(request, 'room_list.html', {'rooms': rooms, 'now': now})



@login_required(login_url='/login')
def book_room(request):
    # Ensure the user has an associated UserProfile
    try:
        user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        error_message = "You don't have permission to book rooms. Please contact support."
        return render(request, 'error_page.html', {'error': error_message})

    # Fetch rooms that belong to the current user's profile
    rooms = Room.objects.filter(user_profile=user_profile)

    if request.method == 'POST':
        # Get form data
        room_ids = request.POST.getlist('rooms')  # Get selected room IDs from the form
        checkin_datetime = request.POST.get('checkin_datetime')
        checkout_datetime = request.POST.get('checkout_datetime')
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        aadhar = request.POST.get('aadhar')
        price = request.POST.get('price') or 0  # Default to 0 if blank
        other_charges = request.POST.get('other_charges') or 0  # Default to 0 if blank
        persons = request.POST.get('persons')
        reason = request.POST.get('reason')
        payment = request.POST.get('payment')

        # Validate required fields before entering the transaction
        if not room_ids:
            error_message = 'You must select at least one room to proceed with the booking.'
            return render(request, 'book_room.html', {'rooms': rooms, 'error': error_message})

        if not name or not checkin_datetime or not checkout_datetime:
            error_message = 'Please fill in all required fields.'
            return render(request, 'book_room.html', {'rooms': rooms, 'error': error_message})

        if checkout_datetime <= checkin_datetime:
            error_message = 'Invalid date range: Check-out date must be after check-in date.'
            return render(request, 'book_room.html', {'rooms': rooms, 'error': error_message})

        try:
            # Use atomic transaction for database operations
            with transaction.atomic():
                # Create the booking object
                booking = Booking.objects.create(
                    user_profile=user_profile,
                    name=name,
                    address=address,
                    phone=phone,
                    aadhar=aadhar,
                    price=price,
                    other_charges=other_charges,
                    email=email,
                    persons=persons,
                    reason=reason,
                    payment=payment,
                    checkin_datetime=checkin_datetime,
                    checkout_datetime=checkout_datetime,
                )

                # List to store rooms that are already booked
                conflicting_rooms = []

                # Iterate through selected rooms and check availability
                for room_id in room_ids:
                    room = Room.objects.get(id=room_id, user_profile=user_profile)

                    # Check if the room is already booked for the given date range
                    existing_bookings = Booking.objects.filter(
                        rooms=room,
                        user_profile=user_profile,
                        checkout_datetime__gte=checkin_datetime,
                        checkin_datetime__lte=checkout_datetime
                    )
                    if existing_bookings.exists():
                        conflicting_rooms.append(room.room_number)

                    # Add the room to the booking if no conflict
                    booking.rooms.add(room)

                # If there are conflicting rooms, show an error and rollback the transaction
                if conflicting_rooms:
                    booking.delete()  # Rollback the booking
                    error_message = f'The following rooms are already booked: {", ".join(map(str, conflicting_rooms))}'
                    return render(request, 'book_room.html', {'rooms': rooms, 'error': error_message})

                # Mark rooms as unavailable after successful booking
                for room_id in room_ids:
                    room = Room.objects.get(id=room_id, user_profile=user_profile)
                    room.is_available = False
                    room.save()

                # If everything succeeds, redirect to booking detail
                return redirect('booking_detail', booking_id=booking.user_specific_id)

        except ValueError as ve:
            # Handle invalid values (e.g., non-numeric aadhar)
            error_message = f'Invalid value encountered: {str(ve)}'
            return render(request, 'book_room.html', {'rooms': rooms, 'error': error_message})

        except Exception as e:
            # Handle any other unexpected errors
            error_message = f'An error occurred during the booking process: {str(e)}'
            return render(request, 'book_room.html', {'rooms': rooms, 'error': error_message})

    else:
        # If GET request, simply render the available rooms for selection
        return render(request, 'book_room.html', {'rooms': rooms})


@login_required(login_url='/login')
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, user_specific_id=booking_id, user_profile=request.user.userprofile)
    rooms = booking.rooms.all()
    price = booking.price
    other_charges = booking.other_charges
    total_charges = Decimal(other_charges or 0) + price

    gst_amount = price - (price / (1 + Decimal('0.12')))
    net_price = price - gst_amount
    gst = price * Decimal('0.12')
    total_price = price + gst

    return render(request, 'booking_detail.html', {
        'booking': booking,
        'rooms': rooms,
        'price': price,
        'gst': gst,
        'gst_amount': gst_amount,
        'total_charges': total_charges,
        'net_price': net_price,
        'total_price': total_price,
        'reason': booking.reason,
    })

@login_required(login_url='/login')
def edit_booking(request, booking_id):
    user_profile = request.user.userprofile
    booking = get_object_or_404(Booking, user_specific_id=booking_id, user_profile=user_profile)
    rooms = booking.rooms.filter(user_profile=user_profile)
    if request.method == 'POST':
        booking.checkin_datetime = request.POST.get('checkin_datetime')
        booking.checkout_datetime = request.POST.get('checkout_datetime')
        booking.name = request.POST.get('name')
        booking.address = request.POST.get('address')
        booking.phone = request.POST.get('phone')
        booking.aadhar = request.POST.get('aadhar')
        booking.email = request.POST.get('email')
        booking.price = request.POST.get('price')
        booking.other_charges = request.POST.get('other_charges')

        booking.save()
        return redirect('booking_detail', booking_id=booking_id)
    else:
        return render(request, 'edit_booking.html', {'booking': booking, 'rooms': rooms})


@login_required(login_url='/login')
def delete_booking(request, booking_id):
    user_profile = request.user.userprofile
    booking = get_object_or_404(Booking, user_specific_id=booking_id, user_profile=user_profile)
    rooms = booking.rooms.all()
    for room in rooms:
        room.is_available = True
        room.save()
    booking.delete()
    return redirect('room_list')



from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from io import BytesIO
from django.http import HttpResponse

from django.utils.timezone import make_aware

from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from django.http import HttpResponse
from django.utils.timezone import make_aware, timezone

from decimal import Decimal
@login_required(login_url='/login')
def generate_pdf_book(request):
    # Check if a date range is provided in the request
    checkin_datetime = request.GET.get('checkin_datetime', '')
    checkout_datetime = request.GET.get('checkout_datetime', '')

    # Default to the last 30 days if no date range is provided
    if not checkin_datetime or not checkout_datetime:
        checkout_datetime = timezone.now()
        checkin_datetime = checkout_datetime - timedelta(days=30)
    else:
        checkin_datetime = make_aware(datetime.strptime(checkin_datetime, '%Y-%m-%d'))
        checkout_datetime = make_aware(datetime.strptime(checkout_datetime, '%Y-%m-%d'))

    # Filter bookings based on the provided date range
    bookings = Booking.objects.filter(checkin_datetime__range=(checkin_datetime, checkout_datetime))

    buffer = BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    # Add title to the PDF with decoration
    title_text = f"Booking List ({checkin_datetime.date()} to {checkout_datetime.date()})"
    title = Paragraph(title_text, styles["Title"])
    title.alignment = 1  # Center alignment
    elements.append(title)
    '''
    # Add SV Mahal / AKS Inn to the top center
    elements.append(Paragraph("SV Mahal / AKS Inn", styles["Heading2"]))
    elements.append(Paragraph("No.192/1A 1B, Vandavasi Road, Sevilimedu, Kanchipuram - 631502", styles["BodyText"]))
    elements.append(Paragraph("Phone: 9842254415, 9443733265, 9994195966", styles["BodyText"]))
    elements.append(Paragraph("Email: svmahalaksinn@gmail.com", styles["BodyText"]))
    elements.append(Paragraph("GST: 33ADDFS68571Z8", styles["BodyText"]))
    elements.append(Paragraph("<br/><br/>", normal_style))  # Add space between address and table
    '''

    # Define data for the table
    data = [['ID', 'Name', 'Phone', 'Aadhar', 'Price', 'GST', 'Net Price']]

    total_revenue = Decimal('0.00')

    for booking in bookings:
        # Calculate GST and total price
        price = booking.price
        gst = price * Decimal('0.12')
        total_price = price + gst

        gst_amount = booking.price * Decimal('0.12')
        net_price = booking.price - gst_amount

        # Append booking details to the data list
        data.append([
            booking.user_specific_id,
            booking.name,
            booking.phone,
            booking.aadhar,
            price,
            gst,
            net_price,
        ])

        # Increment total revenue
        total_revenue += price

    if len(data) == 1:
        data.append(['No bookings found', '', '', '', '', '', ''])  # If no bookings found, add a message row

    # Create the table
    table = Table(data)

    # Define style for the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    # Apply style to the table
    table.setStyle(style)
    elements.append(table)
    elements.append(Paragraph(f"Total Revenue: {total_revenue}", styles["Normal"]))

    # Build the PDF

    buffer.seek(0)
    # Build the PDF
    doc.build(elements)
    buffer.seek(0)

    # Create the HTTP response with PDF mime type
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="booking_list.pdf"'

    return response



from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.http import HttpResponse
from django.utils.timezone import localtime
from decimal import Decimal
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from django.utils.timezone import localtime
from reportlab.lib.units import inch

@login_required(login_url='/login')
def generate_bill(request, booking_id):
    buffer = BytesIO()

    # Retrieve booking details
    booking = Booking.objects.get(id=booking_id)
    checkin_datetime_local = localtime(booking.checkin_datetime)
    checkout_datetime_local = localtime(booking.checkout_datetime)

    # Create a PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = 1  # Center alignment
    detail_style = styles["Normal"]

    # Content for the PDF
    content = []  # Main content list that will be passed to doc.build()

    # Add SV Mahal/Aksinn Topic and Address, Email, Phone
    '''
    content.append(Paragraph(user_profile.user.username, title_style))
    content.append(Paragraph("No.192/1A 1B, Vandavasi Road, Sevilimedu, Kanchipuram - 631502", detail_style))
    content.append(Paragraph("Phone: 9842254415, 9443733265, 9994195966 ", detail_style))
    content.append(Paragraph("Email: svmahalaksinn@gmail.com", detail_style))
    content.append(Paragraph("GST: 33ADDFS68571Z8", detail_style))
    '''
    user_profile = booking.user_profile

    # Add title and details with spacing
    content.append(Paragraph(user_profile.user.username, title_style))
    content.append(Spacer(1, 6))  # Spacer for spacing
    location_parts = user_profile.location.split(',')
    for part in location_parts:
        content.append(Paragraph(part.strip(), detail_style))

    content.append(Spacer(1, 24))  # Larger spacer before the table

    # Add title
    content.append(Paragraph("Booking Bill", title_style))
    total_charges = Decimal(booking.price or 0) + Decimal(booking.other_charges or 0)

    # Add booking details
    booking_details = [
        ["Booking ID:", str(booking.user_specific_id)],
        ["Check-in Date:", str(checkin_datetime_local)],
        ["Check-out Date:", str(checkout_datetime_local)],
        ["Name:", booking.name],
        ['Address', "\n".join(booking.address.split(','))],
        ["Phone:", booking.phone],
        ["Aadhar:", booking.aadhar],
        ["Price:", str(booking.price)],
        ["Other Charges:", str(booking.other_charges)],
        ["Total Price:", total_charges],
        ["Email:", booking.email],
        ["Persons:", str(booking.persons)],
        ["Reason:", booking.reason],
    ]

    room_numbers = [room.room_number for room in booking.rooms.all()]
    room_lines = [", ".join(room_numbers[i:i+5]) for i in range(0, len(room_numbers), 5)]
    room_numbers_text = "\n".join(room_lines)

    booking_details.append(["Room Numbers:", room_numbers_text])

    # Add booking details to table
    booking_table = Table(booking_details, colWidths=[2*inch, 4*inch])
    booking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # Increase font size
        ('TOPPADDING', (0, 0), (-1, -1), 8),  # Add padding to the cells
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    content.append(booking_table)




    # Set up a rounding format for two decimal places
    two_places = Decimal('0.01')

    # Calculate GST and net price using a similar method as the first example
    gst_amount = (booking.price - (booking.price / (1 + Decimal('0.12')))).quantize(two_places, rounding=ROUND_HALF_UP)
    net_price = (booking.price - gst_amount).quantize(two_places, rounding=ROUND_HALF_UP)

    # Add GST and net price to content
    content.append(Paragraph(f"GST (12%): {gst_amount}", detail_style))
    content.append(Paragraph(f"Net Price: {net_price}", detail_style))

    # Build the PDF
    doc.build(content)



    # Return the buffer content as HTTP response
    pdf = buffer.getvalue()
    buffer.close()

    # Create HTTP response with PDF content
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking_bill_{booking.id}.pdf"'
    return response



#@login_required(login_url='/login')
def client_generate_bill(request, booking_id):
    buffer = BytesIO()

    # Retrieve booking details
    booking = Booking.objects.get(id=booking_id)
    checkin_datetime_local = localtime(booking.checkin_datetime)
    checkout_datetime_local = localtime(booking.checkout_datetime)

    # Create a PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = 1  # Center alignment
    detail_style = styles["Normal"]

    # Content for the PDF
    content = []  # Main content list that will be passed to doc.build()

    # Add SV Mahal/Aksinn Topic and Address, Email, Phone
    '''
    content.append(Paragraph(user_profile.user.username, title_style))
    content.append(Paragraph("No.192/1A 1B, Vandavasi Road, Sevilimedu, Kanchipuram - 631502", detail_style))
    content.append(Paragraph("Phone: 9842254415, 9443733265, 9994195966 ", detail_style))
    content.append(Paragraph("Email: svmahalaksinn@gmail.com", detail_style))
    content.append(Paragraph("GST: 33ADDFS68571Z8", detail_style))
    '''
    user_profile = booking.user_profile

    # Add title and details with spacing
    content.append(Paragraph(user_profile.user.username, title_style))
    content.append(Spacer(1, 6))  # Spacer for spacing
    location_parts = user_profile.location.split(',')
    for part in location_parts:
        content.append(Paragraph(part.strip(), detail_style))

    content.append(Spacer(1, 24))  # Larger spacer before the table

    # Add title
    content.append(Paragraph("Booking Bill", title_style))
    total_charges = Decimal(booking.price or 0) + Decimal(booking.other_charges or 0)

    # Add booking details
    booking_details = [
        ["Booking ID:", str(booking.user_specific_id)],
        ["Check-in Date:", str(checkin_datetime_local)],
        ["Check-out Date:", str(checkout_datetime_local)],
        ["Name:", booking.name],
        ['Address', "\n".join(booking.address.split(','))],
        ["Phone:", booking.phone],
        ["Aadhar:", booking.aadhar],
        ["Price:", str(booking.price)],
        ["Other Charges:", str(booking.other_charges)],
        ["Total Price:", total_charges],
        ["Email:", booking.email],
        ["Persons:", str(booking.persons)],
        ["Reason:", booking.reason],
    ]

    room_numbers = [room.room_number for room in booking.rooms.all()]
    room_lines = [", ".join(room_numbers[i:i+5]) for i in range(0, len(room_numbers), 5)]
    room_numbers_text = "\n".join(room_lines)

    booking_details.append(["Room Numbers:", room_numbers_text])

    # Add booking details to table
    booking_table = Table(booking_details, colWidths=[2*inch, 4*inch])
    booking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # Increase font size
        ('TOPPADDING', (0, 0), (-1, -1), 8),  # Add padding to the cells
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    content.append(booking_table)

    # Calculate GST and net price
    gst_amount = booking.price * Decimal('0.12')
    net_price = booking.price - gst_amount

    # Add GST and net price to content
    content.append(Paragraph(f"GST (12%): {gst_amount}", detail_style))
    content.append(Paragraph(f"Net Price: {net_price}", detail_style))

    # Build the PDF
    doc.build(content)

    # Return the buffer content as HTTP response
    pdf = buffer.getvalue()
    buffer.close()

    # Create HTTP response with PDF content
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking_bill_{booking.id}.pdf"'
    return response


@login_required(login_url='/login')
def booking_list(request):
    user_profile = request.user.userprofile
    # Check if a date range is provided in the request
    checkin_datetime = request.GET.get('checkin_datetime', '')
    checkout_datetime = request.GET.get('checkout_datetime', '')

    # Default to the last 30 days if no date range is provided
    if not checkin_datetime or not checkout_datetime:
        checkout_datetime = datetime.now()
        checkin_datetime = checkout_datetime - timedelta(days=30)
    else:
        checkin_datetime = make_aware(datetime.strptime(checkin_datetime, '%Y-%m-%d'))
        checkout_datetime = make_aware(datetime.strptime(checkout_datetime, '%Y-%m-%d'))

    bookings = Booking.objects.filter(user_profile=user_profile,checkin_datetime__range=(checkin_datetime, checkout_datetime))

    # Calculate total revenue for the given date range
    total_revenue = bookings.aggregate(Sum('price'))['price__sum']

    # Prepare a list to hold each booking along with its details
    bookings_with_details = []

    for booking in bookings:
        # Calculate GST for the booking
        price = float(booking.price)
        gst = price * 0.12

        # Collect room details for the booking
        room_details = ", ".join([room.room_number for room in booking.rooms.all()])

        # Construct a dictionary with booking details
        booking_details = {
            'booking.user_specific_id' : booking.user_specific_id,
            'booking': booking,
            'checkin_datetime': booking.checkin_datetime,
            'checkout_datetime': booking.checkout_datetime,
            'price': price,
            'gst': gst,
            'total_price': price + gst,
            'rooms': room_details,
        }

        bookings_with_details.append(booking_details)

    return render(request, 'booking_list.html', {
        'bookings': bookings_with_details,
        'checkin_datetime': checkin_datetime,
        'checkout_datetime': checkout_datetime,
        'total_revenue': total_revenue,

    })


@login_required(login_url='/login')
def room_check_list(request, room_id):
    user_profile = request.user.userprofile
    # Retrieve the room object based on the room ID
    room = get_object_or_404(Room, id=room_id, user_profile=user_profile)

    # Check if a date range is provided in the request
    checkin_datetime = request.GET.get('checkin_datetime', '')
    checkout_datetime = request.GET.get('checkout_datetime', '')

    # Default to the last 30 days if no date range is provided
    if not checkin_datetime or not checkout_datetime:
        checkout_datetime = datetime.now()
        checkin_datetime = checkout_datetime - timedelta(days=30)
    else:
        checkin_datetime = make_aware(datetime.strptime(checkin_datetime, '%Y-%m-%d'))
        checkout_datetime = make_aware(datetime.strptime(checkout_datetime, '%Y-%m-%d'))

    # Retrieve bookings related to the room within the specified date range
    bookings = Booking.objects.filter(
        rooms=room,
        checkin_datetime__range=(checkin_datetime, checkout_datetime)
    )

    # Prepare a list to hold each booking along with its details
    bookings_with_details = []

    for booking in bookings:
        # Construct a dictionary with booking details
        booking_details = {
            'booking': booking,
            'checkin_datetime': booking.checkin_datetime,
            'checkout_datetime': booking.checkout_datetime,
        }

        bookings_with_details.append(booking_details)

    return render(request, 'room_check_list.html', {
        'room': room,
        'bookings': bookings_with_details,
        'checkin_datetime': checkin_datetime,
        'checkout_datetime': checkout_datetime,
    })



from django.utils.crypto import get_random_string
from django.utils.timezone import now, timedelta
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.sites.shortcuts import get_current_site
from django.http import JsonResponse


# Dictionary to store temporary bill links (can be replaced with a more secure method later)
temporary_links = {}

@login_required(login_url='/login')
def generate_shareable_bill_link(request, booking_id):
    # Generate a unique token for the link
    token = get_random_string(32)
    expiry_time = now() + timedelta(hours=1)  # Set an expiration time (e.g., 1 hour)

    # Save the token in the dictionary (key: token, value: booking_id and expiry time)
    temporary_links[token] = {
        'booking_id': booking_id,
        'expires_at': expiry_time
    }

    # Construct the shareable URL (you can change domain based on your server setup)
    shareable_url = request.build_absolute_uri(reverse('download_bill', args=[token]))

    return JsonResponse({
        'shareable_url': shareable_url
    })
from users.decorators import staff_login_required
@staff_login_required
def staff_generate_shareable_bill_link(request, booking_id):
    # Generate a unique token for the link
    token = get_random_string(32)
    expiry_time = now() + timedelta(hours=1)  # Set an expiration time (e.g., 1 hour)

    # Save the token in the dictionary (key: token, value: booking_id and expiry time)
    temporary_links[token] = {
        'booking_id': booking_id,
        'expires_at': expiry_time
    }

    # Construct the shareable URL (you can change domain based on your server setup)
    shareable_url = request.build_absolute_uri(reverse('download_bill', args=[token]))

    return JsonResponse({
        'shareable_url': shareable_url
    })

# This view will handle downloading the bill using the unique token
def download_bill(request, token):
    # Check if the token exists in the dictionary
    if token not in temporary_links:
        return HttpResponseForbidden("Invalid or expired link.")

    # Check if the link has expired
    link_info = temporary_links[token]
    if now() > link_info['expires_at']:
        del temporary_links[token]  # Remove the expired token
        return HttpResponseForbidden("This link has expired.")

    # Retrieve booking information and generate the bill
    booking_id = link_info['booking_id']
    return client_generate_bill(request, booking_id)  # Reuse the existing `generate_bill` function

