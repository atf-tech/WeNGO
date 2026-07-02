from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import RMPayment,RMGPayPayment



@admin.register(RMPayment)
class RMPaymentAdmin(admin.ModelAdmin):
    readonly_fields = ("receipt_no", "submitted_at")
    search_fields = [f.name for f in RMPayment._meta.fields]
    

admin.site.register(RMGPayPayment)
    