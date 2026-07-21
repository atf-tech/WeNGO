from django.urls import path
from dashboard import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.dashboard_login, name='dashboard_login'),
    path('logout', views.dashboard_logout, name='dashboard_logout'),
    path('keepalive/', views.dashboard_keepalive, name='dashboard_keepalive'),
    path('visitor_chat', views.visitor_chat, name='visitor_chat'),
    path('Website_Donations', views.Website_Donations, name='Website_Donations'),
    path('RM_s', views.RM_S, name='RM_S'),
    path('RM_Portal',views.RM_Portal, name='RM_Portal'),
    path('qr_donation',views.qr_donation, name='qr_donation'),
    path('admin_search_page',views.admin_search_page, name='admin_search_page'),

    path('add_items',views.add_items, name='add_items'),
]
