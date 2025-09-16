from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    Category, Brand, Tag, Product, ProductVariant, ProductImage,
    Customer, Address, Review, Wishlist, Cart, CartItem, Order,
    OrderItem, OrderStatusHistory, Payment, Coupon, CouponUsage,
    ShippingZone, ShippingMethod, ReturnRequest, ReturnItem,
    RefundRequest, StockMovement, InventoryAlert, SalesReport,
    ProductAnalytics, Notification, EmailTemplate, StoreSettings,
    FAQ, Banner
)

# --------------------------
# Inline Admin Classes
# --------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'order']

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ['name', 'sku', 'price', 'stock_quantity', 'is_active']

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ['product', 'variant', 'quantity', 'unit_price']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product', 'variant', 'quantity', 'product_price']

class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ['previous_status', 'new_status', ]

class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    fields = ['order_item', 'quantity', 'condition']

class ShippingMethodInline(admin.TabularInline):
    model = ShippingMethod
    extra = 1
    fields = ['name', 'base_cost', 'free_shipping_threshold', 'is_active']

# --------------------------
# Main Admin Classes
# --------------------------
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'sort_order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'sort_order']

@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ['name', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'sort_order']

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ['name', 'color']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ['name', 'sku', 'category', 'brand', 'price', 'stock_quantity', 'is_active']
    list_filter = ['is_active', 'category', 'brand']
    search_fields = ['name', 'sku']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    filter_horizontal = ['tags']
    inlines = [ProductImageInline, ProductVariantInline]

@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    list_display = ['product', 'name', 'sku', 'price', 'stock_quantity', 'is_active']
    list_filter = ['is_active', 'product']
    search_fields = ['name', 'sku', 'product__name']
    list_editable = ['is_active']

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ['full_name', 'email', 'is_guest']
    list_filter = ['is_guest']
    search_fields = ['email', 'first_name', 'last_name']

@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ['customer', 'type', 'full_name', 'city', 'is_default']
    list_filter = ['type', 'is_default']
    search_fields = ['first_name', 'last_name', 'city']

@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ['customer', 'total_items', 'subtotal', 'coupon']
    list_filter = ['coupon']
    search_fields = ['customer__email']
    inlines = [CartItemInline]

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'total_amount']
    list_filter = ['status', 'payment_method']
    search_fields = ['order_number', 'billing_email']
    inlines = [OrderItemInline, OrderStatusHistoryInline]

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['payment_id', 'method', 'status', 'amount']
    list_filter = ['method', 'status']
    search_fields = ['payment_id']

@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code', 'name']
    list_editable = ['is_active']

@admin.register(ShippingZone)
class ShippingZoneAdmin(ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ShippingMethodInline]

@admin.register(ShippingMethod)
class ShippingMethodAdmin(ModelAdmin):
    list_display = ['zone', 'name', 'base_cost', 'is_active']
    list_filter = ['is_active', 'zone']
    search_fields = ['name']

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ['product', 'customer', 'rating', 'is_approved']
    list_filter = ['rating', 'is_approved']
    search_fields = ['product__name', 'customer__email']
    list_editable = ['is_approved']

@admin.register(ReturnRequest)
class ReturnRequestAdmin(ModelAdmin):
    list_display = ['return_id', 'order', 'customer', 'status']
    list_filter = ['status']
    search_fields = ['return_id', 'order__order_number']
    inlines = [ReturnItemInline]

@admin.register(RefundRequest)
class RefundRequestAdmin(ModelAdmin):
    list_display = ['refund_id', 'order', 'customer', 'status']
    list_filter = ['status']
    search_fields = ['refund_id', 'order__order_number']

@admin.register(StockMovement)
class StockMovementAdmin(ModelAdmin):
    list_display = ['product', 'variant', 'movement_type', 'quantity_change']
    list_filter = ['movement_type']
    search_fields = ['product__name', 'variant__name']

@admin.register(InventoryAlert)
class InventoryAlertAdmin(ModelAdmin):
    list_display = ['product', 'variant', 'alert_type', 'current_stock', 'is_resolved']
    list_filter = ['alert_type', 'is_resolved']
    search_fields = ['product__name']
    list_editable = ['is_resolved']

@admin.register(SalesReport)
class SalesReportAdmin(ModelAdmin):
    list_display = ['date', 'total_orders', 'gross_sales', 'net_sales']
    date_hierarchy = 'date'

@admin.register(ProductAnalytics)
class ProductAnalyticsAdmin(ModelAdmin):
    list_display = ['product', 'total_sold', 'total_revenue']
    search_fields = ['product__name']

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ['title', 'customer', 'notification_type', 'is_read']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'customer__email']
    list_editable = ['is_read']

@admin.register(EmailTemplate)
class EmailTemplateAdmin(ModelAdmin):
    list_display = ['name', 'template_type', 'is_active']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name']
    list_editable = ['is_active']

@admin.register(StoreSettings)
class StoreSettingsAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ['question', 'category', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['question']
    list_editable = ['is_active']

@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ['title', 'is_active', 'show_on_homepage']
    list_filter = ['is_active', 'show_on_homepage']
    search_fields = ['title']
    list_editable = ['is_active']

# Register remaining models
admin.site.register(Wishlist)
admin.site.register(CouponUsage)

# Customize admin site
admin.site.site_header = "E-commerce Admin"
admin.site.site_title = "E-commerce Admin"
admin.site.index_title = "Welcome to E-commerce Admin"