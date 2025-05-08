from django.shortcuts import render, redirect, get_object_or_404
from users.models.staff import Staff, StaffAttendance
from users.models.booking import Booking, Room
from users.forms import PaymentForm
from django.views import View
from users.decorators import staff_login_required
from users.models.member import Member
from django.contrib.auth.decorators import login_required
from django.utils import timezone as djtimezone
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
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



@staff_login_required
def sroom_list(request):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance

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
    return render(request, 'sroom_list.html', {'rooms': rooms, 'now': now})



@staff_login_required
def sbook_room(request):
    # Ensure that the staff is logged in by getting the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Get the user profile associated with the staff
    user_profile = staff.user_profiles  # Retrieve associated UserProfile

    # Get the rooms that the staff's associated user profile is allowed to book
    rooms = Room.objects.filter(user_profile=user_profile)  # Filter rooms for this user profile

    if request.method == 'POST':
        # Validate form data before starting the transaction
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

        # Validate required fields and input data before starting the transaction
        if not room_ids:
            error_message = 'You must select at least one room to proceed with the booking.'
            return render(request, 'sbook_room.html', {'rooms': rooms, 'error': error_message})

        if not name or not checkin_datetime or not checkout_datetime:
            error_message = 'Please fill in all required fields.'
            return render(request, 'sbook_room.html', {'rooms': rooms, 'error': error_message})

        if checkout_datetime <= checkin_datetime:
            error_message = 'Invalid date range: Check-out date must be after check-in date.'
            return render(request, 'sbook_room.html', {'rooms': rooms, 'error': error_message})

        try:
            # Use atomic transaction for database operations
            with transaction.atomic():
                # Create the Booking object, associating it with the staff's user profile
                booking = Booking.objects.create(
                    user_profile=user_profile,  # Use the staff's associated UserProfile
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

                # List to hold rooms that are already booked
                conflicting_rooms = []

                # Iterate through selected rooms and add them to the booking
                for room_id in room_ids:
                    room = Room.objects.get(id=room_id, user_profile=user_profile)

                    # Check if the room is already booked for the given date range
                    existing_bookings = Booking.objects.filter(
                        rooms=room,
                        checkout_datetime__gte=checkin_datetime,
                        checkin_datetime__lte=checkout_datetime
                    )

                    if existing_bookings.exists():
                        # Add the room number to the list of conflicting rooms
                        conflicting_rooms.append(room.room_number)

                    # Add the room to the booking (handled after the conflict check)
                    booking.rooms.add(room)

                # If there are any conflicting rooms, delete the booking and show the error
                if conflicting_rooms:
                    booking.delete()  # Rollback the booking
                    error_message = f'The following rooms are already booked: {", ".join(map(str, conflicting_rooms))}'
                    return render(request, 'sbook_room.html', {'rooms': rooms, 'error': error_message})

                # If no conflicts, proceed with saving the rooms and booking
                for room_id in room_ids:
                    room = Room.objects.get(id=room_id, user_profile=user_profile)
                    room.is_available = False  # Mark the room as unavailable
                    room.save()

                # If everything succeeds, redirect to booking detail
                return redirect('sbooking_detail', booking_id=booking.user_specific_id)

        except ValueError as ve:
            # Handle invalid values (e.g., non-numeric input)
            error_message = f'Invalid value encountered: {str(ve)}'
            return render(request, 'sbook_room.html', {'rooms': rooms, 'error': error_message})

        except ValidationError as e:
            # Handle any other validation errors
            error_message = 'Validation error occurred. Please check your input.'
            return render(request, 'sbook_room.html', {'rooms': rooms, 'error': error_message})

    else:
        # Handle the GET request
        return render(request, 'sbook_room.html', {'rooms': rooms})

@staff_login_required
def sbooking_detail(request, booking_id):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Ensure this matches the attribute in the Staff model

    booking = get_object_or_404(Booking, user_specific_id=booking_id, user_profile=user_profile)
    rooms = booking.rooms.all()
    price = booking.price
    other_charges = booking.other_charges
    total_charges = Decimal(other_charges or 0) + price

    gst_amount = price - (price / (1 + Decimal('0.12')))
    net_price = price - gst_amount
    gst = price * Decimal('0.12')
    total_price = price + gst

    return render(request, 'sbooking_detail.html', {
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



@staff_login_required
def sedit_booking(request, booking_id):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance
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
        return redirect('sbooking_detail', booking_id=booking_id)
    else:
        return render(request, 'sedit_booking.html', {'booking': booking, 'rooms': rooms})


@staff_login_required
def staff_room_check_list(request, room_id):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance
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

    return render(request, 'staff_room_check_list.html', {
        'room': room,
        'bookings': bookings_with_details,
        'checkin_datetime': checkin_datetime,
        'checkout_datetime': checkout_datetime,
    })

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from django.utils.timezone import localtime
from reportlab.lib.units import inch

@staff_login_required
def staff_generate_bill(request, booking_id):
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
    content.append(Spacer(1, 12))
    content.append(Paragraph(f"GST (12%): {gst_amount}", detail_style))
    content.append(Paragraph(f"Net Price: {net_price}", detail_style))

    # Add the logged-in staff's name at the bottom of the document
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)
    content.append(Spacer(1, 24))
    content.append(Paragraph(f"Generated by: {staff.username}", detail_style))

    # Build the PDF
    doc.build(content)

    # Return the buffer content as HTTP response
    pdf = buffer.getvalue()
    buffer.close()

    # Create HTTP response with PDF content
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking_bill_{booking.id}.pdf"'
    return response
