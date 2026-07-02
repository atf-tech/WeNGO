from django.db import models
from dashboard.models import Services


class ServiceDonation(models.Model):

    service = models.ForeignKey(
        Services,
        on_delete=models.CASCADE,
        related_name="donations"
    )

    donor_name = models.CharField(max_length=200)
    donor_mobile = models.CharField(max_length=15)
    donor_email = models.EmailField()
    address = models.TextField()
    service_date = models.DateField( null=True, blank=True)
    pan_number = models.CharField( max_length=10, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    donation_amount = models.DecimalField( max_digits=10, decimal_places=2)

    # Payment Fields 
    txnid = models.CharField(max_length=100, unique=True, blank=True, null=True)
    easebuzz_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    easebuzz_payment_mode = models.CharField(max_length=50, blank=True, null=True)
    easebuzz_payment_status = models.CharField(max_length=50, blank=True, null=True)
    is_paid = models.BooleanField(default=False)


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor_name} - {self.service.service_name}"
    

    
class Volunteer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile_no = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    dob = models.DateField(null=True,blank=True)
    address = models.TextField()
    cv = models.FileField(upload_to='cvs/')   

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email})"
    

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=50)
    message = models.TextField(max_length=500)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

