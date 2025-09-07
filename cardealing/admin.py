from django.contrib import admin
from django.db.models import Q
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import (
    CustomerProfile, DealerProfile, CommissionHistory, Vehicle,
    ServiceCategory, Service, ServiceAvailability, ServiceSlot,
    Booking, Promotion, WebhookConfiguration, WebhookEvent,
    WebhookLog, Payment, PayoutRequest, VirtualCard,
    BalanceTransaction, Notification, Review, DealerVerificationDocument,
)

# Base Admin class with role-based filtering
class RoleBasedAdmin(ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return self.filter_queryset_by_user_type(request, qs)
    
    def filter_queryset_by_user_type(self, request, qs):
        """Override this method in child classes for specific filtering"""
        return qs
    
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return self.check_add_permission_by_user_type(request)
    
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self.check_change_permission_by_user_type(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self.check_delete_permission_by_user_type(request, obj)
    
    def check_add_permission_by_user_type(self, request):
        return False
    
    def check_change_permission_by_user_type(self, request, obj=None):
        return False
    
    def check_delete_permission_by_user_type(self, request, obj=None):
        return False

# Inline Classes
class DealerVerificationDocumentInline(StackedInline):
    model = DealerVerificationDocument
    extra = 0
    fields = ['document_type', 'document_file', 'status', 'admin_notes', 'reviewed_by', 'reviewed_at']
    readonly_fields = ['uploaded_at', 'reviewed_at']

class CommissionHistoryInline(TabularInline):
    model = CommissionHistory
    extra = 0
    readonly_fields = ['created_at']
    fields = ['commission_percentage', 'effective_date', 'reason', 'created_at']

class BalanceTransactionInline(TabularInline):
    model = BalanceTransaction
    extra = 0
    readonly_fields = ['created_at']
    fields = ['transaction_type', 'amount', 'description', 'created_at']

class ServiceSlotInline(TabularInline):
    model = ServiceSlot
    extra = 1
    fields = ['start_time', 'end_time', 'is_available', 'slot_number']
    readonly_fields = ['created_at', 'updated_at']

class ServiceAvailabilityInline(StackedInline):
    model = ServiceAvailability
    extra = 0
    fields = ['start_date', 'end_date', 'location', 'is_active']
    readonly_fields = ['created_at']

class WebhookLogInline(TabularInline):
    model = WebhookLog
    extra = 0
    readonly_fields = ['created_at', 'response_headers', 'response_body', 'execution_time_ms']
    fields = ['request_url', 'response_status_code', 'execution_time_ms', 'created_at']

# Admin Classes
@admin.register(CustomerProfile)
class CustomerProfileAdmin(RoleBasedAdmin):
    list_display = ['user', 'get_user_email', 'get_user_full_name', 'city', 'preferred_notification_method', 'created_at']
    list_filter = ['preferred_notification_method', 'city', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'city', 'postal_code']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'preferred_notification_method')
        }),
        ('Address Details', {
            'fields': ('address', 'city', 'postal_code', 'emergency_contact')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user']
    
    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'
    
    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user.first_name else obj.user.username
    get_user_full_name.short_description = 'Full Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'customer':
            return qs.filter(user=request.user)
        return qs.none()
    
    def check_change_permission_by_user_type(self, request, obj=None):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'customer':
            return obj is None or obj.user == request.user
        return False

@admin.register(DealerProfile)
class DealerProfileAdmin(RoleBasedAdmin):
    list_display = ['user', 'get_user_email', 'business_name', 'city', 'commission_percentage', 'is_approved', 'rating', 'current_balance', 'created_at']
    list_filter = ['is_approved', 'city', 'has_external_website', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'business_name', 'business_license', 'city']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Business Details', {
            'fields': ('business_name', 'business_license', 'commission_percentage', 'is_approved')
        }),
        ('Address & Location', {
            'fields': ('address', 'city', 'postal_code', 'latitude', 'longitude', 'service_radius')
        }),
        ('Banking Information', {
            'fields': ('bank_account_name', 'bank_account_number', 'bank_name', 'bank_routing_number')
        }),
        ('Webhook Integration', {
            'fields': ('has_external_website', 'webhook_url', 'webhook_secret'),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': ('rating', 'total_reviews', 'current_balance')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'rating', 'total_reviews', 'current_balance']
    autocomplete_fields = ['user']
    inlines = [DealerVerificationDocumentInline, CommissionHistoryInline, BalanceTransactionInline]
    
    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(user=request.user)
        return qs
    
    def check_change_permission_by_user_type(self, request, obj=None):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return obj is None or obj.user == request.user
        return False

@admin.register(CommissionHistory)
class CommissionHistoryAdmin(ModelAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'commission_percentage', 'effective_date', 'created_at']
    list_filter = ['effective_date', 'created_at']
    search_fields = ['dealer__user__username', 'dealer__business_name', 'reason']
    fieldsets = (
        ('Commission Details', {
            'fields': ('dealer', 'commission_percentage', 'effective_date', 'reason')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    autocomplete_fields = ['dealer']
    date_hierarchy = 'effective_date'

    def get_dealer_business_name(self, obj):
        return obj.dealer.business_name
    get_dealer_business_name.short_description = 'Business Name'
    get_dealer_business_name.admin_order_field = 'dealer__business_name'

@admin.register(Vehicle)
class VehicleAdmin(RoleBasedAdmin):
    list_display = ['owner', 'get_owner_name', 'make', 'model', 'year', 'license_plate', 'fuel_type', 'is_primary', 'created_at']
    list_filter = ['fuel_type', 'is_primary', 'make', 'year', 'created_at']
    search_fields = ['owner__username', 'owner__first_name', 'owner__last_name', 'make', 'model', 'license_plate', 'vin']
    fieldsets = (
        ('Owner Information', {
            'fields': ('owner',)
        }),
        ('Vehicle Details', {
            'fields': ('make', 'model', 'year', 'color', 'fuel_type', 'is_primary')
        }),
        ('Identification', {
            'fields': ('license_plate', 'vin')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['owner']

    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}" if obj.owner.first_name else obj.owner.username
    get_owner_name.short_description = 'Owner Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'customer':
            return qs.filter(owner=request.user)
        return qs
    
    def check_add_permission_by_user_type(self, request):
        user_type = getattr(request.user, 'profile', None)
        return user_type and user_type.user_type == 'customer'
    
    def check_change_permission_by_user_type(self, request, obj=None):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'customer':
            return obj is None or obj.owner == request.user
        return False

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    fieldsets = (
        ('Category Details', {
            'fields': ('name', 'description', 'icon', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

@admin.register(Service)
class ServiceAdmin(RoleBasedAdmin):
    list_display = ['name', 'dealer', 'get_dealer_business_name', 'category', 'base_price', 'estimated_duration', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'is_synced_from_external', 'created_at']
    search_fields = ['name', 'description', 'dealer__username', 'dealer__dealerprofile__business_name']
    fieldsets = (
        ('Basic Information', {
            'fields': ('dealer', 'category', 'name', 'description')
        }),
        ('Service Details', {
            'fields': ('base_price', 'estimated_duration', 'max_concurrent_slots', 'is_active')
        }),
        ('External Integration', {
            'fields': ('external_service_id', 'is_synced_from_external'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['dealer', 'category']
    inlines = [ServiceAvailabilityInline, ServiceSlotInline]

    def get_dealer_business_name(self, obj):
        return obj.dealer.dealerprofile.business_name if hasattr(obj.dealer, 'dealerprofile') else 'N/A'
    get_dealer_business_name.short_description = 'Business Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(dealer=request.user)
        return qs
    
    def check_add_permission_by_user_type(self, request):
        user_type = getattr(request.user, 'profile', None)
        return user_type and user_type.user_type == 'dealer'

@admin.register(VirtualCard)
class VirtualCardAdmin(RoleBasedAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'card_number', 'balance', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['dealer__username', 'dealer__dealerprofile__business_name', 'card_number', 'external_card_id']
    fieldsets = (
        ('Card Information', {
            'fields': ('dealer', 'card_number', 'expiry_date', 'cvv', 'balance', 'is_active', 'external_card_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['dealer']

    def get_dealer_business_name(self, obj):
        return obj.dealer.dealerprofile.business_name if hasattr(obj.dealer, 'dealerprofile') else 'N/A'
    get_dealer_business_name.short_description = 'Business Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(dealer=request.user)
        return qs

@admin.register(BalanceTransaction)
class BalanceTransactionAdmin(RoleBasedAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'transaction_type', 'amount', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['dealer__user__username', 'dealer__business_name', 'description']
    fieldsets = (
        ('Transaction Information', {
            'fields': ('dealer', 'transaction_type', 'amount', 'description', 'related_booking', 'related_payout')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    autocomplete_fields = ['dealer', 'related_booking', 'related_payout']

    def get_dealer_business_name(self, obj):
        return obj.dealer.business_name
    get_dealer_business_name.short_description = 'Business Name'
    get_dealer_business_name.admin_order_field = 'dealer__business_name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(dealer__user=request.user)
        return qs

@admin.register(Notification)
class NotificationAdmin(RoleBasedAdmin):
    list_display = ['recipient', 'get_recipient_name', 'message_preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['recipient__username', 'recipient__first_name', 'recipient__last_name', 'message']
    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'message', 'is_read')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    autocomplete_fields = ['recipient']

    def get_recipient_name(self, obj):
        return f"{obj.recipient.first_name} {obj.recipient.last_name}" if obj.recipient.first_name else obj.recipient.username
    get_recipient_name.short_description = 'Recipient Name'

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type in ['customer', 'dealer']:
            return qs.filter(recipient=request.user)
        return qs

@admin.register(Review)
class ReviewAdmin(RoleBasedAdmin):
    list_display = ['customer', 'get_customer_name', 'dealer', 'get_dealer_business_name', 'booking', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['customer__username', 'customer__first_name', 'customer__last_name', 'dealer__username', 'comment']
    fieldsets = (
        ('Review Information', {
            'fields': ('customer', 'dealer', 'booking', 'rating', 'comment')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    autocomplete_fields = ['customer', 'dealer', 'booking']

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}" if obj.customer.first_name else obj.customer.username
    get_customer_name.short_description = 'Customer Name'

    def get_dealer_business_name(self, obj):
        return obj.dealer.dealerprofile.business_name if hasattr(obj.dealer, 'dealerprofile') else 'N/A'
    get_dealer_business_name.short_description = 'Business Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type:
            if user_type.user_type == 'customer':
                return qs.filter(customer=request.user)
            elif user_type.user_type == 'dealer':
                return qs.filter(dealer=request.user)
        return qs

@admin.register(DealerVerificationDocument)
class DealerVerificationDocumentAdmin(ModelAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'document_type', 'status', 'uploaded_at', 'reviewed_at']
    list_filter = ['document_type', 'status', 'uploaded_at']
    search_fields = ['dealer__user__username', 'dealer__business_name', 'document_type']
    fieldsets = (
        ('Document Information', {
            'fields': ('dealer', 'document_type', 'document_file', 'status')
        }),
        ('Admin Review', {
            'fields': ('admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Metadata', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['uploaded_at', 'reviewed_at']
    autocomplete_fields = ['dealer', 'reviewed_by']

    def get_dealer_business_name(self, obj):
        return obj.dealer.business_name
    get_dealer_business_name.short_description = 'Business Name'
    get_dealer_business_name.admin_order_field = 'dealer__business_name' 
    
    def check_add_permission_by_user_type(self, request):
        user_type = getattr(request.user, 'profile', None)
        return user_type and user_type.user_type == 'dealer'
    
    def check_change_permission_by_user_type(self, request, obj=None):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return obj is None or obj.dealer == request.user
        return False

@admin.register(ServiceAvailability)
class ServiceAvailabilityAdmin(RoleBasedAdmin):
    list_display = ['service', 'get_service_dealer', 'location', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_date', 'created_at']
    search_fields = ['service__name', 'service__dealer__username', 'location']
    fieldsets = (
        ('Service Information', {
            'fields': ('service',)
        }),
        ('Availability Details', {
            'fields': ('start_date', 'end_date', 'location', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    autocomplete_fields = ['service']
    date_hierarchy = 'start_date'

    def get_service_dealer(self, obj):
        return obj.service.dealer.username
    get_service_dealer.short_description = 'Dealer'
    get_service_dealer.admin_order_field = 'service__dealer__username'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(service__dealer=request.user)
        return qs

@admin.register(ServiceSlot)
class ServiceSlotAdmin(RoleBasedAdmin):
    list_display = ['service', 'get_service_dealer', 'start_time', 'end_time', 'is_available', 'slot_number', 'is_synced_from_external']
    list_filter = ['is_available', 'is_synced_from_external', 'start_time', 'created_at']
    search_fields = ['service__name', 'service__dealer__username', 'external_slot_id']
    fieldsets = (
        ('Service Information', {
            'fields': ('service',)
        }),
        ('Slot Details', {
            'fields': ('start_time', 'end_time', 'is_available', 'slot_number')
        }),
        ('External Integration', {
            'fields': ('external_slot_id', 'is_synced_from_external'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['service']
    date_hierarchy = 'start_time'

    def get_service_dealer(self, obj):
        return obj.service.dealer.username
    get_service_dealer.short_description = 'Dealer'
    get_service_dealer.admin_order_field = 'service__dealer__username'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(service__dealer=request.user)
        return qs
    
    def check_add_permission_by_user_type(self, request):
        user_type = getattr(request.user, 'profile', None)
        return user_type and user_type.user_type == 'dealer'

@admin.register(Promotion)
class PromotionAdmin(ModelAdmin):
    list_display = ['code', 'description_short', 'discount_percentage', 'discount_amount', 'start_date', 'end_date', 'is_active', 'current_uses', 'max_uses']
    list_filter = ['is_active', 'start_date', 'end_date', 'created_at']
    search_fields = ['code', 'description']
    fieldsets = (
        ('Promotion Details', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Configuration', {
            'fields': ('discount_percentage', 'discount_amount')
        }),
        ('Validity Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'current_uses')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'current_uses']
    date_hierarchy = 'start_date'

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

@admin.register(Booking)
class BookingAdmin(RoleBasedAdmin):
    list_display = ['id', 'customer', 'get_customer_name', 'get_service_name', 'get_dealer', 'vehicle', 'source', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'source', 'booking_for', 'is_synced_from_external', 'created_at']
    search_fields = ['customer__username', 'customer__first_name', 'customer__last_name', 'service_slot__service__name', 'vehicle__license_plate']
    fieldsets = (
        ('Booking Information', {
            'fields': ('customer', 'service_slot', 'vehicle', 'promotion', 'source', 'booking_for', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'platform_commission', 'dealer_amount')
        }),
        ('Additional Information', {
            'fields': ('friend_vehicle_info', 'special_instructions', 'cancellation_reason', 'dealer_response_deadline')
        }),
        ('External Integration', {
            'fields': ('external_booking_id', 'is_synced_from_external'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'platform_commission', 'dealer_amount']
    autocomplete_fields = ['customer', 'service_slot', 'vehicle', 'promotion']
    date_hierarchy = 'created_at'

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}" if obj.customer.first_name else obj.customer.username
    get_customer_name.short_description = 'Customer Name'

    def get_service_name(self, obj):
        return obj.service_slot.service.name
    get_service_name.short_description = 'Service'
    
    def get_dealer(self, obj):
        return obj.service_slot.service.dealer.username
    get_dealer.short_description = 'Dealer'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type:
            if user_type.user_type == 'customer':
                return qs.filter(customer=request.user)
            elif user_type.user_type == 'dealer':
                return qs.filter(service_slot__service__dealer=request.user)
        return qs
    
    def check_change_permission_by_user_type(self, request, obj=None):
        user_type = getattr(request.user, 'profile', None)
        if user_type and obj:
            if user_type.user_type == 'customer':
                return obj.customer == request.user
            elif user_type.user_type == 'dealer':
                return obj.service_slot.service.dealer == request.user
        return False

@admin.register(WebhookConfiguration)
class WebhookConfigurationAdmin(RoleBasedAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'endpoint_url', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['dealer__username', 'dealer__dealerprofile__business_name', 'endpoint_url']
    fieldsets = (
        ('Configuration', {
            'fields': ('dealer', 'endpoint_url', 'secret_key', 'is_active', 'subscribed_events')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['dealer']

    def get_dealer_business_name(self, obj):
        return obj.dealer.dealerprofile.business_name if hasattr(obj.dealer, 'dealerprofile') else 'N/A'
    get_dealer_business_name.short_description = 'Business Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(dealer=request.user)
        return qs

@admin.register(WebhookEvent)
class WebhookEventAdmin(RoleBasedAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'event_type', 'status', 'retry_count', 'created_at']
    list_filter = ['event_type', 'status', 'created_at']
    search_fields = ['dealer__username', 'dealer__dealerprofile__business_name', 'event_type', 'external_id']
    fieldsets = (
        ('Event Information', {
            'fields': ('dealer', 'event_type', 'event_data', 'external_id', 'status')
        }),
        ('Retry Information', {
            'fields': ('error_message', 'retry_count', 'max_retries')
        }),
        ('Metadata', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'processed_at']
    autocomplete_fields = ['dealer']
    inlines = [WebhookLogInline]

    def get_dealer_business_name(self, obj):
        return obj.dealer.dealerprofile.business_name if hasattr(obj.dealer, 'dealerprofile') else 'N/A'
    get_dealer_business_name.short_description = 'Business Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(dealer=request.user)
        return qs

@admin.register(WebhookLog)
class WebhookLogAdmin(RoleBasedAdmin):
    list_display = ['webhook_event', 'get_event_dealer', 'request_url', 'response_status_code', 'execution_time_ms', 'created_at']
    list_filter = ['response_status_code', 'created_at']
    search_fields = ['webhook_event__event_type', 'request_url', 'webhook_event__dealer__username']
    fieldsets = (
        ('Event Information', {
            'fields': ('webhook_event',)
        }),
        ('Request Details', {
            'fields': ('request_url', 'request_headers', 'request_body')
        }),
        ('Response Details', {
            'fields': ('response_status_code', 'response_headers', 'response_body', 'execution_time_ms')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'response_headers', 'response_body', 'execution_time_ms']
    autocomplete_fields = ['webhook_event']

    def get_event_dealer(self, obj):
        return obj.webhook_event.dealer.username
    get_event_dealer.short_description = 'Dealer'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(webhook_event__dealer=request.user)
        return qs

@admin.register(Payment)
class PaymentAdmin(RoleBasedAdmin):
    list_display = ['booking', 'get_customer', 'get_dealer', 'transaction_id', 'payment_method', 'amount', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_gateway', 'created_at']
    search_fields = ['booking__id', 'transaction_id', 'booking__customer__username']
    fieldsets = (
        ('Payment Information', {
            'fields': ('booking', 'payment_gateway', 'transaction_id', 'payment_method', 'virtual_card', 'amount', 'currency', 'status')
        }),
        ('Response Details', {
            'fields': ('gateway_response', 'processed_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'processed_at']
    autocomplete_fields = ['booking', 'virtual_card']

    def get_customer(self, obj):
        return obj.booking.customer.username
    get_customer.short_description = 'Customer'
    
    def get_dealer(self, obj):
        return obj.booking.service_slot.service.dealer.username
    get_dealer.short_description = 'Dealer'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type:
            if user_type.user_type == 'customer':
                return qs.filter(booking__customer=request.user)
            elif user_type.user_type == 'dealer':
                return qs.filter(booking__service_slot__service__dealer=request.user)
        return qs

@admin.register(PayoutRequest)
class PayoutRequestAdmin(RoleBasedAdmin):
    list_display = ['dealer', 'get_dealer_business_name', 'amount', 'status', 'processed_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['dealer__username', 'dealer__dealerprofile__business_name', 'amount']
    fieldsets = (
        ('Payout Information', {
            'fields': ('dealer', 'amount', 'status', 'bank_details')
        }),
        ('Admin Details', {
            'fields': ('admin_notes', 'processed_by', 'processed_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'processed_at']
    autocomplete_fields = ['dealer', 'processed_by']

    def get_dealer_business_name(self, obj):
        return obj.dealer.dealerprofile.business_name if hasattr(obj.dealer, 'dealerprofile') else 'N/A'
    get_dealer_business_name.short_description = 'Business Name'
    
    def filter_queryset_by_user_type(self, request, qs):
        user_type = getattr(request.user, 'profile', None)
        if user_type and user_type.user_type == 'dealer':
            return qs.filter(dealer=request.user)
        return