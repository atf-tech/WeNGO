from django.db import models
from django.utils.text import slugify
import random
import string
from django.utils import timezone
from datetime import timedelta


class Services(models.Model):

    service_name = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_quantity = models.PositiveIntegerField(default=1)
    display_order = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_food_service = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.service_name)  
        super().save(*args, **kwargs)

    def __str__(self):

        return self.service_name
    

def generate_unique_code():
    while True:
        code = ''.join(random.choices(string.ascii_lowercase, k=4))
        if not RM.objects.filter(rm_code=code).exists():
            return code

class RM(models.Model):
    BRANCH_CHOICES = [
        ('madurai', 'Madurai'),
        ('chennai', 'Chennai'),
        ('bangalore', 'Bangalore'),
    ]
    GENDER_CHOICE = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    rm_name = models.CharField(max_length=100)
    rm_mob_no = models.CharField(max_length=15)
    rm_email = models.EmailField()
    rm_code = models.CharField(max_length=4, unique=True, editable=False)
    rm_branch = models.CharField(
        max_length=20, 
        choices=BRANCH_CHOICES, 
        null=True, 
        blank=True
    )
    rm_gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICE,
        null=True,
        blank=True
    )

    rm_password = models.CharField(max_length=255, null=True, blank=True)
    
    virtual_label = models.CharField(max_length=150, blank=True, null=True)
    
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    active_whatsapp = models.BooleanField(default=False)
    whatsapp_admin_enabled = models.BooleanField(default=False)
    last_assigned_at = models.DateTimeField(null=True, blank=True)

    # Visitor live chat
    active_visitor_chat = models.BooleanField(default=False)
    last_visitor_assigned_at = models.DateTimeField(null=True, blank=True)

    tl_name = models.CharField(max_length=50,blank=True, null=True)

    qr_image = models.ImageField(upload_to="qr/", null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.rm_code:
            self.rm_code = generate_unique_code()
        self.virtual_label = f"{self.rm_name.strip()} - {self.rm_code.strip()}"
        super().save(*args, **kwargs)


    def __str__(self):
        return self.rm_name
    
    class Meta:
        indexes = [
            models.Index(fields=["is_active", "active_whatsapp", "whatsapp_admin_enabled"]),
            models.Index(fields=["is_active", "active_visitor_chat"]),
        ]


class RMLoginHistory(models.Model):
    rm = models.ForeignKey(RM, on_delete=models.CASCADE, related_name="login_history")
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.logout_time and not self.duration:
            self.duration = self.logout_time - self.login_time
        super().save(*args, **kwargs)

    def __str__(self):
       return f"{self.rm.rm_name} - {self.rm.rm_code} ({'Active' if self.status else 'Logged out'})"