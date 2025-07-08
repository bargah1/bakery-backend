# =======================================================
# File: reports/urls.py (Upgraded)
# =======================================================
from django.urls import path
from . import views

urlpatterns = [
    # --- NEW: URL for the main dashboard summary ---
    path('dashboard-summary/', views.get_dashboard_summary, name='dashboard_summary'),
    
    path('profit-loss/', views.get_profit_loss_report, name='profit_loss_report'),
    path('clear-data/', views.clear_transaction_data, name='clear_transaction_data'),
    path('low-stock-alerts/', views.get_low_stock_alerts, name='low_stock_alerts'),
]
