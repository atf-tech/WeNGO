from django.db import models
from django.utils import timezone
import random
from dashboard.models import RM


def generate_gpay_receipt_number():
    from .models import RMGPayPayment

    while True:
        number = (
            f"IPF{timezone.now().strftime('%Y%m%d')}"
            f"-{random.randint(1000, 9999)}"
        )

        if not RMGPayPayment.objects.filter(
            receipt_no=number
        ).exists():
            return number


class RMGPayPayment(models.Model):
    rm = models.ForeignKey(
        RM,
        on_delete=models.CASCADE,
        related_name="gpay_payments"
    )

    # Store RM snapshot details
    rm_code = models.CharField(max_length=4)
    rm_name = models.CharField(max_length=100)
    rm_email = models.EmailField(blank=True, null=True)

    # Donor details
    donor_name = models.CharField( max_length=100, blank=True, null=True)
    donor_email = models.EmailField( blank=True, null=True)
    donor_mobile = models.CharField( max_length=15, blank=True, null=True)
    donor_address = models.TextField( blank=True, null=True)
    donor_pan = models.CharField( max_length=20, blank=True, null=True)

    # Payment details
    amount = models.DecimalField( max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField( default=timezone.now)
    gpay_reference_id = models.CharField( max_length=100, blank=True, null=True, db_index=True, help_text="UPI Ref / UTR / GPay Transaction ID")
    payment_screenshot = models.ImageField( upload_to="gpay_screenshots/", blank=True, null=True, help_text="Upload GPay payment screenshot" )
    receipt_no = models.CharField( max_length=25, unique=True, editable=False)

    PACKAGE_CHOICES = [
        ("birthday", "Birthday Package"),
        ("food", "Food Package"),
        ("service", "Service"),
        ("other", "Other"),
    ]

    package_type = models.CharField(
        max_length=20,
        choices=PACKAGE_CHOICES,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField( auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-fill RM details
        self.rm_code = self.rm.rm_code
        self.rm_name = self.rm.rm_name
        self.rm_email = self.rm.rm_email

        # Generate receipt number
        if not self.receipt_no:
            self.receipt_no = generate_gpay_receipt_number()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.donor_name or 'GPay Donor'} "
            f"- ₹{self.amount} "
            f"({self.receipt_no})"
        )

    @property
    def display_amount(self):
        return self.amount

    @property
    def submitted_at(self):
        return self.payment_date

    @property
    def easebuzz_payment_mode(self):
        return "UPI"

    @property
    def pan_no(self):
        return self.donor_pan
    




def generate_receipt_number():
    from .models import RMPayment
    import random
    while True:
        number = f"IPF-{random.randint(0, 999999):06d}"
        if not RMPayment.objects.filter(receipt_no=number).exists():
            return number
        
        

class RMPayment(models.Model):
    rm_code = models.CharField(max_length=4)
    rm_name = models.CharField(max_length=100)
    qr_name= models.CharField(max_length=150, blank=True, null=True)
    
    PACKAGE_CHOICES = [
        ('birthday', 'Birthday Package'),
        ('food', 'Food Package'),
    ]

    donor_name = models.CharField(max_length=100)
    donor_email = models.EmailField()
    donor_mobile = models.CharField(max_length=15)
    donor_amount = models.DecimalField(max_digits=10, decimal_places=2)
    donor_message = models.TextField(blank=True, null=True)  
    donor_address = models.TextField(blank=True, null=True)  
    
    receipt_no = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True)

    package_type = models.CharField(max_length=20, choices=PACKAGE_CHOICES, blank=True, null=True)
    
    txnid = models.CharField(max_length=100, unique=True) 
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    payment_mode = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(max_length=50, blank=True, null=True)
    bank_rrn = models.CharField(max_length=50, blank=True, null=True)
    
    easebuzz_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    easebuzz_payment_mode = models.CharField(max_length=50, blank=True, null=True)
    easebuzz_payment_status = models.CharField(max_length=50, blank=True, null=True)

    pan_no = models.CharField(max_length=20, blank=True, null=True)

    is_paid = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = generate_receipt_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donor_name} | ₹{self.donor_amount} | {self.rm_code}"







class QRDonation(models.Model):
    
    #easebuzz instacollect
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True,blank=True, null=True) 
    payment_mode = models.CharField(max_length=20,blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    unique_transaction_reference = models.CharField(max_length=100,blank=True, null=True)
    
    remitter_name = models.CharField(max_length=100,blank=True, null=True)
    remitter_upi = models.CharField(max_length=100, blank=True, null=True)
    remitter_account_number = models.CharField(max_length=20, blank=True, null=True)
    remitter_ifsc = models.CharField(max_length=20, blank=True, null=True)
    remitter_phone = models.CharField(max_length=20, blank=True, null=True)
    virtual_upi_handle = models.CharField(max_length=100,blank=True, null=True)
    virtual_label = models.CharField(max_length=100, blank=True, null=True)
    
    
    qr_id = models.CharField(max_length=100,null=True, blank=True)  
    qr_name = models.CharField(max_length=255, null=True, blank=True)
    qr_description = models.TextField(null=True, blank=True)
    qr_notes = models.JSONField(null=True, blank=True)
    
    rm_name = models.CharField(max_length=100, blank=True, null=True)
    rm = models.ForeignKey(RM, on_delete=models.SET_NULL, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True,blank=True, null=True)
    
    # ---Razerpay Payment Info ---
    payment_id = models.CharField(
    max_length=100,
    unique=True,
    null=True,
    blank=True
)

    bank_rrn = models.CharField(max_length=100, null=True, blank=True)
    method = models.CharField(max_length=50, null=True, blank=True)

    # Donor Info
    PACKAGE_CHOICES = [
        ('birthday', 'Birthday Package'),
        ('food', 'Food Package'),
        ('service', 'Service Package'),
        
    ]
    
    #rm portal edits
    donor_name = models.CharField(max_length=255, null=True, blank=True)
    donor_email = models.EmailField(null=True, blank=True)
    donor_mobile = models.CharField(max_length=20, null=True, blank=True)
    donor_address = models.TextField(blank=True, null=True)
    receipt_no = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True)
    package_type = models.CharField(max_length=20, choices=PACKAGE_CHOICES, blank=True, null=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)
    

    
    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = generate_receipt_number()
        super().save(*args, **kwargs)

    def _str_(self):
        return f"{self.transaction_id} - {self.remitter_name}" 
    
    @property
    def ui_status(self):
        mapping = {
            "unsettled": "success",
            "failure": "failure",
        }
        return mapping.get(self.status.lower(), self.status)

    @property
    def display_amount(self):
        return self.amount