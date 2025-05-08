from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models.attendance import Attendance
from users.models.userprofile import UserProfile
from users.models.staff import Staff
from users.models.payment import Payment
from users.models.member import Member
from django.utils import timezone
from users.decorators import staff_login_required

@login_required
def dashboard(request):
    user_profile = request.user.userprofile

    members = Member.objects.filter(user_profile=user_profile)
    active_members = members.filter(payment__expiry_date__gte=timezone.now().date()).distinct().count()
    inactive_members = members.exclude(payment__expiry_date__gte=timezone.now().date()).distinct().count()

    total_attendance_today = Attendance.objects.filter(date=timezone.now().date(), member__user_profile=user_profile).count()

    personal_archived_members = members.filter(personal_archived=True).count()

    context = {
        'user_profile': user_profile,
        'active_members': active_members,
        'inactive_members': inactive_members,
        'total_attendance_today': total_attendance_today,
        'total_active_members': active_members,
        'total_inactive_members': inactive_members,
        'personal_archived_members': personal_archived_members,
    }
    return render(request, 'dashboard.html', context)



@staff_login_required
def staffdashboard(request):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance

    # Gather member data related to this user profile
    members = Member.objects.filter(user_profile=user_profile)
    active_members = members.filter(payment__expiry_date__gte=timezone.now().date()).distinct().count()
    inactive_members = members.exclude(payment__expiry_date__gte=timezone.now().date()).distinct().count()

    total_attendance_today = Attendance.objects.filter(date=timezone.now().date(), member__user_profile=user_profile).count()

    personal_archived_members = members.filter(personal_archived=True).count()

    context = {
        'staff': staff,
        'user_profile': user_profile,
        'active_members': active_members,
        'inactive_members': inactive_members,
        'total_attendance_today': total_attendance_today,
        'total_active_members': active_members,
        'total_inactive_members': inactive_members,
        'personal_archived_members': personal_archived_members,
    }
    return render(request, 'staffdashboard.html', context)

from users.models.booking import Room , Booking
from django.utils import timezone as djtimezone
from datetime import datetime, timedelta
from django.db.models import Sum
from decimal import Decimal

@login_required
def bdashboard(request):
    user_profile = request.user.userprofile
    now = timezone.now()

    # Fetch total bookings for this user profile this week
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=7)
    total_bookings = Booking.objects.filter(
        user_profile=user_profile,
        checkin_datetime__range=(start_of_week, end_of_week)
    ).count()

    # Fetch total revenue for this user profile this week
    total_revenue = Booking.objects.filter(
        user_profile=user_profile,
        checkin_datetime__range=(start_of_week, end_of_week)
    ).aggregate(Sum('price'))['price__sum'] or Decimal('0.00')

    # Fetch rooms associated with the user's profile
    rooms = Room.objects.filter(user_profile=user_profile)

    # Prepare room data
    room_data = []
    for room in rooms:
        upcoming_bookings = Booking.objects.filter(
            rooms=room,
            checkin_datetime__gt=now,
            user_profile=user_profile  # Filter by user profile
        ).order_by('checkin_datetime')

        recent_bookings = Booking.objects.filter(
            rooms=room,
            checkin_datetime__lte=now,
            checkin_datetime__gt=now - timedelta(days=7),
            user_profile=user_profile  # Filter by user profile
        ).order_by('-checkin_datetime')

        status = 'Occupied' if Booking.objects.filter(rooms=room, checkout_datetime__gte=now, user_profile=user_profile).exists() else 'Available'

        room_data.append({
            'room': room,
            'upcoming_bookings': upcoming_bookings,
            'recent_bookings': recent_bookings,
            'status': status
        })

    # Fetch room availability for this user profile
    room_availability = [{'room': room.room_number, 'status': 'Occupied' if Booking.objects.filter(rooms=room, checkout_datetime__gte=now, user_profile=user_profile).exists() else 'Available'} for room in rooms]

    context = {
        'user_profile': user_profile,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'room_data': room_data,
        'room_availability': room_availability,
    }
    return render(request, 'bdashboard.html', context)




@staff_login_required
def sbdashboard(request):
    # Get the staff ID from the session
    staff_id = request.session.get('staff')
    staff = get_object_or_404(Staff, id=staff_id)

    # Retrieve the associated user profile for this staff
    user_profile = staff.user_profiles  # Single UserProfile instance

    now = timezone.now()

    # Fetch total bookings for this user profile this week
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=7)
    total_bookings = Booking.objects.filter(
        user_profile=user_profile,
        checkin_datetime__range=(start_of_week, end_of_week)
    ).count()

    # Fetch total revenue for this user profile this week
    total_revenue = Booking.objects.filter(
        user_profile=user_profile,
        checkin_datetime__range=(start_of_week, end_of_week)
    ).aggregate(Sum('price'))['price__sum'] or Decimal('0.00')

    # Fetch rooms associated with the user's profile
    rooms = Room.objects.filter(user_profile=user_profile)

    # Prepare room data
    room_data = []
    for room in rooms:
        upcoming_bookings = Booking.objects.filter(
            rooms=room,
            checkin_datetime__gt=now,
            user_profile=user_profile  # Filter by user profile
        ).order_by('checkin_datetime')

        recent_bookings = Booking.objects.filter(
            rooms=room,
            checkin_datetime__lte=now,
            checkin_datetime__gt=now - timedelta(days=7),
            user_profile=user_profile  # Filter by user profile
        ).order_by('-checkin_datetime')

        status = 'Occupied' if Booking.objects.filter(rooms=room, checkout_datetime__gte=now, user_profile=user_profile).exists() else 'Available'

        room_data.append({
            'room': room,
            'upcoming_bookings': upcoming_bookings,
            'recent_bookings': recent_bookings,
            'status': status
        })

    # Fetch room availability for this user profile
    room_availability = [{'room': room.room_number, 'status': 'Occupied' if Booking.objects.filter(rooms=room, checkout_datetime__gte=now, user_profile=user_profile).exists() else 'Available'} for room in rooms]

    # Prepare context
    context = {
        'staff': staff,
        'user_profile': user_profile,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'room_data': room_data,
        'room_availability': room_availability,
    }

    return render(request, 'sbdashboard.html', context)


