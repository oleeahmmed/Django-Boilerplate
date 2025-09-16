from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

from Authentication.models import UserProfile  # Adjust 'Authentication' to your actual app name

# =============================================================================
# 1. USER MANAGEMENT MODELS
# =============================================================================
# Admin creates users; Customers and Dealers get profiles. Subscriptions for dealer tiers.
# Flow: Admin → User creation → Profile assignment → Verification.

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(r'^\+?\d{10,15}$', 'Invalid phone number format')]
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
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
    
    def clean(self):
        if self.preferred_notification_method == 'sms' and not self.emergency_contact:
            raise ValidationError('Emergency contact required for SMS notifications.')
    
    def __str__(self):
        return f"{self.user.username} - Customer Profile"

class SubscriptionPlan(models.Model):
    # Dealer subscription tiers (Admin configures).
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=10.00
    )
    features = models.JSONField(default=dict)  # e.g., {"featured_listing": true}
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_plans'
    
    def __str__(self):
        return self.name

class DealerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer_profile')
    business_name = models.CharField(max_length=200)
    business_license = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    service_radius = models.PositiveIntegerField(default=10)
    
    bank_account_name = models.CharField(max_length=200)
    bank_account_number = models.CharField(max_length=50, validators=[
        RegexValidator(r'^\d{8,20}$', 'Invalid bank account number')
    ])
    bank_name = models.CharField(max_length=100)
    bank_routing_number = models.CharField(max_length=20, validators=[
        RegexValidator(r'^\d{9}$', 'Invalid routing number')
    ])
    
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=10.00,
        help_text="Platform commission percentage for app bookings"
    )
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
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
        ]
    
    def __str__(self):
        return f"{self.user.username} - Dealer Profile"

class CommissionHistory(models.Model):
    # Tracks dealer commission changes (Admin/Platform manages).
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

# Signals for User Profile Management
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

# =============================================================================
# 2. VEHICLE MANAGEMENT MODELS
# =============================================================================
# Customers add vehicles for booking services.

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

# =============================================================================
# 3. SERVICE MANAGEMENT MODELS
# =============================================================================
# Dealers create services; Admin approves categories. Technicians assign to slots.

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

class Technician(models.Model):
    dealer = models.ForeignKey('DealerProfile', on_delete=models.CASCADE, related_name='technicians')
    name = models.CharField(max_length=100)
    expertise = models.JSONField(default=list)  # e.g., ["oil_change", "tire_repair"]
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'technicians'
        indexes = [
            models.Index(fields=['dealer']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.dealer}"

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

class ServiceHistory(models.Model):
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='service_history')
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    completed_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'service_history'
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['completed_at']),
        ]
    
    def __str__(self):
        return f"{self.vehicle} - {self.service.name} ({self.completed_at})"

# =============================================================================
# 4. BOOKING MANAGEMENT MODELS
# =============================================================================
# Customers book slots; Dealers respond. Promotions for marketing.

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
    service_slot = models.ForeignKey('ServiceSlot', on_delete=models.CASCADE)
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE)
    promotion = models.ForeignKey('Promotion', on_delete=models.SET_NULL, null=True, blank=True)
    
    BOOKING_FOR_CHOICES = [
        ('self', 'Self'),
        ('friend', 'Friend')
    ]
    booking_for = models.CharField(max_length=20, choices=BOOKING_FOR_CHOICES, default='self')
    friend_vehicle_info = models.JSONField(null=True, blank=True)
    
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='app')
    status = models.CharField(max_length=30, choices=BOOKING_STATUS_CHOICES, default='pending')
    base_amount = models.DecimalField(max_digits=8, decimal_places=2)  # Service cost
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  # VAT
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
        ]
    
    def clean(self):
        # Validate status transitions
        valid_transitions = {
            'pending': ['confirmed', 'cancelled_by_customer', 'cancelled_by_dealer', 'rejected', 'expired'],
            'confirmed': ['in_progress', 'cancelled_by_customer', 'cancelled_by_dealer'],
            'in_progress': ['completed', 'no_show'],
        }
        if self.pk:  # Only validate on update
            old_instance = Booking.objects.get(pk=self.pk)
            if old_instance.status in valid_transitions and self.status not in valid_transitions[old_instance.status]:
                raise ValidationError(f"Invalid status transition from {old_instance.status} to {self.status}")

# Signal for Booking Financials (Auto-calculates on save)
@receiver(post_save, sender=Booking)
def update_booking_financials(sender, instance, **kwargs):
    from django.db import transaction
    with transaction.atomic():
        if instance.status == 'pending':
            dealer = instance.service_slot.service.dealer
            total_amount = instance.base_amount
            # Apply promotion
            if instance.promotion and instance.promotion.is_active:
                if instance.promotion.start_date <= timezone.now() <= instance.promotion.end_date:
                    if instance.promotion.max_uses is None or instance.promotion.current_uses < instance.promotion.max_uses:
                        if instance.promotion.discount_percentage > 0:
                            total_amount *= (1 - instance.promotion.discount_percentage / 100)
                        elif instance.promotion.discount_amount:
                            total_amount = max(0, total_amount - instance.promotion.discount_amount)
                        instance.promotion.current_uses += 1
                        instance.promotion.save(update_fields=['current_uses'])
            # Apply VAT (15% for Bangladesh)
            instance.tax_amount = total_amount * 0.15
            total_amount += instance.tax_amount
            # Calculate commission
            commission_rate = dealer.dealer_profile.commission_percentage / 100 if hasattr(dealer, 'dealer_profile') else 0.10
            instance.platform_commission = total_amount * commission_rate
            instance.dealer_amount = total_amount - instance.platform_commission
            instance.total_amount = total_amount
            instance.save(update_fields=['total_amount', 'tax_amount', 'platform_commission', 'dealer_amount'])
        
        if instance.status == 'completed' and kwargs.get('update_fields') is None:
            dealer = instance.service_slot.service.dealer
            if hasattr(dealer, 'dealer_profile'):
                dealer.dealer_profile.current_balance += instance.dealer_amount
                dealer.dealer_profile.save(update_fields=['current_balance'])
                # Log balance transaction
                BalanceTransaction.objects.create(
                    dealer=dealer.dealer_profile,
                    amount=instance.dealer_amount,
                    transaction_type='booking',
                    description=f"Booking {instance.id} completed",
                    related_booking=instance
                )

# =============================================================================
# 5. PAYMENT MANAGEMENT MODELS
# =============================================================================
# Post-booking payments; Dealers request payouts (Admin approves).

class VirtualCard(models.Model):
    # Dealer virtual cards for payments.
    dealer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='virtual_card')
    card_number = models.CharField(
        max_length=16,
        unique=True,
        validators=[RegexValidator(r'^\d{16}$', 'Invalid card number')]
    )
    last_four_digits = models.CharField(max_length=4)
    expiry_date = models.CharField(max_length=5)
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
    
    def save(self, *args, **kwargs):
        # Store last 4 digits
        if self.card_number:
            self.last_four_digits = self.card_number[-4:]
        super().save(*args, **kwargs)

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
    # Tracks dealer balance changes.
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

# =============================================================================
# 6. NOTIFICATION AND REVIEW MODELS
# =============================================================================
# Post-booking feedback and communication.

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

# =============================================================================
# 7. WEBHOOK INTEGRATION MODELS
# =============================================================================
# External system sync (Dealer/Platform).

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

# =============================================================================
# 8. VERIFICATION MODELS
# =============================================================================
# Admin verifies dealers and customers (KYC).

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

class CustomerVerification(models.Model):
    # Customer KYC for fraud prevention.
    VERIFICATION_TYPE_CHOICES = [
        ('phone', 'Phone OTP'),
        ('email', 'Email Verification'),
        ('national_id', 'National ID'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPE_CHOICES)
    token = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_verifications'
        unique_together = ['user', 'verification_type']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]