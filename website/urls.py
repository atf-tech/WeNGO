from django.urls import path
from website import views
from .views import *

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('services', views.service, name='service'),
    path('food', views.home, name='home'),
    path('join_us', views.join_us, name='join_us'),
    path('contact', views.contact, name='contact'),

    path('service/<slug:slug>/',views.service_detail,name='service_detail'),
    path( "home/<slug:slug>/",views.home_details,name="home_details"),

    path('termsConditions', views.termsConditions, name='termsConditions'),
    path('shippingPolicy', views.shippingPolicy, name='shippingPolicy'),
    path('privacyPolicy', views.privacyPolicy, name='privacyPolicy'),
    path('cancellationRefunds', views.cancellationRefunds, name='cancellationRefunds'),

    path('donation/payment/initiate/', CreateServicePaymentView.as_view(), name='donation_payment_initiate'),
    path('donation/payment/callback/', ServiceDonationCallbackView.as_view(), name='donation_payment_callback'),
    path("payment/success/", views.PaymentSuccessView.as_view(), name="payment_success"),
    path("payment/failed/", PaymentFailedView.as_view(), name="payment_failed"),

    path('food/payment/initiate/', CreateHomePaymentView.as_view(), name='food_donation_payment_initiate'),
    path('food/payment/callback/', HomeDonationCallbackView.as_view(), name='food_donation_payment_callback'),
    path("food/payment/success/", HomePaymentSuccessView.as_view(), name="food_payment_success"),
    path("food/payment/failed/", HomePaymentFailedView.as_view(), name="food_payment_failed"),
    
    


    
]
