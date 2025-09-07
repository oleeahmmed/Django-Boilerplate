from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from Authentication.models import UserProfile  # Adjust 'Authentication' to your actual app name

# User Management Models
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    
    NOTIFICATION_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both'),
    ]
    preferred_notification_method = models.CharField(
        max_length=20,
        choices=NOTIFICATION_CHOICES,
        default='email'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_profiles'
    
    def __str__(self):
        return f"{self.user.username} - Customer Profile"

class DealerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer_profile')
    business_name = models.CharField(max_length=200)
    business_license = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    service_radius = models.PositiveIntegerField(default=10)
    
    bank_account_name = models.CharField(max_length=200)
    bank_account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    bank_routing_number = models.CharField(max_length=20)
    
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="Platform commission percentage for app bookings")
    is_approved = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    has_external_website = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True, null=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dealer_profiles'
        indexes = [
            models.Index(fields=['is_approved']),
            models.Index(fields=['city']),
            models.Index(fields=['rating']),
            models.Index(fields=['has_external_website']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Dealer Profile"

class CommissionHistory(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='commission_history')
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    effective_date = models.DateTimeField()
    reason = models.TextField(blank=True, help_text="Reason for commission change")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commission_history'
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['effective_date']),
        ]
    
    def __str__(self):
        return f"{self.dealer} - {self.commission_percentage}% from {self.effective_date}"

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        try:
            user_profile = instance.profile
            if user_profile.user_type == 'customer':
                CustomerProfile.objects.create(user=instance)
            elif user_profile.user_type == 'dealer':
                DealerProfile.objects.create(user=instance)
        except UserProfile.DoesNotExist:
            pass

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'customer_profile'):
        instance.customer_profile.save()
    elif hasattr(instance, 'dealer_profile'):
        instance.dealer_profile.save()

# Vehicle Management Models
class Vehicle(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    color = models.CharField(max_length=30, blank=True)
    license_plate = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=17, unique=True, blank=True)
    
    FUEL_TYPE_CHOICES = [
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid')
    ]
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPE_CHOICES, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles'
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['license_plate']),
        ]

# Service Management Models
class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='category_icons/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'service_categories'
        verbose_name_plural = 'Service Categories'

class Service(models.Model):
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_duration = models.PositiveIntegerField()
    max_concurrent_slots = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    external_service_id = models.CharField(max_length=100, blank=True, null=True)
    is_synced_from_external = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'services'
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['external_service_id']),
        ]

class ServiceAvailability(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='availabilities')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'service_availability'
        indexes = [
            models.Index(fields=['service']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.location} ({self.start_date})"

class ServiceSlot(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_available = models.BooleanField(default=True)
    slot_number = models.PositiveIntegerField()
    
    external_slot_id = models.CharField(max_length=100, blank=True, null=True)
    is_synced_from_external = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_slots'
        unique_together = ['service', 'start_time', 'slot_number']
        indexes = [
            models.Index(fields=['service']),
            models.Index(fields=['start_time']),
            models.Index(fields=['is_available']),
            models.Index(fields=['external_slot_id']),
        ]

# Booking Management Models
class Promotion(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    current_uses = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.description}"

class Booking(models.Model):
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending Dealer Acceptance'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled_by_customer', 'Cancelled by Customer'),
        ('cancelled_by_dealer', 'Cancelled by Dealer'),
        ('rejected', 'Rejected by Dealer'),
        ('no_show', 'Customer No Show'),
        ('expired', 'Expired')
    ]
    
    SOURCE_CHOICES = [
        ('app', 'App'),
        ('external', 'External'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    service_slot = models.ForeignKey(ServiceSlot, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    promotion = models.ForeignKey(Promotion, on_delete=models.SET_NULL, null=True, blank=True)
    
    BOOKING_FOR_CHOICES = [
        ('self', 'Self'),
        ('friend', 'Friend')
    ]
    booking_for = models.CharField(max_length=20, choices=BOOKING_FOR_CHOICES, default='self')
    friend_vehicle_info = models.JSONField(null=True, blank=True)
    
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='app')
    status = models.CharField(max_length=30, choices=BOOKING_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    dealer_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    special_instructions = models.TextField(blank=True)
    dealer_response_deadline = models.DateTimeField()
    cancellation_reason = models.TextField(blank=True)
    
    external_booking_id = models.CharField(max_length=100, blank=True, null=True)
    is_synced_from_external = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bookings'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['source']),
            models.Index(fields=['created_at']),
            models.Index(fields=['external_booking_id']),
        ]

@receiver(post_save, sender=Booking)
def update_booking_financials(sender, instance, **kwargs):
    if instance.status == 'pending':
        dealer = instance.service_slot.service.dealer
        total_amount = instance.total_amount
        # Apply promotion if present
        if instance.promotion and instance.promotion.is_active:
            if instance.promotion.discount_percentage > 0:
                total_amount *= (1 - instance.promotion.discount_percentage / 100)
            elif instance.promotion.discount_amount:
                total_amount -= instance.promotion.discount_amount
            instance.promotion.current_uses += 1
            instance.promotion.save(update_fields=['current_uses'])
        # Calculate commission
        if instance.source == 'app':
            commission_rate = dealer.profile.commission_percentage / 100 if hasattr(dealer, 'profile') else 0.10
            instance.platform_commission = total_amount * commission_rate
            instance.dealer_amount = total_amount - instance.platform_commission
        else:  # external
            instance.platform_commission = 0.00
            instance.dealer_amount = total_amount
        instance.total_amount = total_amount
        instance.save(update_fields=['total_amount', 'platform_commission', 'dealer_amount'])
    
    if instance.status == 'completed' and kwargs.get('update_fields') is None:
        dealer = instance.service_slot.service.dealer
        if hasattr(dealer, 'profile'):
            dealer.profile.current_balance += instance.dealer_amount
            dealer.profile.save(update_fields=['current_balance'])
            # Log balance transaction
            BalanceTransaction.objects.create(
                dealer=dealer.profile,
                amount=instance.dealer_amount,
                transaction_type='booking',
                description=f"Booking {instance.id} completed",
                related_booking=instance
            )

# Webhook Integration Models
class WebhookConfiguration(models.Model):
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webhook_configs')
    endpoint_url = models.URLField()
    secret_key = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    EVENT_TYPES = [
        ('booking.created', 'Booking Created'),
        ('booking.updated', 'Booking Updated'),
        ('booking.cancelled', 'Booking Cancelled'),
        ('service.created', 'Service Created'),
        ('service.updated', 'Service Updated'),
        ('slot.created', 'Slot Created'),
        ('slot.updated', 'Slot Updated'),
    ]
    subscribed_events = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhook_configurations'

class WebhookEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('service.created', 'Service Created'),
        ('service.updated', 'Service Updated'),
        ('service.deleted', 'Service Deleted'),
        ('slot.created', 'Slot Created'),
        ('slot.updated', 'Slot Updated'),
        ('slot.deleted', 'Slot Deleted'),
        ('booking.created', 'Booking Created'),
        ('booking.updated', 'Booking Updated'),
        ('booking.cancelled', 'Booking Cancelled'),
    ]
    
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webhook_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    event_data = models.JSONField()
    external_id = models.CharField(max_length=100, blank=True, null=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'webhook_events'
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['event_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class WebhookLog(models.Model):
    webhook_event = models.ForeignKey(WebhookEvent, on_delete=models.CASCADE, related_name='logs')
    request_url = models.URLField()
    request_headers = models.JSONField()
    request_body = models.JSONField()
    response_status_code = models.PositiveIntegerField(null=True, blank=True)
    response_headers = models.JSONField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    execution_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'webhook_logs'
        indexes = [
            models.Index(fields=['webhook_event']),
            models.Index(fields=['created_at']),
        ]

class VirtualCard(models.Model):
    dealer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='virtual_card')
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.CharField(max_length=5)
    cvv = models.CharField(max_length=4)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    external_card_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'virtual_cards'
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['card_number']),
        ]


# Payment Management Models
class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded')
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('customer_card', 'Customer Card'),
        ('virtual_card', 'Dealer Virtual Card'),
        ('external', 'External (No Payment Record)'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    payment_gateway = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default='BDT')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='customer_card')
    virtual_card = models.ForeignKey(VirtualCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    gateway_response = models.JSONField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_method']),
        ]


class PayoutRequest(models.Model):
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected')
    ]
    
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payout_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='pending')
    bank_details = models.JSONField()
    admin_notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_payouts')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payout_requests'
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]


class BalanceTransaction(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='balance_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    TRANSACTION_TYPE_CHOICES = [
        ('booking', 'Booking Completion'),
        ('payout', 'Payout'),
        ('adjustment', 'Manual Adjustment'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    description = models.TextField(blank=True)
    related_booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    related_payout = models.ForeignKey(PayoutRequest, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'balance_transactions'
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.dealer} - {self.transaction_type} ({self.amount})"

# Notification Models
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient']),
            models.Index(fields=['is_read']),
        ]

# Review Models
class Review(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reviews'
        unique_together = ['customer', 'booking']
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['rating']),
        ]

# Verification Models
class DealerVerificationDocument(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='verification_documents')
    DOCUMENT_TYPE_CHOICES = [
        ('trade_license', 'Trade License'),
        ('business_registration', 'Business Registration Certificate'),
        ('national_id', 'National ID (NID)'),
        ('tin_certificate', 'TIN Certificate'),
        ('address_proof', 'Proof of Business Address'),
    ]
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_file = models.FileField(upload_to='dealer_verification_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_documents')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'dealer_verification_documents'
        unique_together = ['dealer', 'document_type']
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['document_type']),
            models.Index(fields=['status']),
        ]

@receiver(post_save, sender=Booking)
def update_booking_financials(sender, instance, **kwargs):
    if instance.status == 'pending':
        dealer = instance.service_slot.service.dealer
        if instance.source == 'app':
            commission_rate = dealer.profile.commission_percentage / 100 if hasattr(dealer, 'profile') else 0.10
            instance.platform_commission = instance.total_amount * commission_rate
            instance.dealer_amount = instance.total_amount - instance.platform_commission
        else:  # external
            instance.platform_commission = 0.00
            instance.dealer_amount = instance.total_amount
        instance.save(update_fields=['platform_commission', 'dealer_amount'])
    
    if instance.status == 'completed' and kwargs.get('update_fields') is None:
        dealer = instance.service_slot.service.dealer
        if hasattr(dealer, 'profile'):
            dealer.profile.current_balance += instance.dealer_amount
            dealer.profile.save(update_fields=['current_balance'])