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
    
    path('payment_success', views.payment_success, name='payment_success'),
    path('payment_failed', views.payment_failed, name='payment_failed'),
    
    path('wheel_chair', views.wheel_chair, name='wheel_chair'),
    path('napkin', views.napkin, name='napkin'),
    path('veg_briyani', views.veg_briyani, name='veg_briyani'),
    path('school_bag', views.school_bag, name='school_bag'),
    path('grocery_kit', views.grocery_kit, name='grocery_kit'),
    path('dresses', views.dresses, name='dresses'),
    path('birds_feeding', views.birds_feeding, name='birds_feeding'),
    
]
