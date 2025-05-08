from django.urls import path
from .views.view_expense import  add_esection, add_expense, delete_expense, esection_list, expense_list, generate_pdf
from .views.view_userprofile import edit_profile,signup, profile, user_login, user_logout, index, pending_approval
from .views.view_member import generate_member_card, archived_generate_member_report_pdf, generate_member_report_pdf, scan_qr_code, generate_qr_code, MemberLogin,memberlogout,memberdashboard, member_list, add_member, member_detail, member_update, member_delete, archive_list, archive_member, unarchive_member, personal_archive_list, personal_archive_member, personal_unarchive_member
from .views.view_payment import edit_payment, add_payment, payment_list_all, generate_pdf_receipt, payment_holding_list, mark_payment_complete, member_payment_details
from .views.view_attendance import qr_mark_attendance_by_scan,mark_attendance, attendance_list, member_attendance_details
from .views.view_dashboard import dashboard, staffdashboard, bdashboard, sbdashboard
from .views.view_staff import  smember_update, generate_pdf_receipt_for_staff, staff_member_payment_details, staff_qr_mark_attendance_by_scan, staff_signup, spersonal_archive_member,smember_detail, spersonal_unarchive_member,  staff_list,  stafflogout, smember_list, sadd_member, smark_attendance, sattendance_list, sadd_payment, spayment_holding_list,spersonal_archive_list
#from .views.view_viber import viber_signup, viber_login, viber_profile, viber_edit_profile
from .views.view_booking import client_generate_bill, download_bill, generate_shareable_bill_link, staff_generate_shareable_bill_link, room_check_list, add_room, room_list, book_room, edit_booking, delete_booking, generate_pdf_book, booking_detail, booking_list, generate_bill
from .views.view_staffattendance import staff_mark_attendance, staff_attendance_list
from .views.view_staff_booking import sroom_list, sbook_room, sedit_booking, sbooking_detail, staff_room_check_list, staff_generate_bill

urlpatterns = [

    #path('viber_signup/', viber_signup, name='viber_signup'),
    #path('viber_login/', viber_login, name='viber_login'),
    #path('viber_profile/', viber_profile, name='viber_profile'),
    #path('viber_edit_profile/', viber_edit_profile, name='viber_edit_profile'),
    #path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('', index, name='index'),
    path('signup/', signup, name='signup'),
    path('profile/', profile, name='profile'),
    path('pending_approval/', pending_approval, name='pending_approval'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('profile/edit/', edit_profile, name='edit_profile'),

    #path('stafflogin/', StaffLogin.as_view(), name='stafflogin'),
    path('stafflogout/', stafflogout, name='stafflogout'),
    path('smembers/', smember_list, name='smember_list'),
    path('staff/list/', staff_list, name='staff_list'),
    path('smembers/add/', sadd_member, name='sadd_member'),
    path('smark/', smark_attendance, name='smark_attendance'),
    path('sattendance_list/', sattendance_list, name='sattendance_list'),
    path('sadd_payment/<int:member_id>/', sadd_payment, name='sadd_payment'),
    path('spayment/holding/', spayment_holding_list, name='spayment_holding_list'),
    path('smember/<int:pk>/', smember_detail, name='smember_detail'),
    path('<int:pk>/sedit/', smember_update, name='smember_update'),
    path('spersonal_archive_list/', spersonal_archive_list, name='spersonal_archive_list'),
    path('spersonal_archive/<int:member_id>/', spersonal_archive_member, name='spersonal_archive_member'),
    path('spersonal_unarchive/<int:member_id>/', spersonal_unarchive_member, name='spersonal_unarchive_member'),
    path('ssignup/', staff_signup, name='staff_signup'),


    path('staff/payment/<int:payment_id>/generate_pdf/<int:member_id>/', generate_pdf_receipt_for_staff, name='generate_pdf_receipt_for_staff'),
    path('staff/member/<int:member_id>/payments/', staff_member_payment_details, name='staff_member_payment_details'),

    #path('memberlogin/', MemberLogin.as_view(), name='memberlogin'),
    #path('memberlogout/', memberlogout, name='memberlogout'),
    #path('memberdashboard/<int:member_id>/', memberdashboard, name='memberdashboard'),
    path('members/', member_list, name='member_list'),
    path('members/add/', add_member, name='add_member'),
    path('members/<int:pk>/', member_detail, name='member_detail'),
    path('<int:pk>/edit/', member_update, name='member_update'),
    path('<int:pk>/delete/', member_delete, name='member_confirm_delete'),
    path('archive/', archive_list, name='archive_list'),
    path('archive/<int:member_id>/', archive_member, name='archive_member'),
    path('unarchive/<int:member_id>/', unarchive_member, name='unarchive_member'),
    path('personal_archive/', personal_archive_list, name='personal_archive_list'),
    path('personal_archive/<int:member_id>/', personal_archive_member, name='personal_archive_member'),
    path('personal_unarchive/<int:member_id>/', personal_unarchive_member, name='personal_unarchive_member'),
    path('report/pdf/', generate_member_report_pdf, name='generate_member_report_pdf'),
    path('archive/report/pdf/', archived_generate_member_report_pdf, name='archived_generate_member_report_pdf'),

    path('members/<int:member_id>/generate-card/', generate_member_card, name='generate_member_card'),
    path('qr/<int:member_id>', generate_qr_code, name='generate_qr_code'),
    path('qr/', qr_mark_attendance_by_scan, name='qr_mark_attendance_by_scan'),
    path('sca/', scan_qr_code, name='scan_qr_code'),
    path('sqr/', staff_qr_mark_attendance_by_scan, name='staff_qr_mark_attendance_by_scan'),

    path('add_payment/<int:member_id>/', add_payment, name='add_payment'),
    path('paylist/', payment_list_all, name='payment_list_all'),
    path('payment/<int:payment_id>/generate_pdf/<int:member_id>/', generate_pdf_receipt, name='generate_pdf_receipt'),
    path('payment/holding/', payment_holding_list, name='payment_holding_list'),
    path('payment/<int:payment_id>/complete/', mark_payment_complete, name='mark_payment_complete'),
    path('member/<int:member_id>/payments/', member_payment_details, name='member_payment_details'),
    path('payment/edit/<int:payment_id>/', edit_payment, name='edit_payment'),

    path('mark/', mark_attendance, name='mark_attendance'),
    path('attendance_list/', attendance_list, name='attendance_list'),
    path('member/<int:member_id>/attendance/', member_attendance_details, name='member_attendance_details'),

    path('bdashboard/', bdashboard, name='bdashboard'),
    path('dashboard/', dashboard, name='dashboard'),
    path('staffdashboard/', staffdashboard, name='staffdashboard'),
    path('sbdashboard/', sbdashboard, name='sbdashboard'),

    path('staff_mark/', staff_mark_attendance, name='staff_mark_attendance'),
    path('staff_attendance_list/', staff_attendance_list, name='staff_attendance_list'),

    path('esection/', esection_list, name='esection_list'),
    path('esection/add/', add_esection, name='add_esection'),
    path('esection/<int:esection_id>/expenses/', expense_list, name='expense_list'),
    path('esection/<int:esection_id>/add_expense/', add_expense, name='add_expense'),
    path('esection/expense/<int:expense_id>/delete/', delete_expense, name='delete_expense'),
    path('generate-pdf/<int:esection_id>/', generate_pdf, name='generate_pdf'),


    path('add/', add_room, name='add_room'),
    path('room_list', room_list, name='room_list'),
    path('book-room/', book_room, name='book_room'),
    path('edit-booking/<str:booking_id>/', edit_booking, name='edit_booking'),
    path('delete-booking/<str:booking_id>/', delete_booking, name='delete_booking'),
    path('generate-pdf/', generate_pdf_book, name='generate_pdf_book'),
    path('booking_detail/<str:booking_id>/', booking_detail, name='booking_detail'),
    path('booking_list/', booking_list, name='booking_list'),
    path('generate_bill/<str:booking_id>/', generate_bill, name='generate_bill'),
    path('client_generate_bill/<str:booking_id>/', client_generate_bill, name='client_generate_bill'),
    path('room/<int:room_id>/checklist/', room_check_list, name='room_check_list'),


    path('sroom_list/', sroom_list, name='sroom_list'),
    path('sbook-room/', sbook_room, name='sbook_room'),
    path('sedit-booking/<str:booking_id>/', sedit_booking, name='sedit_booking'),
    path('sbooking_detail/<str:booking_id>/', sbooking_detail, name='sbooking_detail'),
    path('sroom/<int:room_id>/checklist/', staff_room_check_list, name='staff_room_check_list'),
    path('sgenerate_bill/<str:booking_id>/', staff_generate_bill, name='staff_generate_bill'),

    # URL for generating the shareable link
    path('generate-shareable-bill/<int:booking_id>/', generate_shareable_bill_link, name='generate_shareable_bill_link'),
    path('staff-generate-shareable-bill/<int:booking_id>/', staff_generate_shareable_bill_link, name='staff_generate_shareable_bill_link'),
    # URL for downloading the bill using the token from the shareable link
    path('download-bill/<str:token>/', download_bill, name='download_bill'),




]