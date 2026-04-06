
from django.contrib import admin
from .models import Manual80GSubmission

@admin.register(Manual80GSubmission)
class Manual80GSubmissionAdmin(admin.ModelAdmin):
    list_display = ['donor_name', 'donor_email', 'donor_mobile', 'donor_pan', 'donor_address', 'receipt_no', 'donation_price', 'mode_of_donation', 'service_date', 'donation_date', 'submitted_at']