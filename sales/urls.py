# sales/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('record-sale/', views.record_sale, name='record_sale'),
    path('summary-report/', views.get_sales_summary_report, name='sales_summary_report'),
    path('structured-report/', views.get_structured_sales_report, name='structured_sales_report'), # <-- ADD THIS LINE
]
