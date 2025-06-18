    # items/urls.py
from django.urls import path
from . import views

urlpatterns = [
        path('manage-products/', views.manage_products, name='manage_products'),
        path('inventory-report/', views.get_inventory_report, name='inventory_report'), # <-- Add this line
    ]
    