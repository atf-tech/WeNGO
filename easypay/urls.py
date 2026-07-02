from django.urls import path
from . import views
from .views import *
from dashboard.views import *


urlpatterns = [
    path('create/rm-payment/', CreateRMPaymentView.as_view(), name='create_rm_payment'),
    path('payment/callback/rm/', RMPaymentCallbackView.as_view(), name='rm_payment_callback'),
    path('easepay/success/', views.payment_success, name='payment_success'),
    path('easepay/failure/', views.payment_failure, name='payment_failure'),
    path('easepay/<str:rm_code>/', views.rm_donation_form, name='rm_donation_form'),
   
]
