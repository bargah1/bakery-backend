    # items/urls.py
from django.urls import path
from . import views
urlpatterns = [

    path('manage-products/', views.manage_products, name='manage_products'),
    path('manage-products/<str:product_id>/', views.manage_single_product, name='manage_single_product'), 
    path('inventory-report/', views.get_inventory_report, name='inventory_report'),
    path('generate-barcode/', views.generate_barcode, name='generate_barcode'),
    path('upload-image/', views.upload_product_image, name='upload_product_image'), 

]
