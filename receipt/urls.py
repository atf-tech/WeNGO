from django.urls import path
from . import views

urlpatterns = [
    path('80g/', views.manual_80g_mail, name='manual_80g_mail'),
    path('80g/download/', views.manual_80g_download, name='manual_80g_download'),
]
