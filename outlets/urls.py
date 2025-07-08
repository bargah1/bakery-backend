from django.urls import path
from . import views

urlpatterns = [
    #  GET /outlets/manage/  -> List all outlets
    # POST /outlets/manage/  -> Create a new outlet
    path('manage/', views.manage_outlets, name='manage_outlets'),
    
    #  PUT /outlets/manage/<outlet_id>/ -> Update an outlet
    #  DELETE /outlets/manage/<outlet_id>/ -> Delete an outlet
    path('manage/<str:outlet_id>/', views.manage_single_outlet, name='manage_single_outlet'),
]
