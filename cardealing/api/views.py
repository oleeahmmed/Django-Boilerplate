from rest_framework import viewsets, permissions
from .serializers import (
    CustomerProfileSerializer,
    DealerProfileSerializer,
    VehicleSerializer,
    ServiceCategorySerializer,
    ServiceSerializer,
    ServiceAvailabilitySerializer,
    ServiceSlotSerializer,
    PromotionSerializer,
    BookingSerializer,
    WebhookConfigurationSerializer,
    WebhookEventSerializer,
    WebhookLogSerializer,
    PaymentSerializer,
    PayoutRequestSerializer,
    VirtualCardSerializer,
    BalanceTransactionSerializer,
    NotificationSerializer,
    ReviewSerializer,
    DealerVerificationDocumentSerializer,
    CommissionHistorySerializer,
)
from cardealing.models import (
    CustomerProfile,
    DealerProfile,
    Vehicle,
    ServiceCategory,
    Service,
    ServiceAvailability,
    ServiceSlot,
    Booking,
    Promotion,
    WebhookConfiguration,
    WebhookEvent,
    WebhookLog,
    Payment,
    PayoutRequest,
    VirtualCard,
    BalanceTransaction,
    Notification,
    Review,
    DealerVerificationDocument,
    CommissionHistory,
)
from .permissions import IsAdmin, IsDealer, IsCustomer, IsOwnerOrAdmin

class CustomerProfileViewSet(viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer | IsAdmin]

class DealerProfileViewSet(viewsets.ModelViewSet):
    queryset = DealerProfile.objects.all()
    serializer_class = DealerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Vehicle.objects.all()
        return Vehicle.objects.filter(owner=user)

class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Service.objects.all()
        return Service.objects.filter(dealer=user)

class ServiceAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = ServiceAvailability.objects.all()
    serializer_class = ServiceAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return ServiceAvailability.objects.all()
        return ServiceAvailability.objects.filter(service__dealer=user)

class ServiceSlotViewSet(viewsets.ModelViewSet):
    queryset = ServiceSlot.objects.all()
    serializer_class = ServiceSlotSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return ServiceSlot.objects.all()
        return ServiceSlot.objects.filter(service__dealer=user)

class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer | IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Booking.objects.all()
        if IsDealer().has_permission(self.request, self):
            return Booking.objects.filter(service_slot__service__dealer=user)
        return Booking.objects.filter(customer=user)

class WebhookConfigurationViewSet(viewsets.ModelViewSet):
    queryset = WebhookConfiguration.objects.all()
    serializer_class = WebhookConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return WebhookConfiguration.objects.all()
        return WebhookConfiguration.objects.filter(dealer=user)

class WebhookEventViewSet(viewsets.ModelViewSet):
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return WebhookEvent.objects.all()
        return WebhookEvent.objects.filter(dealer=user)

class WebhookLogViewSet(viewsets.ModelViewSet):
    queryset = WebhookLog.objects.all()
    serializer_class = WebhookLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

class PayoutRequestViewSet(viewsets.ModelViewSet):
    queryset = PayoutRequest.objects.all()
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return PayoutRequest.objects.all()
        return PayoutRequest.objects.filter(dealer=user)

class VirtualCardViewSet(viewsets.ModelViewSet):
    queryset = VirtualCard.objects.all()
    serializer_class = VirtualCardSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return VirtualCard.objects.all()
        return VirtualCard.objects.filter(dealer=user)

class BalanceTransactionViewSet(viewsets.ModelViewSet):
    queryset = BalanceTransaction.objects.all()
    serializer_class = BalanceTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return BalanceTransaction.objects.all()
        return BalanceTransaction.objects.filter(dealer__user=user)

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer | IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Review.objects.all()
        if IsDealer().has_permission(self.request, self):
            return Review.objects.filter(dealer=user)
        return Review.objects.filter(customer=user)

class DealerVerificationDocumentViewSet(viewsets.ModelViewSet):
    queryset = DealerVerificationDocument.objects.all()
    serializer_class = DealerVerificationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return DealerVerificationDocument.objects.all()
        return DealerVerificationDocument.objects.filter(dealer__user=user)

class CommissionHistoryViewSet(viewsets.ModelViewSet):
    queryset = CommissionHistory.objects.all()
    serializer_class = CommissionHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return CommissionHistory.objects.all()
        return CommissionHistory.objects.filter(dealer__user=user)