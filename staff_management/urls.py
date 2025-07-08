    # staff_management/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_staff, name='add_staff'),
    path('upload-image/', views.upload_staff_image, name='upload_staff_image'),
    path('list/', views.list_staff, name='list_staff'),
    path('delete/<str:staff_id>/', views.delete_staff, name='delete_staff'),
    path('punch-attendance/', views.punch_attendance, name='punch_attendance'),
    path('attendance-report/', views.get_staff_attendance_report, name='attendance_report'),
    path('record-cctv-observation/', views.record_cctv_observation, name='record_cctv_observation'), 
    path('recognize-face/', views.recognize_face, name='recognize_face'),
    path('cctv-observation-report/', views.get_cctv_observation_report, name='cctv_observation_report'),
    path('attendance/delete-range/', views.delete_attendance_logs, name='delete_attendance_logs'),
    path('last-punch-status/<str:staff_id>/', views.get_last_punch_status, name='get_last_punch_status'),

]