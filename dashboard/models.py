from django.db import models
from django.utils.text import slugify
import random
import string
from django.utils import timezone
from datetime import timedelta
import re

class Home(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, null=True)
    members = models.PositiveIntegerField()
    description = models.TextField()
    home_image = models.ImageField(upload_to='home_images/')

    # ── Google Maps location (paste the "Embed a map" code from Google Maps) ──
    map_embed = models.TextField(
        blank=True, null=True,
        help_text="Paste the Google Maps 'Embed a map' iframe code (or just its src URL) for this home's location."
    )

    # ── Last 5 Service Images (oldest auto-replaced when uploading via dashboard) ──
    service_img1 = models.ImageField(upload_to='home_service_images/', blank=True, null=True)
    service_img2 = models.ImageField(upload_to='home_service_images/', blank=True, null=True)
    service_img3 = models.ImageField(upload_to='home_service_images/', blank=True, null=True)
    service_img4 = models.ImageField(upload_to='home_service_images/', blank=True, null=True)
    service_img5 = models.ImageField(upload_to='home_service_images/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def map_embed_src(self):
        """Return a safe Google Maps embed URL from `map_embed`.

        Staff may paste either the full <iframe ... src="..."></iframe> code or
        just the src URL. We extract the URL and only allow Google Maps embed
        links so nothing arbitrary can be framed on the site.
        """
        value = (self.map_embed or "").strip()
        if not value:
            return ""
        match = re.search(r'src\s*=\s*["\']([^"\']+)["\']', value)
        url = match.group(1) if match else value
        if url.startswith("https://www.google.com/maps/embed") or \
           url.startswith("https://maps.google.com/maps"):
            return url
        return ""

    def get_service_images(self):
        return [
            img for img in [
                self.service_img1, self.service_img2, self.service_img3,
                self.service_img4, self.service_img5,
            ] if img
        ]

    def add_service_image(self, new_image):
        
        # Delete the oldest file from storage before overwriting
        if self.service_img1:
            self.service_img1.delete(save=False)

        # Shift left
        self.service_img1 = self.service_img2
        self.service_img2 = self.service_img3
        self.service_img3 = self.service_img4
        self.service_img4 = self.service_img5
        self.service_img5 = new_image
        self.save()

    def __str__(self):
        return self.name
    

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