# shop/models.py
import uuid
from decimal import Decimal
from typing import Optional

from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError

# Authentication app-এ থাকা UserProfile reuse করছি
from Authentication.models import UserProfile


# --------------------------
# Base timestamp mixin
# --------------------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


# --------------------------
# Catalog: Category, Brand, Tag
# --------------------------
class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        """Returns full category path like 'Electronics > Mobile > Samsung'"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Brand(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Tag(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=7, default='#000000', help_text='Hex color for display')

    def __str__(self):
        return self.name


# --------------------------
# Product & Variant
# --------------------------
class Product(TimeStampedModel):
    name = models.CharField(max_length=250)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=80, unique=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    tags = models.ManyToManyField(Tag, blank=True, related_name='products')

    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=255, blank=True)

    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="For profit calculation")

    # Inventory
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    is_track_stock = models.BooleanField(default=True)
    allow_backorders = models.BooleanField(default=False)

    # Physical attributes
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Weight in kg")
    length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Length in cm")
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Width in cm")
    height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Height in cm")

    # Status flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False, help_text="Digital products don't need shipping")

    # SEO and metadata
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    meta = models.JSONField(blank=True, null=True, help_text="Additional product specifications")

    # Timestamps
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def current_price(self) -> Decimal:
        return self.discount_price if self.discount_price is not None else self.price

    @property
    def discount_percentage(self) -> Optional[int]:
        if self.discount_price and self.price > 0:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return None

    @property
    def is_in_stock(self) -> bool:
        if not self.is_track_stock:
            return True
        if self.allow_backorders:
            return True
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        if not self.is_track_stock:
            return False
        return self.stock_quantity <= self.low_stock_threshold

    def get_available_stock(self) -> int:
        """Returns available stock considering variants"""
        if self.variants.exists():
            return sum(v.stock_quantity for v in self.variants.filter(is_active=True))
        return self.stock_quantity

    def clean(self):
        if self.discount_price and self.discount_price >= self.price:
            raise ValidationError('Discount price must be less than regular price')


class ProductVariant(TimeStampedModel):
    """Product variants for size, color, etc."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=200, help_text="e.g. Red / Size M")
    sku = models.CharField(max_length=120, unique=True)
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                help_text="If blank, uses product price")
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Inventory
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Physical attributes (can override product attributes)
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    
    # Variant attributes (color, size, etc.)
    attributes = models.JSONField(blank=True, null=True, help_text="{'color': 'red', 'size': 'M'}")

    class Meta:
        unique_together = ('product', 'name')
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product', 'is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def current_price(self) -> Decimal:
        if self.price is not None:
            return self.price
        return (self.product.current_price or Decimal('0.00')) + (self.additional_price or Decimal('0.00'))

    @property
    def is_in_stock(self) -> bool:
        if not self.product.is_track_stock:
            return True
        if self.product.allow_backorders:
            return True
        return self.stock_quantity > 0


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} Image"


# --------------------------
# Customer & Guest Management
# --------------------------
class Customer(TimeStampedModel):
    """Unified customer model for both registered and guest users"""
    # User relationship (null for guest customers)
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='customer')
    
    # Guest customer fields
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    
    # Customer type
    is_guest = models.BooleanField(default=True)
    
    # Guest session tracking
    session_key = models.CharField(max_length=80, blank=True, null=True)
    
    # Customer stats
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['session_key']),
            models.Index(fields=['is_guest']),
        ]

    def __str__(self):
        if self.user_profile:
            return f"{self.user_profile.user.username} (Registered)"
        return f"{self.email} (Guest)"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def get_or_create_guest_customer(cls, email, session_key, first_name='', last_name='', phone=''):
        """Get or create a guest customer"""
        customer, created = cls.objects.get_or_create(
            email=email,
            is_guest=True,
            defaults={
                'session_key': session_key,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
            }
        )
        if not created and session_key:
            customer.session_key = session_key
            customer.save(update_fields=['session_key'])
        return customer

    @classmethod
    def get_or_create_registered_customer(cls, user_profile):
        """Get or create a registered customer"""
        customer, created = cls.objects.get_or_create(
            user_profile=user_profile,
            defaults={
                'email': user_profile.user.email,
                'first_name': user_profile.user.first_name,
                'last_name': user_profile.user.last_name,
                'is_guest': False,
            }
        )
        return customer


# --------------------------
# Reviews & Wishlist
# --------------------------
class Review(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=250, blank=True)
    comment = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'customer')
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.rating}⭐"


class Wishlist(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')

    class Meta:
        unique_together = ('customer', 'product')

    def __str__(self):
        return f"{self.customer} → {self.product.name}"


# --------------------------
# Address Management
# --------------------------
class Address(TimeStampedModel):
    ADDRESS_TYPES = (
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
        ('both', 'Both'),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='both')
    
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    company = models.CharField(max_length=120, blank=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=120, default='Bangladesh')
    phone = models.CharField(max_length=30, blank=True)
    
    is_default = models.BooleanField(default=False)
    
    # Location coordinates (optional for delivery optimization)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', 'type']),
            models.Index(fields=['customer', 'is_default']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.type}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_address(self):
        parts = [self.address_line_1]
        if self.address_line_2:
            parts.append(self.address_line_2)
        parts.extend([self.city, self.state, self.postal_code, self.country])
        return ", ".join(filter(None, parts))


# --------------------------
# Enhanced Cart Management
# --------------------------
class Cart(TimeStampedModel):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, null=True, blank=True, related_name='cart')
    session_key = models.CharField(max_length=80, blank=True, null=True)  # For anonymous users
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Applied coupon
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')
    
    # Notes
    notes = models.TextField(blank=True, help_text="Special instructions or notes")

    class Meta:
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['customer']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        if self.customer:
            return f"Cart - {self.customer}"
        return f"Cart - {self.session_key}"

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self) -> Decimal:
        return sum(item.total_price for item in self.items.select_related('product', 'variant').all())

    @property
    def total_weight(self) -> Decimal:
        total = Decimal('0.00')
        for item in self.items.select_related('product', 'variant'):
            weight = item.variant.weight if item.variant and item.variant.weight else item.product.weight
            if weight:
                total += weight * item.quantity
        return total

    def apply_coupon(self, coupon_code):
        """Apply coupon to cart"""
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            if coupon.is_valid() and self.subtotal >= coupon.minimum_amount:
                self.coupon = coupon
                self.save()
                return True, "Coupon applied successfully"
            else:
                return False, "Coupon is not valid or minimum amount not met"
        except Coupon.DoesNotExist:
            return False, "Invalid coupon code"

    def remove_coupon(self):
        """Remove applied coupon"""
        self.coupon = None
        self.save()

    def get_discount_amount(self) -> Decimal:
        """Calculate discount amount from applied coupon"""
        if not self.coupon or not self.coupon.is_valid():
            return Decimal('0.00')
        
        subtotal = self.subtotal
        if subtotal < self.coupon.minimum_amount:
            return Decimal('0.00')

        if self.coupon.discount_type == 'percentage':
            discount = (subtotal * self.coupon.discount_value / Decimal('100')).quantize(Decimal('0.01'))
            if self.coupon.max_discount_amount:
                discount = min(discount, self.coupon.max_discount_amount)
            return discount
        else:
            return min(self.coupon.discount_value, subtotal)

    @classmethod
    def get_or_create_cart(cls, customer=None, session_key=None):
        """Get or create cart for customer or session"""
        if customer:
            cart, created = cls.objects.get_or_create(
                customer=customer,
                defaults={'expires_at': timezone.now() + timezone.timedelta(days=30)}
            )
        else:
            cart, created = cls.objects.get_or_create(
                session_key=session_key,
                defaults={'expires_at': timezone.now() + timezone.timedelta(days=7)}
            )
        return cart


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    # Price snapshot (stored when item is added)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Custom options/notes for this item
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('cart', 'product', 'variant')
        indexes = [
            models.Index(fields=['cart']),
        ]

    def __str__(self):
        desc = f"{self.product.name}"
        if self.variant:
            desc += f" ({self.variant.name})"
        return f"{desc} x {self.quantity}"

    @property
    def current_unit_price(self) -> Decimal:
        """Get current price (may differ from stored unit_price)"""
        if self.variant:
            return self.variant.current_price
        return self.product.current_price

    @property
    def total_price(self) -> Decimal:
        return self.unit_price * self.quantity

    def update_unit_price(self):
        """Update stored unit price to current price"""
        self.unit_price = self.current_unit_price
        self.save(update_fields=['unit_price'])


# --------------------------
# Enhanced Coupon System
# --------------------------
class Coupon(TimeStampedModel):
    DISCOUNT_TYPES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    )
    
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200, help_text="Internal name for admin")
    description = models.TextField(blank=True, help_text="Description for customers")
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='fixed')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                              help_text="Max discount for percentage type")
    
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Total usage limit")
    usage_limit_per_customer = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    
    # Validity
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    # Restrictions
    applicable_categories = models.ManyToManyField(Category, blank=True, help_text="Leave blank for all categories")
    applicable_products = models.ManyToManyField(Product, blank=True, help_text="Specific products only")
    exclude_sale_items = models.BooleanField(default=False)
    
    # Customer restrictions
    first_time_customers_only = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'valid_from', 'valid_to']),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    def is_valid(self, customer=None) -> bool:
        now = timezone.now()
        
        # Basic validation
        if not self.is_active:
            return False
        if not (self.valid_from <= now <= self.valid_to):
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
            
        # Customer-specific validation
        if customer:
            if self.usage_limit_per_customer:
                customer_usage = CouponUsage.objects.filter(coupon=self, customer=customer).count()
                if customer_usage >= self.usage_limit_per_customer:
                    return False
            
            if self.first_time_customers_only and customer.total_orders > 0:
                return False
                
        return True

    def get_discount_amount(self, subtotal: Decimal) -> Decimal:
        """Calculate discount amount for given subtotal"""
        if subtotal < self.minimum_amount:
            return Decimal('0.00')
            
        if self.discount_type == 'percentage':
            discount = (subtotal * self.discount_value / Decimal('100')).quantize(Decimal('0.01'))
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        elif self.discount_type == 'fixed':
            return min(self.discount_value, subtotal)
        else:  # free_shipping
            return Decimal('0.00')  # Handled separately in shipping calculation


class CouponUsage(TimeStampedModel):
    """Track coupon usage by customers"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='coupon_usages')

    class Meta:
        unique_together = ('coupon', 'order')


# --------------------------
# Shipping Management
# --------------------------
class ShippingZone(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ShippingMethod(TimeStampedModel):
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name='shipping_methods')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    
    # Pricing
    base_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Delivery time
    min_delivery_days = models.PositiveIntegerField(default=1)
    max_delivery_days = models.PositiveIntegerField(default=7)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['zone', 'base_cost']

    def __str__(self):
        return f"{self.zone.name} - {self.name}"

    def calculate_cost(self, weight: Decimal = None, subtotal: Decimal = None) -> Decimal:
        """Calculate shipping cost based on weight and subtotal"""
        if self.free_shipping_threshold and subtotal and subtotal >= self.free_shipping_threshold:
            return Decimal('0.00')
            
        cost = self.base_cost
        if weight and self.cost_per_kg > 0:
            cost += weight * self.cost_per_kg
            
        return cost.quantize(Decimal('0.01'))


# --------------------------
# Payment Management
# --------------------------
class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        COD = 'cod', 'Cash on Delivery'
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        ROCKET = 'rocket', 'Rocket'
        CARD = 'card', 'Credit/Debit Card'
        BANK = 'bank', 'Bank Transfer'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
        PARTIALLY_REFUNDED = 'partially_refunded', 'Partially Refunded'

    payment_id = models.UUIDField(default=uuid.uuid4, unique=True)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.COD)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    currency = models.CharField(max_length=3, default='BDT')
    
    # Gateway information
    gateway_transaction_id = models.CharField(max_length=200, blank=True, null=True)
    gateway_reference = models.CharField(max_length=200, blank=True, null=True)
    
    # Response data from payment gateway
    gateway_response = models.JSONField(blank=True, null=True)
    
    # Fees
    gateway_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Refund information
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Failure information
    failure_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_method_display()} - {self.get_status_display()} - {self.amount}"

    @property
    def is_successful(self) -> bool:
        return self.status == self.Status.SUCCESS

    @property
    def can_be_refunded(self) -> bool:
        return self.status == self.Status.SUCCESS and self.refunded_amount < self.amount


# --------------------------
# Enhanced Order Management
# --------------------------
class Order(TimeStampedModel):
    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for Delivery'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
        RETURNED = 'returned', 'Returned'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        PARTIALLY_REFUNDED = 'partially_refunded', 'Partially Refunded'

    # Order identification
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_number = models.CharField(max_length=32, unique=True, blank=True)  # Human-readable order number
    
    # Customer information
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Status tracking
    status = models.CharField(max_length=30, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    payment_status = models.CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    # Applied discounts
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Shipping information
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Payment information
    payments = models.ManyToManyField(Payment, blank=True, related_name='orders')
    payment_method = models.CharField(max_length=20, choices=Payment.Method.choices, default=Payment.Method.COD)
    
    # Billing address snapshot
    billing_first_name = models.CharField(max_length=120)
    billing_last_name = models.CharField(max_length=120)
    billing_company = models.CharField(max_length=200, blank=True)
    billing_address_line_1 = models.CharField(max_length=255)
    billing_address_line_2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=120)
    billing_state = models.CharField(max_length=120, blank=True)
    billing_postal_code = models.CharField(max_length=50, blank=True)
    billing_country = models.CharField(max_length=120, default='Bangladesh')
    billing_phone = models.CharField(max_length=30, blank=True)
    billing_email = models.EmailField()

    # Shipping address snapshot
    shipping_first_name = models.CharField(max_length=120)
    shipping_last_name = models.CharField(max_length=120)
    shipping_company = models.CharField(max_length=200, blank=True)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=120)
    shipping_state = models.CharField(max_length=120, blank=True)
    shipping_postal_code = models.CharField(max_length=50, blank=True)
    shipping_country = models.CharField(max_length=120, default='Bangladesh')
    shipping_phone = models.CharField(max_length=30, blank=True)

    # Financial snapshots
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Weight and dimensions
    total_weight = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal('0.000'))
    
    # Order notes and tracking
    customer_notes = models.TextField(blank=True, help_text="Customer's order notes")
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes")
    tracking_number = models.CharField(max_length=100, blank=True)
    
    # Important dates
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    # Source tracking
    source = models.CharField(max_length=50, default='website', help_text="Order source: website, mobile_app, phone, etc.")
    
    # Special flags
    is_gift = models.BooleanField(default=False)
    gift_message = models.TextField(blank=True)
    requires_signature = models.BooleanField(default=False)
    is_expedited = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['billing_email']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate human-readable order number"""
        import time
        timestamp = int(time.time())
        return f"ORD-{timestamp}"

    def __str__(self):
        return f"Order {self.order_number}"

    @property
    def customer_name(self):
        return f"{self.billing_first_name} {self.billing_last_name}".strip()

    @property
    def shipping_address_full(self):
        parts = [self.shipping_address_line_1]
        if self.shipping_address_line_2:
            parts.append(self.shipping_address_line_2)
        parts.extend([self.shipping_city, self.shipping_state, self.shipping_postal_code, self.shipping_country])
        return ", ".join(filter(None, parts))

    @property
    def billing_address_full(self):
        parts = [self.billing_address_line_1]
        if self.billing_address_line_2:
            parts.append(self.billing_address_line_2)
        parts.extend([self.billing_city, self.billing_state, self.billing_postal_code, self.billing_country])
        return ", ".join(filter(None, parts))

    @property
    def can_be_cancelled(self) -> bool:
        return self.status in [self.OrderStatus.PENDING, self.OrderStatus.CONFIRMED]

    @property
    def can_be_refunded(self) -> bool:
        return self.status in [self.OrderStatus.DELIVERED] and self.payment_status == self.PaymentStatus.PAID

    @property
    def is_paid(self) -> bool:
        return self.payment_status == self.PaymentStatus.PAID

    @property
    def total_items_count(self) -> int:
        return sum(item.quantity for item in self.items.all())

    def get_status_display_badge_class(self):
        """Return CSS class for status badge"""
        status_classes = {
            self.OrderStatus.PENDING: 'warning',
            self.OrderStatus.CONFIRMED: 'info',
            self.OrderStatus.PROCESSING: 'primary',
            self.OrderStatus.SHIPPED: 'secondary',
            self.OrderStatus.OUT_FOR_DELIVERY: 'info',
            self.OrderStatus.DELIVERED: 'success',
            self.OrderStatus.CANCELLED: 'danger',
            self.OrderStatus.REFUNDED: 'dark',
            self.OrderStatus.RETURNED: 'warning',
        }
        return status_classes.get(self.status, 'secondary')

    def compute_subtotal(self) -> Decimal:
        """Compute subtotal from order items"""
        return sum((item.total_price for item in self.items.all()), start=Decimal('0.00'))

    def compute_tax(self) -> Decimal:
        """Compute tax amount"""
        if self.tax_rate > 0:
            return (self.subtotal * self.tax_rate).quantize(Decimal('0.01'))
        return Decimal('0.00')

    def compute_shipping(self) -> Decimal:
        """Compute shipping cost"""
        if self.shipping_method:
            # Check if coupon provides free shipping
            if self.coupon and self.coupon.discount_type == 'free_shipping' and self.coupon.is_valid():
                return Decimal('0.00')
            return self.shipping_method.calculate_cost(self.total_weight, self.subtotal)
        return Decimal('0.00')

    def compute_discount(self) -> Decimal:
        """Compute discount amount from coupon"""
        if not self.coupon:
            return Decimal('0.00')
        
        if not self.coupon.is_valid(self.customer):
            return Decimal('0.00')
            
        if self.subtotal < self.coupon.minimum_amount:
            return Decimal('0.00')

        return self.coupon.get_discount_amount(self.subtotal)

    def compute_total(self) -> Decimal:
        """Compute total order amount"""
        return (self.subtotal + self.tax_amount + self.shipping_amount - self.discount_amount).quantize(Decimal('0.01'))

    def recalculate_totals(self):
        """Recalculate and save all totals"""
        self.subtotal = self.compute_subtotal()
        self.tax_amount = self.compute_tax()
        self.shipping_amount = self.compute_shipping()
        self.discount_amount = self.compute_discount()
        self.total_amount = self.compute_total()
        
        # Calculate total weight
        self.total_weight = sum(
            (item.get_weight() * item.quantity for item in self.items.all()),
            start=Decimal('0.000')
        )
        
        self.save(update_fields=[
            'subtotal', 'tax_amount', 'shipping_amount', 
            'discount_amount', 'total_amount', 'total_weight', 'updated_at'
        ])

    def create_from_cart(self, cart, billing_address, shipping_address, payment_method, shipping_method=None, customer_notes=''):
        """Create order from cart"""
        # Set customer and addresses
        self.customer = cart.customer
        self.payment_method = payment_method
        self.customer_notes = customer_notes
        self.shipping_method = shipping_method
        self.coupon = cart.coupon
        
        # Copy billing address
        self.billing_first_name = billing_address.first_name
        self.billing_last_name = billing_address.last_name
        self.billing_company = billing_address.company
        self.billing_address_line_1 = billing_address.address_line_1
        self.billing_address_line_2 = billing_address.address_line_2
        self.billing_city = billing_address.city
        self.billing_state = billing_address.state
        self.billing_postal_code = billing_address.postal_code
        self.billing_country = billing_address.country
        self.billing_phone = billing_address.phone
        self.billing_email = self.customer.email
        
        # Copy shipping address
        self.shipping_first_name = shipping_address.first_name
        self.shipping_last_name = shipping_address.last_name
        self.shipping_company = shipping_address.company
        self.shipping_address_line_1 = shipping_address.address_line_1
        self.shipping_address_line_2 = shipping_address.address_line_2
        self.shipping_city = shipping_address.city
        self.shipping_state = shipping_address.state
        self.shipping_postal_code = shipping_address.postal_code
        self.shipping_country = shipping_address.country
        self.shipping_phone = shipping_address.phone
        
        self.save()
        
        # Create order items from cart items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=self,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                product_sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                product_price=cart_item.unit_price,
                quantity=cart_item.quantity,
                product_image=cart_item.product.images.filter(is_primary=True).first()
            )
        
        # Calculate totals
        self.recalculate_totals()
        
        # Record coupon usage
        if self.coupon:
            CouponUsage.objects.create(
                coupon=self.coupon,
                customer=self.customer,
                order=self
            )
            self.coupon.used_count += 1
            self.coupon.save(update_fields=['used_count'])
        
        # Clear the cart
        cart.items.all().delete()
        cart.coupon = None
        cart.save()
        
        return self


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Product snapshot at time of order
    product_name = models.CharField(max_length=250)
    product_sku = models.CharField(max_length=120, blank=True)
    product_price = models.DecimalField(max_digits=12, decimal_places=2)
    product_image = models.ForeignKey(ProductImage, on_delete=models.SET_NULL, null=True, blank=True)
    
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    # Item-specific attributes
    variant_name = models.CharField(max_length=200, blank=True)  # Snapshot of variant name
    variant_attributes = models.JSONField(blank=True, null=True)  # Snapshot of variant attributes
    
    # Weight for shipping calculation
    item_weight = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal('0.000'))
    
    # Return/refund tracking
    returned_quantity = models.PositiveIntegerField(default=0)
    refunded_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def save(self, *args, **kwargs):
        if self.variant:
            self.variant_name = self.variant.name
            self.variant_attributes = self.variant.attributes
            self.item_weight = self.variant.weight or self.product.weight or Decimal('0.000')
        else:
            self.item_weight = self.product.weight or Decimal('0.000')
        super().save(*args, **kwargs)

    def __str__(self):
        desc = self.product_name
        if self.variant_name:
            desc += f" ({self.variant_name})"
        return f"{desc} x {self.quantity}"

    @property
    def total_price(self) -> Decimal:
        return (self.product_price or Decimal('0.00')) * self.quantity

    @property
    def can_be_returned(self) -> bool:
        return self.returned_quantity < self.quantity

    @property
    def can_be_refunded(self) -> bool:
        return self.refunded_quantity < self.quantity

    def get_weight(self) -> Decimal:
        """Get item weight for shipping calculation"""
        return self.item_weight or Decimal('0.000')


# --------------------------
# Order Status History
# --------------------------
class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    
    # Who made the change
    changed_by_admin = models.CharField(max_length=150, blank=True)  # Admin username
    changed_by_system = models.BooleanField(default=False)
    
    # Additional tracking info
    tracking_number = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Order Status Histories"

    def __str__(self):
        return f"{self.order.order_number} → {self.new_status}"


# --------------------------
# Returns & Refunds
# --------------------------
class ReturnRequest(TimeStampedModel):
    class ReturnStatus(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        RECEIVED = 'received', 'Received'
        COMPLETED = 'completed', 'Completed'

    class ReturnReason(models.TextChoices):
        DEFECTIVE = 'defective', 'Defective Item'
        WRONG_ITEM = 'wrong_item', 'Wrong Item Sent'
        NOT_AS_DESCRIBED = 'not_as_described', 'Not as Described'
        CHANGED_MIND = 'changed_mind', 'Changed Mind'
        SIZE_ISSUE = 'size_issue', 'Size Issue'
        DAMAGED = 'damaged', 'Damaged During Shipping'
        OTHER = 'other', 'Other'

    return_id = models.UUIDField(default=uuid.uuid4, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='return_requests')
    
    status = models.CharField(max_length=20, choices=ReturnStatus.choices, default=ReturnStatus.REQUESTED)
    reason = models.CharField(max_length=20, choices=ReturnReason.choices)
    description = models.TextField(help_text="Detailed description of the issue")
    
    # Return details
    return_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Admin response
    admin_notes = models.TextField(blank=True)
    processed_by = models.CharField(max_length=150, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Return {self.return_id} - {self.order.order_number}"


class ReturnItem(TimeStampedModel):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    condition = models.CharField(max_length=20, choices=[
        ('new', 'Like New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], default='good')

    def __str__(self):
        return f"{self.order_item.product_name} x {self.quantity}"


class RefundRequest(TimeStampedModel):
    class RefundStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PROCESSED = 'processed', 'Processed'
        COMPLETED = 'completed', 'Completed'

    refund_id = models.UUIDField(default=uuid.uuid4, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refund_requests')
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='refund_requests')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='refund_requests')
    
    status = models.CharField(max_length=20, choices=RefundStatus.choices, default=RefundStatus.PENDING)
    reason = models.TextField()
    
    # Refund amounts
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Refund method
    refund_method = models.CharField(max_length=20, choices=Payment.Method.choices, blank=True)
    
    # Processing information
    processed_by = models.CharField(max_length=150, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.refund_id} - {self.order.order_number}"


# --------------------------
# Stock Management
# --------------------------
class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        SALE = 'sale', 'Sale'
        RETURN = 'return', 'Return'
        RESTOCK = 'restock', 'Restock'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        DAMAGE = 'damage', 'Damage'
        EXPIRED = 'expired', 'Expired'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.IntegerField(help_text="Positive for increase, negative for decrease")
    
    # Stock levels before and after
    stock_before = models.IntegerField()
    stock_after = models.IntegerField()
    
    reason = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Reference number or identifier")
    
    # Who made the change
    changed_by = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        item = self.variant.name if self.variant else self.product.name
        return f"{item}: {self.quantity_change:+d} ({self.get_movement_type_display()})"


# --------------------------
# Inventory Alerts
# --------------------------
class InventoryAlert(TimeStampedModel):
    class AlertType(models.TextChoices):
        LOW_STOCK = 'low_stock', 'Low Stock'
        OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'
        OVERSTOCK = 'overstock', 'Overstock'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_alerts')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='inventory_alerts')
    
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    current_stock = models.IntegerField()
    threshold = models.IntegerField()
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'variant', 'alert_type', 'is_resolved')

    def __str__(self):
        item = f"{self.product.name}"
        if self.variant:
            item += f" ({self.variant.name})"
        return f"{item} - {self.get_alert_type_display()}"


# --------------------------
# Enhanced Signals
# --------------------------
@receiver(pre_save, sender=Order)
def order_status_change_handler(sender, instance: Order, **kwargs):
    """Handle order status changes and stock management"""
    # Stock decrementing statuses
    STOCK_DECREMENT_STATUSES = {
        Order.OrderStatus.CONFIRMED,
        Order.OrderStatus.PROCESSING,
    }
    
    try:
        previous = Order.objects.get(pk=instance.pk)
        prev_status = previous.status
    except Order.DoesNotExist:
        previous = None
        prev_status = None

    # If status changed to stock decrement status and no stock movement exists
    if (prev_status not in STOCK_DECREMENT_STATUSES and 
        instance.status in STOCK_DECREMENT_STATUSES and
        not StockMovement.objects.filter(order=instance, movement_type=StockMovement.MovementType.SALE).exists()):
        
        # Decrement stock for each item
        for item in instance.items.select_related('product', 'variant').all():
            product = item.product
            variant = item.variant
            quantity = item.quantity
            
            if variant:
                old_stock = variant.stock_quantity
                new_stock = max(0, old_stock - quantity)
                variant.stock_quantity = new_stock
                variant.save(update_fields=['stock_quantity'])
                
                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    variant=variant,
                    order=instance,
                    movement_type=StockMovement.MovementType.SALE,
                    quantity_change=-quantity,
                    stock_before=old_stock,
                    stock_after=new_stock,
                    reason=f'Order {instance.order_number} confirmed'
                )
                
                # Check for low stock alerts
                if new_stock <= product.low_stock_threshold:
                    InventoryAlert.objects.get_or_create(
                        product=product,
                        variant=variant,
                        alert_type=InventoryAlert.AlertType.LOW_STOCK if new_stock > 0 else InventoryAlert.AlertType.OUT_OF_STOCK,
                        is_resolved=False,
                        defaults={
                            'current_stock': new_stock,
                            'threshold': product.low_stock_threshold
                        }
                    )
            else:
                old_stock = product.stock_quantity
                new_stock = max(0, old_stock - quantity)
                product.stock_quantity = new_stock
                product.save(update_fields=['stock_quantity'])
                
                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    order=instance,
                    movement_type=StockMovement.MovementType.SALE,
                    quantity_change=-quantity,
                    stock_before=old_stock,
                    stock_after=new_stock,
                    reason=f'Order {instance.order_number} confirmed'
                )
                
                # Check for low stock alerts
                if new_stock <= product.low_stock_threshold:
                    InventoryAlert.objects.get_or_create(
                        product=product,
                        alert_type=InventoryAlert.AlertType.LOW_STOCK if new_stock > 0 else InventoryAlert.AlertType.OUT_OF_STOCK,
                        is_resolved=False,
                        defaults={
                            'current_stock': new_stock,
                            'threshold': product.low_stock_threshold
                        }
                    )


@receiver(post_save, sender=Order)
def create_order_status_history(sender, instance: Order, created, **kwargs):
    """Create status history entry when order status changes"""
    if created:
        OrderStatusHistory.objects.create(
            order=instance,
            new_status=instance.status,
            note="Order created",
            changed_by_system=True
        )
    else:
        # Check if status changed
        try:
            previous = Order.objects.get(pk=instance.pk)
            if hasattr(previous, '_state') and previous._state.adding:
                return
        except Order.DoesNotExist:
            return
            
        # We need to track status changes differently since we don't have the previous value here
        # This would be better handled in a custom save method or using django-model-utils


@receiver(post_save, sender=Customer)
def update_customer_stats(sender, instance: Customer, **kwargs):
    """Update customer statistics"""
    if not instance.is_guest and instance.user_profile:
        orders = instance.orders.filter(status=Order.OrderStatus.DELIVERED)
        instance.total_orders = orders.count()
        instance.total_spent = orders.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        if kwargs.get('update_fields') is None:  # Avoid infinite recursion
            instance.save(update_fields=['total_orders', 'total_spent'])


@receiver(post_save, sender=ReturnRequest)
def handle_return_request_status_change(sender, instance: ReturnRequest, **kwargs):
    """Handle return request status changes"""
    if instance.status == ReturnRequest.ReturnStatus.COMPLETED:
        # Restore stock for returned items
        for return_item in instance.items.all():
            order_item = return_item.order_item
            product = order_item.product
            variant = order_item.variant
            quantity = return_item.quantity
            
            if variant:
                old_stock = variant.stock_quantity
                new_stock = old_stock + quantity
                variant.stock_quantity = new_stock
                variant.save(update_fields=['stock_quantity'])
                
                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    variant=variant,
                    order=order_item.order,
                    movement_type=StockMovement.MovementType.RETURN,
                    quantity_change=quantity,
                    stock_before=old_stock,
                    stock_after=new_stock,
                    reason=f'Return {instance.return_id} completed'
                )
                
                # Update order item
                order_item.returned_quantity += quantity
                order_item.save(update_fields=['returned_quantity'])
                
                # Resolve low stock alerts if stock is now sufficient
                InventoryAlert.objects.filter(
                    product=product,
                    variant=variant,
                    is_resolved=False
                ).update(
                    is_resolved=True,
                    resolved_at=timezone.now()
                )
            else:
                old_stock = product.stock_quantity
                new_stock = old_stock + quantity
                product.stock_quantity = new_stock
                product.save(update_fields=['stock_quantity'])
                
                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    order=order_item.order,
                    movement_type=StockMovement.MovementType.RETURN,
                    quantity_change=quantity,
                    stock_before=old_stock,
                    stock_after=new_stock,
                    reason=f'Return {instance.return_id} completed'
                )
                
                # Update order item
                order_item.returned_quantity += quantity
                order_item.save(update_fields=['returned_quantity'])
                
                # Resolve low stock alerts if stock is now sufficient
                InventoryAlert.objects.filter(
                    product=product,
                    variant__isnull=True,
                    is_resolved=False
                ).update(
                    is_resolved=True,
                    resolved_at=timezone.now()
                )


# --------------------------
# Analytics and Reporting Models
# --------------------------
class SalesReport(TimeStampedModel):
    """Daily sales summary for reporting"""
    date = models.DateField(unique=True)
    
    # Order statistics
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    
    # Financial statistics
    gross_sales = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_sales = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_shipping = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_discounts = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Customer statistics
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    guest_orders = models.PositiveIntegerField(default=0)
    
    # Product statistics
    items_sold = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Sales Report - {self.date}"


class ProductAnalytics(TimeStampedModel):
    """Product performance analytics"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='analytics')
    
    # Sales metrics
    total_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # View metrics (would be populated by website analytics)
    total_views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    
    # Engagement metrics
    total_wishlist_adds = models.PositiveIntegerField(default=0)
    total_cart_adds = models.PositiveIntegerField(default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    
    # Conversion metrics
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))  # Percentage
    
    # Return metrics
    total_returns = models.PositiveIntegerField(default=0)
    return_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))  # Percentage
    
    # Profitability
    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))  # Percentage
    
    # Ranking
    popularity_rank = models.PositiveIntegerField(default=0)
    revenue_rank = models.PositiveIntegerField(default=0)
    
    # Last updated
    last_calculated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics - {self.product.name}"


# --------------------------
# Notification System
# --------------------------
class Notification(TimeStampedModel):
    class NotificationType(models.TextChoices):
        ORDER_PLACED = 'order_placed', 'Order Placed'
        ORDER_CONFIRMED = 'order_confirmed', 'Order Confirmed'
        ORDER_SHIPPED = 'order_shipped', 'Order Shipped'
        ORDER_DELIVERED = 'order_delivered', 'Order Delivered'
        ORDER_CANCELLED = 'order_cancelled', 'Order Cancelled'
        PAYMENT_SUCCESS = 'payment_success', 'Payment Successful'
        PAYMENT_FAILED = 'payment_failed', 'Payment Failed'
        RETURN_REQUESTED = 'return_requested', 'Return Requested'
        RETURN_APPROVED = 'return_approved', 'Return Approved'
        REFUND_PROCESSED = 'refund_processed', 'Refund Processed'
        LOW_STOCK = 'low_stock', 'Low Stock Alert'
        OUT_OF_STOCK = 'out_of_stock', 'Out of Stock Alert'
        PRICE_DROP = 'price_drop', 'Price Drop Alert'
        BACK_IN_STOCK = 'back_in_stock', 'Back in Stock'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    admin_user = models.CharField(max_length=150, blank=True)  # For admin notifications
    
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent_email = models.BooleanField(default=False)
    is_sent_sms = models.BooleanField(default=False)
    
    # Delivery channels
    send_email = models.BooleanField(default=True)
    send_sms = models.BooleanField(default=False)
    send_push = models.BooleanField(default=True)
    
    # Additional data
    extra_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.customer or 'Admin'}"

    @classmethod
    def create_order_notification(cls, order, notification_type, title, message):
        """Create order-related notification"""
        return cls.objects.create(
            customer=order.customer,
            order=order,
            notification_type=notification_type,
            title=title,
            message=message
        )

    @classmethod
    def create_product_notification(cls, customer, product, notification_type, title, message):
        """Create product-related notification"""
        return cls.objects.create(
            customer=customer,
            product=product,
            notification_type=notification_type,
            title=title,
            message=message
        )


# --------------------------
# Email Templates
# --------------------------
class EmailTemplate(TimeStampedModel):
    class TemplateType(models.TextChoices):
        ORDER_CONFIRMATION = 'order_confirmation', 'Order Confirmation'
        ORDER_SHIPPED = 'order_shipped', 'Order Shipped'
        ORDER_DELIVERED = 'order_delivered', 'Order Delivered'
        PAYMENT_SUCCESS = 'payment_success', 'Payment Successful'
        PAYMENT_FAILED = 'payment_failed', 'Payment Failed'
        RETURN_APPROVED = 'return_approved', 'Return Approved'
        REFUND_PROCESSED = 'refund_processed', 'Refund Processed'
        WELCOME_GUEST = 'welcome_guest', 'Welcome Guest'
        WELCOME_REGISTERED = 'welcome_registered', 'Welcome Registered User'
        ABANDONED_CART = 'abandoned_cart', 'Abandoned Cart'
        BACK_IN_STOCK = 'back_in_stock', 'Back in Stock'

    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=30, choices=TemplateType.choices, unique=True)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    
    # Template variables documentation
    available_variables = models.JSONField(blank=True, null=True, help_text="Available template variables")
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


# --------------------------
# Settings and Configuration
# --------------------------
class StoreSettings(models.Model):
    """Store-wide settings"""
    # Store information
    store_name = models.CharField(max_length=200, default="My Store")
    store_description = models.TextField(blank=True)
    store_logo = models.ImageField(upload_to='store/', blank=True, null=True)
    
    # Contact information
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30, blank=True)
    
    # Address
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=120, default='Bangladesh')
    
    # Business settings
    currency = models.CharField(max_length=3, default='BDT')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0000'))
    tax_inclusive_prices = models.BooleanField(default=False)
    
    # Order settings
    auto_approve_orders = models.BooleanField(default=False)
    allow_guest_checkout = models.BooleanField(default=True)
    require_phone_for_orders = models.BooleanField(default=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Inventory settings
    track_stock_globally = models.BooleanField(default=True)
    allow_backorders = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    
    # Return settings
    allow_returns = models.BooleanField(default=True)
    return_period_days = models.PositiveIntegerField(default=30)
    
    # Email settings
    from_email = models.EmailField(blank=True)
    from_name = models.CharField(max_length=100, blank=True)
    
    # Social media
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    
    # SEO settings
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    
    # Maintenance mode
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store Settings"
        verbose_name_plural = "Store Settings"

    def __str__(self):
        return f"Settings - {self.store_name}"

    @classmethod
    def get_settings(cls):
        """Get or create store settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


# --------------------------
# Utility Functions
# --------------------------
def get_next_order_number():
    """Generate next order number"""
    import time
    timestamp = int(time.time())
    return f"ORD-{timestamp}"


def calculate_order_totals(order):
    """Calculate all order totals"""
    subtotal = sum(item.total_price for item in order.items.all())
    
    # Calculate tax
    tax_amount = Decimal('0.00')
    if order.tax_rate > 0:
        tax_amount = (subtotal * order.tax_rate).quantize(Decimal('0.01'))
    
    # Calculate shipping
    shipping_amount = Decimal('0.00')
    if order.shipping_method:
        # Check if coupon provides free shipping
        if order.coupon and order.coupon.discount_type == 'free_shipping' and order.coupon.is_valid():
            shipping_amount = Decimal('0.00')
        else:
            shipping_amount = order.shipping_method.calculate_cost(order.total_weight, subtotal)
    
    # Calculate discount
    discount_amount = Decimal('0.00')
    if order.coupon and order.coupon.is_valid():
        if subtotal >= order.coupon.minimum_amount:
            discount_amount = order.coupon.get_discount_amount(subtotal)
    
    # Calculate total
    total_amount = (subtotal + tax_amount + shipping_amount - discount_amount).quantize(Decimal('0.01'))
    
    return {
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'shipping_amount': shipping_amount,
        'discount_amount': discount_amount,
        'total_amount': total_amount
    }


# --------------------------
# Additional Utility Models
# --------------------------
class FAQ(TimeStampedModel):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=500)
    answer = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'question']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class Banner(TimeStampedModel):
    """Homepage and category banners"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to='banners/')
    mobile_image = models.ImageField(upload_to='banners/mobile/', blank=True, null=True)
    
    # Link settings
    link_url = models.URLField(blank=True)
    link_text = models.CharField(max_length=50, blank=True)
    open_in_new_tab = models.BooleanField(default=False)
    
    # Display settings
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    # Targeting
    show_on_homepage = models.BooleanField(default=True)
    show_on_categories = models.ManyToManyField(Category, blank=True)
    
    # Schedule
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.title

    @property
    def is_scheduled_active(self):
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True



class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer', 'product')  # Prevent duplicate wishlist entries
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"{self.customer.full_name}'s wishlist: {self.product.name}"