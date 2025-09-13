# =======================================================
# File: sales/urls.py (Corrected)
# =======================================================
from django.urls import path
from . import views

urlpatterns = [
    # Most specific, fixed paths should be first.
    path('record-sale/', views.record_sale, name='record_sale'),
    path('summary-report/', views.get_sales_summary_report, name='sales_summary_report'),
    path('structured-report/', views.get_structured_sales_report, name='structured_sales_report'),
    path('customer-transactions-report/', views.get_customer_transactions_report, name='customer_transactions_report'),
    path('process/', views.process_sale, name='process_sale'),
    path('delete-range/', views.delete_sales_data, name='delete_sales_data'),
    
    # Paths with specific keywords come next.
    path('find/<str:bill_number>/', views.find_sale_by_bill_number, name='find_sale_by_bill_number'),
    
    # The most generic path that captures any string MUST be last.
    path('<str:sale_id>/', views.get_sale_details, name='get_sale_details'),
    path('history/', views.get_sales_history, name='get_sales_history'),
    path('find/<str:numeric_bill_id>/', views.find_sale_by_bill_id, name='find_sale_by_bill_id'),
    
]
