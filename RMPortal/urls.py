from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.inbox, name='inbox'),
    path('whatsapp-chat/', views.whatsapp_chat, name='whatsapp_chat'),
    path('all-transaction/', views.all_transaction, name='all_transaction'),
    path('add-gpay-payments/', views.add_gpay_payments, name='add_gpay_payments'),
    
]   