from django.urls import path
from website import views
from .views import *

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('services', views.service, name='service'),
    path('food', views.food, name='food'),
    path('join_us', views.join_us, name='join_us'),
    path('contact', views.contact, name='contact'),
    path('service/<slug:slug>/',views.service_detail,name='service_detail'),
    path('termsConditions', views.termsConditions, name='termsConditions'),
    path('shippingPolicy', views.shippingPolicy, name='shippingPolicy'),
    path('privacyPolicy', views.privacyPolicy, name='privacyPolicy'),
    path('cancellationRefunds', views.cancellationRefunds, name='cancellationRefunds'),

    path('donation/payment/initiate/', CreateServicePaymentView.as_view(), name='donation_payment_initiate'),
    path('donation/payment/callback/', ServiceDonationCallbackView.as_view(), name='donation_payment_callback'),
    path("payment/success/", views.PaymentSuccessView.as_view(), name="payment_success"),
    path("payment/failed/", PaymentFailedView.as_view(), name="payment_failed"),
    
    
    # path('wheel_chair', views.wheel_chair, name='wheel_chair'),
    # path('napkin', views.napkin, name='napkin'),
    # path('veg_briyani', views.veg_briyani, name='veg_briyani'),
    # path('school_bag', views.school_bag, name='school_bag'),
    # path('grocery_kit', views.grocery_kit, name='grocery_kit'),
    # path('dresses', views.dresses, name='dresses'),
    # path('birds_feeding', views.birds_feeding, name='birds_feeding'),
    # path('slipper', views.slipper, name='slipper'),
    

    
]
