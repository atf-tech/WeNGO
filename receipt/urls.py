from django.urls import path
from . import views


urlpatterns = [
    path('download/', views.download_donation_receipt, name='download_donation_receipt'),
    path('80g/', views.manual_80g_mail, name='manual_80g_mail'),
    path('80g/download/', views.manual_80g_download, name='manual_80g_download'),
]
