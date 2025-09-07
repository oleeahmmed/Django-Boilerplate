from rest_framework.routers import DefaultRouter
from .views import (
    CustomerProfileViewSet,
    DealerProfileViewSet,
    VehicleViewSet,
    ServiceCategoryViewSet,
    ServiceViewSet,
    ServiceAvailabilityViewSet,
    ServiceSlotViewSet,
    PromotionViewSet,
    BookingViewSet,
    WebhookConfigurationViewSet,
    WebhookEventViewSet,
    WebhookLogViewSet,
    PaymentViewSet,
    PayoutRequestViewSet,
    VirtualCardViewSet,
    BalanceTransactionViewSet,
    NotificationViewSet,
    ReviewViewSet,
    DealerVerificationDocumentViewSet,
    CommissionHistoryViewSet,
)

router = DefaultRouter()
router.register(r'customer-profiles', CustomerProfileViewSet, basename='customerprofile')
router.register(r'dealer-profiles', DealerProfileViewSet, basename='dealerprofile')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'service-categories', ServiceCategoryViewSet, basename='servicecategory')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-availabilities', ServiceAvailabilityViewSet, basename='serviceavailability')
router.register(r'service-slots', ServiceSlotViewSet, basename='serviceslot')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'webhook-configurations', WebhookConfigurationViewSet, basename='webhookconfiguration')
router.register(r'webhook-events', WebhookEventViewSet, basename='webhookevent')
router.register(r'webhook-logs', WebhookLogViewSet, basename='webhooklog')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'payout-requests', PayoutRequestViewSet, basename='payoutrequest')
router.register(r'virtual-cards', VirtualCardViewSet, basename='virtualcard')
router.register(r'balance-transactions', BalanceTransactionViewSet, basename='balancetransaction')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'dealer-verification-documents', DealerVerificationDocumentViewSet, basename='dealerverificationdocument')
router.register(r'commission-history', CommissionHistoryViewSet, basename='commissionhistory')

urlpatterns = router.urls