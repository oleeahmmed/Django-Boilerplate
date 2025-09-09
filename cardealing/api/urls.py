from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Customer Management
    CustomerProfileViewSet,
    VehicleViewSet,
    ReviewViewSet,
    
    # Dealer Management
    DealerProfileViewSet,
    DealerVerificationDocumentViewSet,
    ServiceCategoryViewSet,
    ServiceViewSet,
    ServiceAvailabilityViewSet,
    ServiceSlotViewSet,
    CommissionHistoryViewSet,
    
    # Booking & Payment Flow
    BookingViewSet,
    PromotionViewSet,
    PaymentViewSet,
    VirtualCardViewSet,
    PayoutRequestViewSet,
    BalanceTransactionViewSet,
    
    # Integration & Automation
    WebhookConfigurationViewSet,
    WebhookEventViewSet,
    WebhookLogViewSet,
    NotificationViewSet,
)

# Create separate routers for each category
customer_router = DefaultRouter()
dealer_router = DefaultRouter()
booking_router = DefaultRouter()
integration_router = DefaultRouter()

# =============================================================================
# CUSTOMER MANAGEMENT ROUTES
# =============================================================================
customer_router.register(r'profiles', CustomerProfileViewSet, basename='customer-profile')
customer_router.register(r'vehicles', VehicleViewSet, basename='customer-vehicle')
customer_router.register(r'reviews', ReviewViewSet, basename='customer-review')

# =============================================================================
# DEALER MANAGEMENT ROUTES
# =============================================================================
dealer_router.register(r'profiles', DealerProfileViewSet, basename='dealer-profile')
dealer_router.register(r'verification-documents', DealerVerificationDocumentViewSet, basename='dealer-verification')
dealer_router.register(r'service-categories', ServiceCategoryViewSet, basename='service-category')
dealer_router.register(r'services', ServiceViewSet, basename='dealer-service')
dealer_router.register(r'service-availabilities', ServiceAvailabilityViewSet, basename='service-availability')
dealer_router.register(r'service-slots', ServiceSlotViewSet, basename='service-slot')
dealer_router.register(r'commission-history', CommissionHistoryViewSet, basename='commission-history')

# =============================================================================
# BOOKING & PAYMENT FLOW ROUTES
# =============================================================================
booking_router.register(r'bookings', BookingViewSet, basename='booking')
booking_router.register(r'promotions', PromotionViewSet, basename='promotion')
booking_router.register(r'payments', PaymentViewSet, basename='payment')
booking_router.register(r'virtual-cards', VirtualCardViewSet, basename='virtual-card')
booking_router.register(r'payout-requests', PayoutRequestViewSet, basename='payout-request')
booking_router.register(r'balance-transactions', BalanceTransactionViewSet, basename='balance-transaction')

# =============================================================================
# INTEGRATION & AUTOMATION ROUTES
# =============================================================================
integration_router.register(r'webhook-configurations', WebhookConfigurationViewSet, basename='webhook-config')
integration_router.register(r'webhook-events', WebhookEventViewSet, basename='webhook-event')
integration_router.register(r'webhook-logs', WebhookLogViewSet, basename='webhook-log')
integration_router.register(r'notifications', NotificationViewSet, basename='notification')

# =============================================================================
# URL PATTERNS
# =============================================================================
urlpatterns = [
    # Customer Management APIs
    path('customer/', include((customer_router.urls, 'customer'), namespace='customer')),
    
    # Dealer Management APIs
    path('dealer/', include((dealer_router.urls, 'dealer'), namespace='dealer')),
    
    # Booking & Payment APIs
    path('booking/', include((booking_router.urls, 'booking'), namespace='booking')),
    
    # Integration & Automation APIs
    path('integration/', include((integration_router.urls, 'integration'), namespace='integration')),
]