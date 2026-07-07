from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('', include('receipt.urls')),
    path('rm/', include('RMPortal.urls')),
    path('', include('easypay.urls')),
]
if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT )