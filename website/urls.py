from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('service', views.service, name='service'),
    path('join_us', views.join_us, name='join_us'),
    path('contact', views.contact, name='contact'),
    path('service_detail', views.service_detail, name='service_detail'),
    path('termsConditions', views.termsConditions, name='termsConditions'),
    path('shippingPolicy', views.shippingPolicy, name='shippingPolicy'),
    path('privacyPolicy', views.privacyPolicy, name='privacyPolicy'),
    path('cancellationRefunds', views.cancellationRefunds, name='cancellationRefunds'),
]
