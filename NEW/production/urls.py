# =======================================================
# File: production/urls.py (Corrected Order)
# =======================================================
from django.urls import path
from . import views

urlpatterns = [
    # Most specific, fixed paths should come first
    path('ingredients/all/', views.get_all_ingredients, name='get_all_ingredients'),
    path('recipes/', views.manage_recipes, name='manage_recipes'),
    path('record/', views.record_production, name='record_production'),
    path('structured-report/', views.get_structured_production_report, name='structured_production_report'),
    path('logs/delete-range/', views.delete_production_logs, name='delete_production_logs'),

    # Paths with one variable
    path('recipes/<str:recipe_id>/', views.manage_single_recipe, name='manage_single_recipe'),
    path('inventory/<str:outlet_id>/', views.manage_ingredients_by_outlet, name='manage_ingredients_by_outlet'),

    # The most generic path with multiple variables should be last
    path('inventory/<str:outlet_id>/<str:ingredient_id>/', views.manage_single_ingredient_by_outlet, name='manage_single_ingredient_by_outlet'),
]
