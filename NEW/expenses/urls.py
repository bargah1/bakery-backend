# =======================================================
# File: expenses/urls.py (NEW FILE)
# =======================================================
from django.urls import path
from . import views

urlpatterns = [
    # e.g., GET /expenses/manage/  or POST /expenses/manage/
    path('manage/', views.manage_expenses, name='manage_expenses'),
    
    # e.g., PUT /expenses/manage/expense_123/ or DELETE /expenses/manage/expense_123/
    path('manage/<str:expense_id>/', views.manage_single_expense, name='manage_single_expense'),
]
