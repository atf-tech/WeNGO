from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('receipt/', include('receipt.urls')),
    path('rm/', include('RMPortal.urls')),
]
