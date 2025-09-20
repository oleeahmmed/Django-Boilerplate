from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.utils.functional import lazy
from django.conf import settings

static_lazy = lazy(static, str)

def get_navigation_for_user(request):
    """Return navigation based on user type"""
    user = request.user
    
    # Check if user has a profile to determine user type
    user_type = 'admin'  # default
    if hasattr(user, 'profile'):
        user_type = user.profile.user_type
    elif user.is_superuser:
        user_type = 'admin'
    
    if user_type == 'admin' or user.is_superuser:
        return get_admin_navigation()
    elif user_type == 'customer':
        return get_customer_navigation()
    elif user_type == 'dealer':
        return get_dealer_navigation()
    else:
        return get_admin_navigation()  # fallback

def get_admin_navigation():
    """Admin navigation with complete system oversight"""
    return [
        {
            "title": _("Dashboard"),
            "separator": True,
            "items": [
                {
                    "title": _("Main Dashboard"),
                    "icon": "dashboard",
                    "link": "/admin/",
                },
            ],
        },

        
            {
                "title": _("Authentication"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "people",
                        "link": "/admin/auth/user/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": "/admin/auth/group/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Permissions"),
                        "icon": "lock",
                        "link": "/admin/auth/permission/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },

            {
                "title": _("Core Management"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Companies"),
                        "icon": "business",
                        "link": "/admin/core/company/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            
            {
                "title": _("Social Accounts"),
                "separator": True,
                "collapsible": True,
                "items": [
                    
                    {
                        "title": _("Sites"),
                        "icon": "language",  
                        "link": reverse_lazy("admin:sites_site_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Social Accounts"),
                        "icon": "account_circle",
                        "link": reverse_lazy("admin:socialaccount_socialaccount_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Social Tokens"),
                        "icon": "vpn_key",
                        "link": reverse_lazy("admin:socialaccount_socialtoken_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Social Apps"),
                        "icon": "apps",
                        "link": reverse_lazy("admin:socialaccount_socialapp_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },         
        {
            "title": _("Customer Management"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Customer Profiles"),
                    "icon": "person",
                    "link": reverse_lazy("admin:cardealing_customerprofile_changelist"),
                },
                {
                    "title": _("Customer Vehicles"),
                    "icon": "directions_car",
                    "link": reverse_lazy("admin:cardealing_vehicle_changelist"),
                },
                {
                    "title": _("Customer Bookings"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
                {
                    "title": _("Customer Reviews"),
                    "icon": "star_rate",
                    "link": reverse_lazy("admin:cardealing_review_changelist"),
                },
            ],
        },
        {
            "title": _("Dealer Management"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Dealer Profiles"),
                    "icon": "store",
                    "link": reverse_lazy("admin:cardealing_dealerprofile_changelist"),
                },
                {
                    "title": _("Dealer Verification"),
                    "icon": "verified",
                    "link": reverse_lazy("admin:cardealing_dealerverificationdocument_changelist"),
                },
                {
                    "title": _("Dealer Services"),
                    "icon": "build",
                    "link": reverse_lazy("admin:cardealing_service_changelist"),
                },
                {
                    "title": _("Service Categories"),
                    "icon": "category",
                    "link": reverse_lazy("admin:cardealing_servicecategory_changelist"),
                },
                {
                    "title": _("Service Availability"),
                    "icon": "event_available",
                    "link": reverse_lazy("admin:cardealing_serviceavailability_changelist"),
                },
                {
                    "title": _("Service Slots"),
                    "icon": "schedule",
                    "link": reverse_lazy("admin:cardealing_serviceslot_changelist"),
                },
                {
                    "title": _("Commission Management"),
                    "icon": "trending_up",
                    "link": reverse_lazy("admin:cardealing_commissionhistory_changelist"),
                },
            ],
        },
        {
            "title": _("Booking & Payment Flow"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("All Bookings"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
                {
                    "title": _("Promotions & Discounts"),
                    "icon": "local_offer",
                    "link": reverse_lazy("admin:cardealing_promotion_changelist"),
                },
                {
                    "title": _("Payment Records"),
                    "icon": "payment",
                    "link": reverse_lazy("admin:cardealing_payment_changelist"),
                },
                {
                    "title": _("Virtual Cards"),
                    "icon": "credit_card",
                    "link": reverse_lazy("admin:cardealing_virtualcard_changelist"),
                },
                {
                    "title": _("Payout Management"),
                    "icon": "account_balance_wallet",
                    "link": reverse_lazy("admin:cardealing_payoutrequest_changelist"),
                },
                {
                    "title": _("Financial Transactions"),
                    "icon": "receipt",
                    "link": reverse_lazy("admin:cardealing_balancetransaction_changelist"),
                },
            ],
        },
        {
            "title": _("Integration & Automation"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Webhook Configurations"),
                    "icon": "webhook",
                    "link": reverse_lazy("admin:cardealing_webhookconfiguration_changelist"),
                },
                {
                    "title": _("Webhook Events"),
                    "icon": "event_note",
                    "link": reverse_lazy("admin:cardealing_webhookevent_changelist"),
                },
                {
                    "title": _("System Logs"),
                    "icon": "history",
                    "link": reverse_lazy("admin:cardealing_webhooklog_changelist"),
                },
                {
                    "title": _("Notifications"),
                    "icon": "notifications",
                    "link": reverse_lazy("admin:cardealing_notification_changelist"),
                },
            ],
        },
    ]

def get_customer_navigation():
    """Customer navigation focused on their journey"""
    return [
        {
            "title": _("My Dashboard"),
            "separator": True,
            "items": [
                {
                    "title": _("Dashboard"),
                    "icon": "dashboard",
                    "link": "/admin/",
                },
            ],
        },
        {
            "title": _("Profile & Vehicles"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("My Profile"),
                    "icon": "person",
                    "link": reverse_lazy("admin:cardealing_customerprofile_changelist"),
                },
                {
                    "title": _("My Vehicles"),
                    "icon": "directions_car",
                    "link": reverse_lazy("admin:cardealing_vehicle_changelist"),
                },
                {
                    "title": _("My Notifications"),
                    "icon": "notifications",
                    "link": reverse_lazy("admin:cardealing_notification_changelist"),
                },
            ],
        },
        {
            "title": _("Book Services"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Browse Services"),
                    "icon": "build",
                    "link": reverse_lazy("admin:cardealing_service_changelist"),
                },
                {
                    "title": _("Service Categories"),
                    "icon": "category",
                    "link": reverse_lazy("admin:cardealing_servicecategory_changelist"),
                },
                {
                    "title": _("Make Booking"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
            ],
        },
        {
            "title": _("My Bookings & History"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Current Bookings"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
                {
                    "title": _("Payment History"),
                    "icon": "payment",
                    "link": reverse_lazy("admin:cardealing_payment_changelist"),
                },
                {
                    "title": _("My Reviews"),
                    "icon": "star_rate",
                    "link": reverse_lazy("admin:cardealing_review_changelist"),
                },
            ],
        },
    ]

def get_dealer_navigation():
    """Dealer navigation for business management flow"""
    return [
        {
            "title": _("Business Dashboard"),
            "separator": True,
            "items": [
                {
                    "title": _("Dashboard"),
                    "icon": "dashboard",
                    "link": "/admin/",
                },
            ],
        },
        {
            "title": _("Setup & Verification"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Business Profile"),
                    "icon": "store",
                    "link": reverse_lazy("admin:cardealing_dealerprofile_changelist"),
                },
                {
                    "title": _("Verification Documents"),
                    "icon": "verified",
                    "link": reverse_lazy("admin:cardealing_dealerverificationdocument_changelist"),
                },
                {
                    "title": _("Commission History"),
                    "icon": "trending_up",
                    "link": reverse_lazy("admin:cardealing_commissionhistory_changelist"),
                },
            ],
        },
        {
            "title": _("Service Setup"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("My Services"),
                    "icon": "build",
                    "link": reverse_lazy("admin:cardealing_service_changelist"),
                },
                {
                    "title": _("Service Categories"),
                    "icon": "category",
                    "link": reverse_lazy("admin:cardealing_servicecategory_changelist"),
                },
                {
                    "title": _("Availability Settings"),
                    "icon": "event_available",
                    "link": reverse_lazy("admin:cardealing_serviceavailability_changelist"),
                },
                {
                    "title": _("Time Slots"),
                    "icon": "schedule",
                    "link": reverse_lazy("admin:cardealing_serviceslot_changelist"),
                },
            ],
        },
        {
            "title": _("Orders & Customers"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Incoming Bookings"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
                {
                    "title": _("Customer Reviews"),
                    "icon": "star_rate",
                    "link": reverse_lazy("admin:cardealing_review_changelist"),
                },
                {
                    "title": _("Notifications"),
                    "icon": "notifications",
                    "link": reverse_lazy("admin:cardealing_notification_changelist"),
                },
            ],
        },
        {
            "title": _("Payments & Earnings"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Payment Records"),
                    "icon": "payment",
                    "link": reverse_lazy("admin:cardealing_payment_changelist"),
                },
                {
                    "title": _("Virtual Card"),
                    "icon": "credit_card",
                    "link": reverse_lazy("admin:cardealing_virtualcard_changelist"),
                },
                {
                    "title": _("Earnings & Balance"),
                    "icon": "receipt",
                    "link": reverse_lazy("admin:cardealing_balancetransaction_changelist"),
                },
                {
                    "title": _("Payout Requests"),
                    "icon": "account_balance_wallet",
                    "link": reverse_lazy("admin:cardealing_payoutrequest_changelist"),
                },
            ],
        },
        {
            "title": _("External Website Integration"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Webhook Setup"),
                    "icon": "webhook",
                    "link": reverse_lazy("admin:cardealing_webhookconfiguration_changelist"),
                },
                {
                    "title": _("Integration Events"),
                    "icon": "event_note",
                    "link": reverse_lazy("admin:cardealing_webhookevent_changelist"),
                },
                {
                    "title": _("System Logs"),
                    "icon": "history",
                    "link": reverse_lazy("admin:cardealing_webhooklog_changelist"),
                },
            ],
        },
    ]

UNFOLD = {
    "SITE_TITLE": "Kreatech Car Detailing",
    "SITE_HEADER": "Kreatech Car Detailing",
    "SITE_LOGO": static_lazy("images/logo.jpg"),
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "config.settings.unfold_admin.environment_callback",
    "LOGIN": {
        "image": static_lazy("images/login-bg.jpg"),
        "redirect_after": lambda request: "/",
    },
    "COLORS": {
        "primary": {
            "50": "oklch(0.97 0.013 240)",
            "100": "oklch(0.93 0.024 240)",
            "200": "oklch(0.86 0.055 240)",
            "300": "oklch(0.78 0.108 240)",
            "400": "oklch(0.69 0.155 240)",
            "500": "oklch(0.58 0.191 240)",
            "600": "oklch(0.49 0.204 240)",
            "700": "oklch(0.42 0.195 240)",
            "800": "oklch(0.35 0.155 240)",
            "900": "oklch(0.28 0.108 240)",
        },
        "secondary": {
            "50": "oklch(0.98 0.003 240)",
            "100": "oklch(0.96 0.006 240)",
            "200": "oklch(0.90 0.011 240)",
            "300": "oklch(0.83 0.017 240)",
            "400": "oklch(0.64 0.015 240)",
            "500": "oklch(0.49 0.013 240)",
            "600": "oklch(0.37 0.013 240)",
            "700": "oklch(0.28 0.013 240)",
            "800": "oklch(0.19 0.013 240)",
            "900": "oklch(0.13 0.013 240)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": get_navigation_for_user,  # Dynamic navigation based on user
    },
}

# Environment callback for showing current environment
def environment_callback(request):
    """Show environment indicator"""
    return ["Development", "success"] if settings.DEBUG else ["Production", "danger"]