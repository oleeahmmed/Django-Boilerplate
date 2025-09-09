from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
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

# =============================================================================
# CUSTOMER MANAGEMENT
# =============================================================================

class CustomerProfileViewSet(viewsets.ModelViewSet):
    """
    Customer Profile Management
    
    Manage customer profiles including personal details, preferences, and address information.
    Only customers can access their own profiles, admins can access all.
    """
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer | IsAdmin]

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="List Customer Profiles",
        operation_description="Retrieve list of customer profiles. Customers see only their own profile.",
        responses={200: CustomerProfileSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Create Customer Profile",
        operation_description="Create a new customer profile",
        request_body=CustomerProfileSerializer,
        responses={201: CustomerProfileSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Get Customer Profile",
        operation_description="Retrieve a specific customer profile by ID",
        responses={200: CustomerProfileSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Update Customer Profile",
        operation_description="Update customer profile information",
        request_body=CustomerProfileSerializer,
        responses={200: CustomerProfileSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Delete Customer Profile",
        operation_description="Delete a customer profile",
        responses={204: "Profile deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return CustomerProfile.objects.all()
        return CustomerProfile.objects.filter(user=user)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Get My Profile",
        operation_description="Get the current authenticated customer's profile",
        responses={200: CustomerProfileSerializer}
    )
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current customer's profile"""
        try:
            profile = CustomerProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response(
                {"error": "Customer profile not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class VehicleViewSet(viewsets.ModelViewSet):
    """
    Vehicle Management
    
    Manage customer vehicles including make, model, year, and identification details.
    Customers can manage their own vehicles, admins can manage all.
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="List Customer Vehicles",
        operation_description="Retrieve list of vehicles. Customers see only their own vehicles.",
        responses={200: VehicleSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Add New Vehicle",
        operation_description="Add a new vehicle to customer's account",
        request_body=VehicleSerializer,
        responses={201: VehicleSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Get Vehicle Details",
        operation_description="Retrieve specific vehicle information by ID",
        responses={200: VehicleSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Update Vehicle",
        operation_description="Update vehicle information",
        request_body=VehicleSerializer,
        responses={200: VehicleSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Delete Vehicle",
        operation_description="Remove a vehicle from customer's account",
        responses={204: "Vehicle deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Vehicle.objects.all()
        return Vehicle.objects.filter(owner=user)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Set Primary Vehicle",
        operation_description="Set a vehicle as the primary vehicle for the customer",
        responses={200: openapi.Response("Vehicle set as primary")}
    )
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set vehicle as primary"""
        vehicle = self.get_object()
        # Remove primary status from other vehicles
        Vehicle.objects.filter(owner=vehicle.owner, is_primary=True).update(is_primary=False)
        # Set this vehicle as primary
        vehicle.is_primary = True
        vehicle.save()
        return Response({"message": "Vehicle set as primary"})


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Review Management
    
    Manage customer reviews for completed bookings. Customers can view/create their reviews,
    dealers can view reviews about their services, admins can manage all reviews.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer | IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="List Reviews",
        operation_description="Retrieve reviews based on user role",
        responses={200: ReviewSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Create Review",
        operation_description="Create a new review for a completed booking",
        request_body=ReviewSerializer,
        responses={201: ReviewSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Get Review",
        operation_description="Retrieve specific review details",
        responses={200: ReviewSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Update Review",
        operation_description="Update review content and rating",
        request_body=ReviewSerializer,
        responses={200: ReviewSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Customer Management'],
        operation_summary="Delete Review",
        operation_description="Delete a review",
        responses={204: "Review deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Review.objects.all()
        if IsDealer().has_permission(self.request, self):
            return Review.objects.filter(dealer=user)
        return Review.objects.filter(customer=user)

# =============================================================================
# DEALER MANAGEMENT
# =============================================================================

class DealerProfileViewSet(viewsets.ModelViewSet):
    """
    Dealer Profile Management
    
    Manage dealer profiles including business information, banking details, and verification status.
    Only dealers can access their own profiles, admins can access all.
    """
    queryset = DealerProfile.objects.all()
    serializer_class = DealerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Dealer Profiles",
        operation_description="Retrieve list of dealer profiles. Dealers see only their own profile.",
        responses={200: DealerProfileSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Create Dealer Profile",
        operation_description="Create a new dealer profile",
        request_body=DealerProfileSerializer,
        responses={201: DealerProfileSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Dealer Profile",
        operation_description="Retrieve specific dealer profile by ID",
        responses={200: DealerProfileSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Update Dealer Profile",
        operation_description="Update dealer profile information",
        request_body=DealerProfileSerializer,
        responses={200: DealerProfileSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Delete Dealer Profile",
        operation_description="Delete a dealer profile",
        responses={204: "Profile deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return DealerProfile.objects.all()
        return DealerProfile.objects.filter(user=user)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get My Business Profile",
        operation_description="Get the current authenticated dealer's profile",
        responses={200: DealerProfileSerializer}
    )
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current dealer's profile"""
        try:
            profile = DealerProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except DealerProfile.DoesNotExist:
            return Response(
                {"error": "Dealer profile not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class DealerVerificationDocumentViewSet(viewsets.ModelViewSet):
    """
    Dealer Verification Document Management
    
    Manage dealer verification documents for business approval process.
    Dealers can manage their own documents, admins can review all documents.
    """
    queryset = DealerVerificationDocument.objects.all()
    serializer_class = DealerVerificationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Verification Documents",
        operation_description="Retrieve dealer verification documents",
        responses={200: DealerVerificationDocumentSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Upload Verification Document",
        operation_description="Upload a new verification document",
        request_body=DealerVerificationDocumentSerializer,
        responses={201: DealerVerificationDocumentSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Verification Document",
        operation_description="Retrieve specific verification document",
        responses={200: DealerVerificationDocumentSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Update Verification Document",
        operation_description="Update verification document information",
        request_body=DealerVerificationDocumentSerializer,
        responses={200: DealerVerificationDocumentSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Delete Verification Document",
        operation_description="Remove a verification document",
        responses={204: "Document deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return DealerVerificationDocument.objects.all()
        return DealerVerificationDocument.objects.filter(dealer__user=user)


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """
    Service Category Management
    
    Manage service categories for organizing different types of car detailing services.
    Read-only for dealers and customers, full access for admins.
    """
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Service Categories",
        operation_description="Retrieve all available service categories",
        responses={200: ServiceCategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Create Service Category",
        operation_description="Create a new service category (Admin only)",
        request_body=ServiceCategorySerializer,
        responses={201: ServiceCategorySerializer}
    )
    def create(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only admins can create service categories"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Service Category",
        operation_description="Retrieve specific service category details",
        responses={200: ServiceCategorySerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Update Service Category",
        operation_description="Update service category information (Admin only)",
        request_body=ServiceCategorySerializer,
        responses={200: ServiceCategorySerializer}
    )
    def update(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only admins can update service categories"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Delete Service Category",
        operation_description="Delete a service category (Admin only)",
        responses={204: "Category deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only admins can delete service categories"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Service Management
    
    Manage car detailing services offered by dealers. Dealers can manage their own services,
    customers can view available services, admins can manage all services.
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Services",
        operation_description="Retrieve services based on user role",
        responses={200: ServiceSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Create Service",
        operation_description="Create a new service offering (Dealer/Admin only)",
        request_body=ServiceSerializer,
        responses={201: ServiceSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Service Details",
        operation_description="Retrieve specific service information",
        responses={200: ServiceSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Update Service",
        operation_description="Update service information",
        request_body=ServiceSerializer,
        responses={200: ServiceSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Delete Service",
        operation_description="Remove a service offering",
        responses={204: "Service deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Service.objects.all()
        if IsDealer().has_permission(self.request, self):
            return Service.objects.filter(dealer=user)
        # Customers can view all active services
        return Service.objects.filter(is_active=True)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Search Services",
        operation_description="Search services by name, description, or category",
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="Search query", type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="Filter by category ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price filter", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price filter", type=openapi.TYPE_NUMBER),
        ],
        responses={200: ServiceSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search and filter services"""
        queryset = self.get_queryset()
        
        # Search query
        query = request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        # Category filter
        category = request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Price filters
        min_price = request.query_params.get('min_price', None)
        if min_price:
            queryset = queryset.filter(base_price__gte=min_price)
            
        max_price = request.query_params.get('max_price', None)
        if max_price:
            queryset = queryset.filter(base_price__lte=max_price)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ServiceAvailabilityViewSet(viewsets.ModelViewSet):
    """
    Service Availability Management
    
    Manage when and where services are available. Dealers can manage their service availability,
    admins can manage all availability settings.
    """
    queryset = ServiceAvailability.objects.all()
    serializer_class = ServiceAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Service Availability",
        operation_description="Retrieve service availability schedules",
        responses={200: ServiceAvailabilitySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Create Service Availability",
        operation_description="Set up new availability schedule for a service",
        request_body=ServiceAvailabilitySerializer,
        responses={201: ServiceAvailabilitySerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Service Availability",
        operation_description="Retrieve specific availability schedule",
        responses={200: ServiceAvailabilitySerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Update Service Availability",
        operation_description="Update availability schedule",
        request_body=ServiceAvailabilitySerializer,
        responses={200: ServiceAvailabilitySerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Delete Service Availability",
        operation_description="Remove an availability schedule",
        responses={204: "Availability deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return ServiceAvailability.objects.all()
        return ServiceAvailability.objects.filter(service__dealer=user)


class ServiceSlotViewSet(viewsets.ModelViewSet):
    """
    Service Slot Management
    
    Manage specific time slots for service bookings. Dealers can manage their service slots,
    customers can view available slots, admins can manage all slots.
    """
    queryset = ServiceSlot.objects.all()
    serializer_class = ServiceSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Service Slots",
        operation_description="Retrieve service slots based on user role",
        responses={200: ServiceSlotSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Create Service Slot",
        operation_description="Create a new bookable time slot (Dealer/Admin only)",
        request_body=ServiceSlotSerializer,
        responses={201: ServiceSlotSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Service Slot",
        operation_description="Retrieve specific slot details",
        responses={200: ServiceSlotSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Update Service Slot",
        operation_description="Update slot information and availability",
        request_body=ServiceSlotSerializer,
        responses={200: ServiceSlotSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Delete Service Slot",
        operation_description="Remove a service slot",
        responses={204: "Slot deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return ServiceSlot.objects.all()
        if IsDealer().has_permission(self.request, self):
            return ServiceSlot.objects.filter(service__dealer=user)
        # Customers can view all available slots
        return ServiceSlot.objects.filter(is_available=True)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Available Slots",
        operation_description="Get available slots for a specific service",
        manual_parameters=[
            openapi.Parameter('service_id', openapi.IN_QUERY, description="Service ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        ],
        responses={200: ServiceSlotSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available slots for booking"""
        service_id = request.query_params.get('service_id')
        date = request.query_params.get('date')
        
        if not service_id:
            return Response(
                {"error": "service_id parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = ServiceSlot.objects.filter(
            service_id=service_id,
            is_available=True
        )
        
        if date:
            queryset = queryset.filter(start_time__date=date)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CommissionHistoryViewSet(viewsets.ModelViewSet):
    """
    Commission History Management
    
    Track commission rate changes for dealers over time.
    Dealers can view their own commission history, admins can manage all.
    """
    queryset = CommissionHistory.objects.all()
    serializer_class = CommissionHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="List Commission History",
        operation_description="Retrieve commission rate change history",
        responses={200: CommissionHistorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Create Commission Record",
        operation_description="Record a commission rate change (Admin only)",
        request_body=CommissionHistorySerializer,
        responses={201: CommissionHistorySerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Dealer Management'],
        operation_summary="Get Commission Record",
        operation_description="Retrieve specific commission history entry",
        responses={200: CommissionHistorySerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return CommissionHistory.objects.all()
        return CommissionHistory.objects.filter(dealer__user=user)

# =============================================================================
# BOOKING & PAYMENT FLOW
# =============================================================================

class BookingViewSet(viewsets.ModelViewSet):
    """
    Booking Management
    
    Manage service bookings throughout their lifecycle from creation to completion.
    All authenticated users can interact with bookings based on their role.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer | IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="List Bookings",
        operation_description="Retrieve bookings based on user role and filters",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by booking status", type=openapi.TYPE_STRING),
            openapi.Parameter('source', openapi.IN_QUERY, description="Filter by booking source (app/external)", type=openapi.TYPE_STRING),
        ],
        responses={200: BookingSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Create Booking",
        operation_description="Create a new service booking",
        request_body=BookingSerializer,
        responses={201: BookingSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Get Booking Details",
        operation_description="Retrieve specific booking information",
        responses={200: BookingSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Update Booking",
        operation_description="Update booking information",
        request_body=BookingSerializer,
        responses={200: BookingSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Cancel Booking",
        operation_description="Cancel a booking",
        responses={204: "Booking cancelled successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.all()
        
        if IsAdmin().has_permission(self.request, self):
            queryset = Booking.objects.all()
        elif IsDealer().has_permission(self.request, self):
            queryset = Booking.objects.filter(service_slot__service__dealer=user)
        else:
            queryset = Booking.objects.filter(customer=user)
        
        # Apply filters
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
            
        source = self.request.query_params.get('source', None)
        if source:
            queryset = queryset.filter(source=source)
            
        return queryset

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Accept Booking",
        operation_description="Dealer accepts a pending booking",
        responses={200: openapi.Response("Booking accepted")}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsDealer | IsAdmin])
    def accept(self, request, pk=None):
        """Dealer accepts booking"""
        booking = self.get_object()
        if booking.status != 'pending':
            return Response(
                {"error": "Only pending bookings can be accepted"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'confirmed'
        booking.save()
        return Response({"message": "Booking accepted successfully"})

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Reject Booking",
        operation_description="Dealer rejects a pending booking",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'reason': openapi.Schema(type=openapi.TYPE_STRING)},
            required=['reason']
        ),
        responses={200: openapi.Response("Booking rejected")}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsDealer | IsAdmin])
    def reject(self, request, pk=None):
        """Dealer rejects booking"""
        booking = self.get_object()
        reason = request.data.get('reason', '')
        
        if booking.status != 'pending':
            return Response(
                {"error": "Only pending bookings can be rejected"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'rejected'
        booking.cancellation_reason = reason
        booking.save()
        return Response({"message": "Booking rejected successfully"})

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Mark In Progress",
        operation_description="Mark booking as in progress",
        responses={200: openapi.Response("Booking marked in progress")}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsDealer | IsAdmin])
    def start_service(self, request, pk=None):
        """Mark booking as in progress"""
        booking = self.get_object()
        if booking.status != 'confirmed':
            return Response(
                {"error": "Only confirmed bookings can be started"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'in_progress'
        booking.save()
        return Response({"message": "Service started successfully"})

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Complete Booking",
        operation_description="Mark booking as completed",
        responses={200: openapi.Response("Booking completed")}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsDealer | IsAdmin])
    def complete(self, request, pk=None):
        """Mark booking as completed"""
        booking = self.get_object()
        if booking.status != 'in_progress':
            return Response(
                {"error": "Only in-progress bookings can be completed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'completed'
        booking.save()
        return Response({"message": "Booking completed successfully"})


class PromotionViewSet(viewsets.ModelViewSet):
    """
    Promotion Management
    
    Manage discount promotions and coupon codes for bookings.
    Customers can view active promotions, admins can manage all promotions.
    """
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="List Promotions",
        operation_description="Retrieve available promotions",
        responses={200: PromotionSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Create Promotion",
        operation_description="Create a new promotion (Admin only)",
        request_body=PromotionSerializer,
        responses={201: PromotionSerializer}
    )
    def create(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only admins can create promotions"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Get Promotion Details",
        operation_description="Retrieve specific promotion information",
        responses={200: PromotionSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Update Promotion",
        operation_description="Update promotion details (Admin only)",
        request_body=PromotionSerializer,
        responses={200: PromotionSerializer}
    )
    def update(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only admins can update promotions"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Delete Promotion",
        operation_description="Remove a promotion (Admin only)",
        responses={204: "Promotion deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only admins can delete promotions"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        if IsAdmin().has_permission(self.request, self):
            return Promotion.objects.all()
        # Non-admins see only active promotions
        return Promotion.objects.filter(is_active=True)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Validate Promotion Code",
        operation_description="Check if a promotion code is valid and available",
        manual_parameters=[
            openapi.Parameter('code', openapi.IN_QUERY, description="Promotion code", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response("Promotion is valid", PromotionSerializer),
            400: openapi.Response("Invalid or expired promotion code")
        }
    )
    @action(detail=False, methods=['get'])
    def validate_code(self, request):
        """Validate promotion code"""
        code = request.query_params.get('code')
        if not code:
            return Response(
                {"error": "Promotion code is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            promotion = Promotion.objects.get(
                code=code,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
            
            # Check usage limits
            if promotion.max_uses and promotion.current_uses >= promotion.max_uses:
                return Response(
                    {"error": "Promotion code usage limit exceeded"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = self.get_serializer(promotion)
            return Response(serializer.data)
            
        except Promotion.DoesNotExist:
            return Response(
                {"error": "Invalid or expired promotion code"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment Management
    
    Manage payment records and transactions for bookings.
    Admins can view all payments, dealers and customers can view their related payments.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="List Payments",
        operation_description="Retrieve payment records based on user role",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by payment status", type=openapi.TYPE_STRING),
            openapi.Parameter('payment_method', openapi.IN_QUERY, description="Filter by payment method", type=openapi.TYPE_STRING),
        ],
        responses={200: PaymentSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Create Payment Record",
        operation_description="Create a new payment record (System use)",
        request_body=PaymentSerializer,
        responses={201: PaymentSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Get Payment Details",
        operation_description="Retrieve specific payment information",
        responses={200: PaymentSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Update Payment",
        operation_description="Update payment status and information",
        request_body=PaymentSerializer,
        responses={200: PaymentSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.all()
        
        if IsAdmin().has_permission(self.request, self):
            queryset = Payment.objects.all()
        elif IsDealer().has_permission(self.request, self):
            queryset = Payment.objects.filter(booking__service_slot__service__dealer=user)
        else:
            queryset = Payment.objects.filter(booking__customer=user)
        
        # Apply filters
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
            
        payment_method = self.request.query_params.get('payment_method', None)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
            
        return queryset


class VirtualCardViewSet(viewsets.ModelViewSet):
    """
    Virtual Card Management
    
    Manage dealer virtual cards for cash payment processing.
    Dealers can manage their own virtual cards, admins can manage all.
    """
    queryset = VirtualCard.objects.all()
    serializer_class = VirtualCardSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="List Virtual Cards",
        operation_description="Retrieve virtual card information",
        responses={200: VirtualCardSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Create Virtual Card",
        operation_description="Create a new virtual card for dealer",
        request_body=VirtualCardSerializer,
        responses={201: VirtualCardSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Get Virtual Card",
        operation_description="Retrieve virtual card details",
        responses={200: VirtualCardSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Update Virtual Card",
        operation_description="Update virtual card information",
        request_body=VirtualCardSerializer,
        responses={200: VirtualCardSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Deactivate Virtual Card",
        operation_description="Deactivate a virtual card",
        responses={204: "Virtual card deactivated"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return VirtualCard.objects.all()
        return VirtualCard.objects.filter(dealer=user)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Top Up Virtual Card",
        operation_description="Add funds to virtual card balance",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'amount': openapi.Schema(type=openapi.TYPE_NUMBER)},
            required=['amount']
        ),
        responses={200: openapi.Response("Card topped up successfully")}
    )
    @action(detail=True, methods=['post'])
    def top_up(self, request, pk=None):
        """Add funds to virtual card"""
        card = self.get_object()
        amount = request.data.get('amount')
        
        if not amount or amount <= 0:
            return Response(
                {"error": "Valid amount is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        card.balance += float(amount)
        card.save()
        
        return Response({
            "message": "Card topped up successfully",
            "new_balance": card.balance
        })


class PayoutRequestViewSet(viewsets.ModelViewSet):
    """
    Payout Request Management
    
    Manage dealer payout requests for withdrawing earnings.
    Dealers can create and view their payout requests, admins can process all requests.
    """
    queryset = PayoutRequest.objects.all()
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="List Payout Requests",
        operation_description="Retrieve payout requests based on user role",
        responses={200: PayoutRequestSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Create Payout Request",
        operation_description="Create a new payout request",
        request_body=PayoutRequestSerializer,
        responses={201: PayoutRequestSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Get Payout Request",
        operation_description="Retrieve specific payout request details",
        responses={200: PayoutRequestSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Update Payout Request",
        operation_description="Update payout request information",
        request_body=PayoutRequestSerializer,
        responses={200: PayoutRequestSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Cancel Payout Request",
        operation_description="Cancel a pending payout request",
        responses={204: "Payout request cancelled"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return PayoutRequest.objects.all()
        return PayoutRequest.objects.filter(dealer=user)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Approve Payout",
        operation_description="Approve a payout request (Admin only)",
        responses={200: openapi.Response("Payout approved")}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        """Approve payout request"""
        payout = self.get_object()
        if payout.status != 'pending':
            return Response(
                {"error": "Only pending payouts can be approved"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payout.status = 'approved'
        payout.processed_by = request.user
        payout.processed_at = timezone.now()
        payout.save()
        
        return Response({"message": "Payout approved successfully"})

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Reject Payout",
        operation_description="Reject a payout request (Admin only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'reason': openapi.Schema(type=openapi.TYPE_STRING)},
            required=['reason']
        ),
        responses={200: openapi.Response("Payout rejected")}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def reject(self, request, pk=None):
        """Reject payout request"""
        payout = self.get_object()
        reason = request.data.get('reason', '')
        
        if payout.status != 'pending':
            return Response(
                {"error": "Only pending payouts can be rejected"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payout.status = 'rejected'
        payout.admin_notes = reason
        payout.processed_by = request.user
        payout.processed_at = timezone.now()
        payout.save()
        
        return Response({"message": "Payout rejected successfully"})


class BalanceTransactionViewSet(viewsets.ModelViewSet):
    """
    Balance Transaction History
    
    Track all balance changes for dealers including bookings, payouts, and adjustments.
    Dealers can view their own transaction history, admins can view all transactions.
    """
    queryset = BalanceTransaction.objects.all()
    serializer_class = BalanceTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="List Balance Transactions",
        operation_description="Retrieve balance transaction history",
        manual_parameters=[
            openapi.Parameter('transaction_type', openapi.IN_QUERY, description="Filter by transaction type", type=openapi.TYPE_STRING),
        ],
        responses={200: BalanceTransactionSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Booking & Payment Flow'],
        operation_summary="Get Transaction Details",
        operation_description="Retrieve specific transaction information",
        responses={200: BalanceTransactionSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = BalanceTransaction.objects.all()
        
        if IsAdmin().has_permission(self.request, self):
            queryset = BalanceTransaction.objects.all()
        else:
            queryset = BalanceTransaction.objects.filter(dealer__user=user)
        
        # Apply filters
        transaction_type = self.request.query_params.get('transaction_type', None)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset.order_by('-created_at')

# =============================================================================
# INTEGRATION & AUTOMATION
# =============================================================================

class WebhookConfigurationViewSet(viewsets.ModelViewSet):
    """
    Webhook Configuration Management
    
    Manage webhook endpoints for external website integration.
    Dealers can configure webhooks for their services, admins can manage all webhooks.
    """
    queryset = WebhookConfiguration.objects.all()
    serializer_class = WebhookConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="List Webhook Configurations",
        operation_description="Retrieve webhook configuration settings",
        responses={200: WebhookConfigurationSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Create Webhook Configuration",
        operation_description="Set up new webhook endpoint",
        request_body=WebhookConfigurationSerializer,
        responses={201: WebhookConfigurationSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Webhook Configuration",
        operation_description="Retrieve specific webhook configuration",
        responses={200: WebhookConfigurationSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Update Webhook Configuration",
        operation_description="Update webhook endpoint settings",
        request_body=WebhookConfigurationSerializer,
        responses={200: WebhookConfigurationSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Delete Webhook Configuration",
        operation_description="Remove webhook configuration",
        responses={204: "Webhook configuration deleted"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return WebhookConfiguration.objects.all()
        return WebhookConfiguration.objects.filter(dealer=user)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Test Webhook",
        operation_description="Send test webhook to verify configuration",
        responses={200: openapi.Response("Webhook test sent successfully")}
    )
    @action(detail=True, methods=['post'])
    def test_webhook(self, request, pk=None):
        """Send test webhook"""
        webhook_config = self.get_object()
        
        # Here you would implement the actual webhook sending logic
        # For now, we'll just return a success response
        
        return Response({
            "message": "Test webhook sent successfully",
            "endpoint": webhook_config.endpoint_url
        })


class WebhookEventViewSet(viewsets.ModelViewSet):
    """
    Webhook Event Management
    
    Manage webhook events and their delivery status.
    Dealers can view events for their webhooks, admins can view all events.
    """
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsDealer | IsAdmin]

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="List Webhook Events",
        operation_description="Retrieve webhook event history",
        manual_parameters=[
            openapi.Parameter('event_type', openapi.IN_QUERY, description="Filter by event type", type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by delivery status", type=openapi.TYPE_STRING),
        ],
        responses={200: WebhookEventSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Webhook Event",
        operation_description="Retrieve specific webhook event details",
        responses={200: WebhookEventSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = WebhookEvent.objects.all()
        
        if IsAdmin().has_permission(self.request, self):
            queryset = WebhookEvent.objects.all()
        else:
            queryset = WebhookEvent.objects.filter(dealer=user)
        
        # Apply filters
        event_type = self.request.query_params.get('event_type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
            
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Retry Webhook Event",
        operation_description="Retry failed webhook delivery",
        responses={200: openapi.Response("Webhook retry initiated")}
    )
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry webhook event delivery"""
        webhook_event = self.get_object()
        
        if webhook_event.status not in ['failed', 'pending']:
            return Response(
                {"error": "Only failed or pending webhooks can be retried"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if webhook_event.retry_count >= webhook_event.max_retries:
            return Response(
                {"error": "Maximum retry attempts exceeded"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Here you would implement the actual webhook retry logic
        webhook_event.retry_count += 1
        webhook_event.status = 'pending'
        webhook_event.save()
        
        return Response({"message": "Webhook retry initiated successfully"})


class WebhookLogViewSet(viewsets.ModelViewSet):
    """
    Webhook Log Management
    
    View detailed logs of webhook delivery attempts including request/response data.
    Admin-only access for debugging and monitoring webhook deliveries.
    """
    queryset = WebhookLog.objects.all()
    serializer_class = WebhookLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="List Webhook Logs",
        operation_description="Retrieve detailed webhook delivery logs with request/response data",
        manual_parameters=[
            openapi.Parameter('webhook_event', openapi.IN_QUERY, description="Filter by webhook event ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('status_code', openapi.IN_QUERY, description="Filter by HTTP response status code", type=openapi.TYPE_INTEGER),
        ],
        responses={200: WebhookLogSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Webhook Log Details",
        operation_description="Retrieve specific webhook delivery log with full request/response data",
        responses={200: WebhookLogSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        queryset = WebhookLog.objects.all()
        
        # Apply filters
        webhook_event = self.request.query_params.get('webhook_event', None)
        if webhook_event:
            queryset = queryset.filter(webhook_event_id=webhook_event)
            
        status_code = self.request.query_params.get('status_code', None)
        if status_code:
            queryset = queryset.filter(response_status_code=status_code)
            
        return queryset.order_by('-created_at')

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Failed Deliveries",
        operation_description="Get logs of failed webhook deliveries for troubleshooting",
        responses={200: WebhookLogSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def failed_deliveries(self, request):
        """Get failed webhook deliveries"""
        queryset = WebhookLog.objects.filter(
            response_status_code__gte=400
        ).order_by('-created_at')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Delivery Statistics",
        operation_description="Get webhook delivery success/failure statistics",
        responses={200: openapi.Response("Delivery statistics")}
    )
    @action(detail=False, methods=['get'])
    def delivery_stats(self, request):
        """Get webhook delivery statistics"""
        from django.db.models import Count, Q
        
        stats = WebhookLog.objects.aggregate(
            total_deliveries=Count('id'),
            successful_deliveries=Count('id', filter=Q(response_status_code__lt=400)),
            failed_deliveries=Count('id', filter=Q(response_status_code__gte=400)),
            avg_execution_time=Avg('execution_time_ms')
        )
        
        success_rate = 0
        if stats['total_deliveries'] > 0:
            success_rate = (stats['successful_deliveries'] / stats['total_deliveries']) * 100
        
        return Response({
            **stats,
            'success_rate_percentage': round(success_rate, 2)
        })
        
        
# Add this to your views.py file in the Integration & Automation section

from django.utils import timezone
from django.db.models import Avg

class NotificationViewSet(viewsets.ModelViewSet):
    """
    Notification Management
    
    Manage system notifications for users including booking updates, payment confirmations,
    and system alerts. Users can view and manage their own notifications.
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="List Notifications",
        operation_description="Retrieve user notifications",
        manual_parameters=[
            openapi.Parameter('is_read', openapi.IN_QUERY, description="Filter by read status", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: NotificationSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Create Notification",
        operation_description="Create a new notification (System use)",
        request_body=NotificationSerializer,
        responses={201: NotificationSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Notification",
        operation_description="Retrieve specific notification details",
        responses={200: NotificationSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Update Notification",
        operation_description="Update notification read status",
        request_body=NotificationSerializer,
        responses={200: NotificationSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Delete Notification",
        operation_description="Remove a notification",
        responses={204: "Notification deleted successfully"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        
        # Apply filters
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            is_read = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read)
            
        return queryset.order_by('-created_at')

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Mark as Read",
        operation_description="Mark notification as read",
        responses={200: openapi.Response("Notification marked as read")}
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"message": "Notification marked as read"})

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Mark as Unread",
        operation_description="Mark notification as unread",
        responses={200: openapi.Response("Notification marked as unread")}
    )
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark notification as unread"""
        notification = self.get_object()
        notification.is_read = False
        notification.save()
        return Response({"message": "Notification marked as unread"})

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Mark All as Read",
        operation_description="Mark all user notifications as read",
        responses={200: openapi.Response("All notifications marked as read")}
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            "message": f"{count} notifications marked as read"
        })

    @swagger_auto_schema(
        tags=['Integration & Automation'],
        operation_summary="Get Unread Count",
        operation_description="Get count of unread notifications",
        responses={200: openapi.Response("Unread notification count")}
    )
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({"unread_count": count})        