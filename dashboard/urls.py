from django.urls import path
from dashboard import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.dashboard_login, name='dashboard_login'),
    path('logout', views.dashboard_logout, name='dashboard_logout'),
    path('keepalive/', views.dashboard_keepalive, name='dashboard_keepalive'),
    path('whatsapp_api', views.whatsapp_api, name='whatsapp_api'),

    # ── WhatsApp Analytics API endpoints ──
    path('whatsapp_api/api/kpi/', views.api_kpi_data, name='wa_api_kpi'),
    path('whatsapp_api/api/branch-chart/', views.api_branch_chart, name='wa_api_branch_chart'),
    path('whatsapp_api/api/trend-chart/', views.api_trend_chart, name='wa_api_trend_chart'),
    path('whatsapp_api/api/rm-table/', views.api_rm_table, name='wa_api_rm_table'),
    path('whatsapp_api/api/response-time/', views.api_response_time, name='wa_api_response_time'),
    path('whatsapp_api/api/funnel/', views.api_conversion_funnel, name='wa_api_funnel'),
    path('whatsapp_api/api/donor-search/', views.api_donor_search, name='wa_api_donor_search'),

    path('whatsapp_api/rm/<str:rm_code>/', views.rm_analytics_detailed, name='rm_analytics_detailed'),
    path('whatsapp_api/api/rm/<str:rm_code>/profile/', views.api_rm_detail_profile, name='wa_api_rm_profile'),
    path('whatsapp_api/api/rm/<str:rm_code>/stats/', views.api_rm_detail_stats, name='wa_api_rm_stats'),
    path('whatsapp_api/api/rm/<str:rm_code>/trend/', views.api_rm_detail_trend, name='wa_api_rm_trend'),
    path('whatsapp_api/api/rm/<str:rm_code>/conversations/', views.api_rm_detail_conversations, name='wa_api_rm_conversations'),
    path('whatsapp_api/api/rm/<str:rm_code>/conversation/<int:conv_id>/messages/', views.api_rm_detail_conv_messages, name='wa_api_rm_conv_messages'),
    path('visitor_chat', views.visitor_chat, name='visitor_chat'),
    path('website_donations', views.website_donations, name='website_donations'),
    path('RM_s', views.RM_S, name='RM_S'),
    path('RM_Portal',views.RM_Portal, name='RM_Portal'),
    path('qr_donation',views.qr_donation, name='qr_donation'),
    path('admin_search_page',views.admin_search_page, name='admin_search_page'),

    path('add_items',views.add_items, name='add_items'),

    # ── Visitor Chat API endpoints (Phase 1: KPI Cards) ──
    path('visitor_chat/api/kpi/', views.api_kpi, name='visitor_chat_api_kpi'),
    path('visitor_chat/api/table/', views.api_table, name='visitor_chat_api_table'),
    path('visitor_chat/api/visitors/', views.api_visitors, name='visitor_chat_api_visitors'),
    path('visitor_chat/api/charts/', views.api_charts, name='visitor_chat_api_charts'),
]
