# bakery_ai_manager/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ownerbot/', include('ownerbot.urls')),
    path('sales/', include('sales.urls')), 
    path('production/', include('production.urls')),
    path('items/', include('items.urls')), 
    path('staff/', include('staff_management.urls')),
    path('outlets/', include('outlets.urls')),
    path('expenses/', include('expenses.urls')),
     path('reports/', include('reports.urls')),
]
