from django.db import models

# Create your models here.

class Manual80GSubmission(models.Model):
    donor_name = models.CharField(max_length=100)
    donor_email = models.EmailField()
    donor_mobile = models.CharField(max_length=20)
    service_date = models.DateField()  
    donation_date = models.DateField()
    donor_pan = models.CharField(max_length=10)
    donation_price = models.DecimalField(max_digits=10, decimal_places=2)
    donor_address = models.TextField()
    receipt_no = models.CharField(max_length=50)
    mode_of_donation = models.CharField(max_length=50)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor_name} - {self.receipt_no}"