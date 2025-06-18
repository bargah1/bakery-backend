# production/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('record-production/', views.record_production, name='record_production'),
    path('summary-report/', views.get_production_summary_report, name='production_summary_report'),
    path('structured-report/', views.get_structured_production_report, name='structured_production_report'), # <-- ADD THIS LINE
]
