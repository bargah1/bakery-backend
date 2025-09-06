    # staff_management/urls.py
from django.urls import path
from . import views

# In staff_management/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_staff, name='add_staff'),
    path('list/', views.list_staff, name='list_staff'),
    path('delete/<str:staff_id>/', views.delete_staff, name='delete_staff'),
    path('punch-attendance/', views.punch_attendance, name='punch_attendance'),
    path('attendance-report/', views.get_staff_attendance_report, name='attendance_report'),
    path('attendance/delete-range/', views.delete_attendance_logs, name='delete_attendance_logs'),
    path('last-punch-status/<str:staff_id>/', views.get_last_punch_status, name='get_last_punch_status'),
    
    # --- FIX: Comment out URLs for disabled face recognition features ---
    # path('upload-image/', views.upload_staff_image, name='upload_staff_image'),
    # path('recognize-face/', views.recognize_face, name='recognize_face'),
    
    # These can remain as they will return a "disabled" message
    path('record-cctv-observation/', views.record_cctv_observation, name='record_cctv_observation'), 
    path('cctv-observation-report/', views.get_cctv_observation_report, name='cctv_observation_report'),
    path('staff/salary/mark-paid/', views.mark_salary_as_paid, name='mark_salary_paid'),
    path('staff/edit/<str:staff_id>/', views.edit_staff, name='edit_staff'),
    path('attendance/mark/', views.punch_attendance, name='punch_attendance'),

]
