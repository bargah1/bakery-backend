# File: ownerbot/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.ask, name='ask_ownerbot'),
    path('parse-order/', views.parse_order_from_voice, name='parse_order_from_voice'),

]