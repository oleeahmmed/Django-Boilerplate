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
    """Admin gets full access to everything"""
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
                    "link": reverse_lazy("admin:auth_user_changelist"),
                },
                {
                    "title": _("Groups"),
                    "icon": "group",
                    "link": reverse_lazy("admin:auth_group_changelist"),
                },
                {
                    "title": _("Permissions"),
                    "icon": "lock",
                    "link": reverse_lazy("admin:auth_permission_changelist"),
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
                },
                {
                    "title": _("Social Accounts"),
                    "icon": "account_circle",
                    "link": reverse_lazy("admin:socialaccount_socialaccount_changelist"),
                },
                {
                    "title": _("Social Tokens"),
                    "icon": "vpn_key",
                    "link": reverse_lazy("admin:socialaccount_socialtoken_changelist"),
                },
                {
                    "title": _("Social Apps"),
                    "icon": "apps",
                    "link": reverse_lazy("admin:socialaccount_socialapp_changelist"),
                },
            ],
        },
        {
            "title": _("User Management"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("All Users"),
                    "icon": "people",
                    "link": reverse_lazy("admin:auth_user_changelist"),
                },
                {
                    "title": _("Customer Profiles"),
                    "icon": "person",
                    "link": reverse_lazy("admin:cardealing_customerprofile_changelist"),
                },
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
            ],
        },
        {
            "title": _("Business Operations"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("All Bookings"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
                {
                    "title": _("Services"),
                    "icon": "build",
                    "link": reverse_lazy("admin:cardealing_service_changelist"),
                },
                {
                    "title": _("Service Categories"),
                    "icon": "category",
                    "link": reverse_lazy("admin:cardealing_servicecategory_changelist"),
                },
                {
                    "title": _("Vehicles"),
                    "icon": "directions_car",
                    "link": reverse_lazy("admin:cardealing_vehicle_changelist"),
                },
            ],
        },
        {
            "title": _("Financial Management"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("All Payments"),
                    "icon": "payment",
                    "link": reverse_lazy("admin:cardealing_payment_changelist"),
                },
                {
                    "title": _("Virtual Cards"),
                    "icon": "credit_card",
                    "link": reverse_lazy("admin:cardealing_virtualcard_changelist"),
                },
                {
                    "title": _("Payout Requests"),
                    "icon": "account_balance_wallet",
                    "link": reverse_lazy("admin:cardealing_payoutrequest_changelist"),
                },
                {
                    "title": _("Balance Transactions"),
                    "icon": "receipt",
                    "link": reverse_lazy("admin:cardealing_balancetransaction_changelist"),
                },
                {
                    "title": _("Commission History"),
                    "icon": "trending_up",
                    "link": reverse_lazy("admin:cardealing_commissionhistory_changelist"),
                },
                {
                    "title": _("Promotions"),
                    "icon": "local_offer",
                    "link": reverse_lazy("admin:cardealing_promotion_changelist"),
                },
            ],
        },
        {
            "title": _("Webhook Integration"),
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
                    "title": _("Webhook Logs"),
                    "icon": "history",
                    "link": reverse_lazy("admin:cardealing_webhooklog_changelist"),
                },
            ],
        },
        {
            "title": _("System Management"),
            "separator": True,
            "collapsible": True,
            "items": [
                {
                    "title": _("Reviews"),
                    "icon": "star_rate",
                    "link": reverse_lazy("admin:cardealing_review_changelist"),
                },
                {
                    "title": _("Notifications"),
                    "icon": "notifications",
                    "link": reverse_lazy("admin:cardealing_notification_changelist"),
                },
                {
                    "title": _("Webhook Events"),
                    "icon": "webhook",
                    "link": reverse_lazy("admin:cardealing_webhookevent_changelist"),
                },
            ],
        },
    ]

def get_customer_navigation():
    """Customer gets limited access - only their own data"""
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
            "title": _("My Profile"),
            "separator": True,
            "items": [
                {
                    "title": _("Profile Settings"),
                    "icon": "person",
                    "link": reverse_lazy("admin:cardealing_customerprofile_changelist"),
                },
                {
                    "title": _("My Vehicles"),
                    "icon": "directions_car",
                    "link": reverse_lazy("admin:cardealing_vehicle_changelist"),
                },
            ],
        },
        {
            "title": _("My Bookings"),
            "separator": True,
            "items": [
                {
                    "title": _("My Bookings"),
                    "icon": "event",
                    "link": reverse_lazy("admin:cardealing_booking_changelist"),
                },
                {
                    "title": _("Available Services"),
                    "icon": "build",
                    "link": reverse_lazy("admin:cardealing_service_changelist"),
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
    """Dealer gets access to manage their business"""
    return [
        {
            "title": _("My Dashboard"),
            "separator": True,
            "items": [
                {
                    "title": _("Business Dashboard"),
                    "icon": "dashboard",
                    "link": "/admin/",
                },
            ],
        },
        {
            "title": _("My Business"),
            "separator": True,
            "items": [
                {
                    "title": _("Business Profile"),
                    "icon": "store",
                    "link": reverse_lazy("admin:cardealing_dealerprofile_changelist"),
                },
                {
                    "title": _("My Services"),
                    "icon": "build",
                    "link": reverse_lazy("admin:cardealing_service_changelist"),
                },
                {
                    "title": _("Service Slots"),
                    "icon": "schedule",
                    "link": reverse_lazy("admin:cardealing_serviceslot_changelist"),
                },
            ],
        },
        {
            "title": _("Bookings & Customers"),
            "separator": True,
            "items": [
                {
                    "title": _("My Bookings"),
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
            "title": _("Financials"),
            "separator": True,
            "items": [
                {
                    "title": _("My Payments"),
                    "icon": "payment",
                    "link": reverse_lazy("admin:cardealing_payment_changelist"),
                },
                {
                    "title": _("Payout Requests"),
                    "icon": "account_balance_wallet",
                    "link": reverse_lazy("admin:cardealing_payoutrequest_changelist"),
                },
                {
                    "title": _("Balance History"),
                    "icon": "receipt",
                    "link": reverse_lazy("admin:cardealing_balancetransaction_changelist"),
                },
            ],
        },
    ]

UNFOLD = {
    "SITE_TITLE": "Kreatech ERP",
    "SITE_HEADER": "Kreatech ERP",
    "SITE_LOGO": static_lazy("images/logo/logo.svg"),
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
        "success": {
            "50": "oklch(0.97 0.027 142)",
            "100": "oklch(0.93 0.055 142)",
            "200": "oklch(0.87 0.108 142)",
            "300": "oklch(0.78 0.155 142)",
            "400": "oklch(0.69 0.191 142)",
            "500": "oklch(0.64 0.204 142)",
            "600": "oklch(0.55 0.195 142)",
            "700": "oklch(0.46 0.155 142)",
            "800": "oklch(0.37 0.108 142)",
            "900": "oklch(0.28 0.055 142)",
        },
        "warning": {
            "50": "oklch(0.98 0.027 85)",
            "100": "oklch(0.95 0.055 85)",
            "200": "oklch(0.90 0.108 85)",
            "300": "oklch(0.84 0.155 85)",
            "400": "oklch(0.78 0.191 85)",
            "500": "oklch(0.69 0.204 85)",
            "600": "oklch(0.58 0.195 85)",
            "700": "oklch(0.46 0.155 85)",
            "800": "oklch(0.37 0.108 85)",
            "900": "oklch(0.28 0.055 85)",
        },
        "error": {
            "50": "oklch(0.97 0.027 25)",
            "100": "oklch(0.93 0.055 25)",
            "200": "oklch(0.87 0.108 25)",
            "300": "oklch(0.78 0.155 25)",
            "400": "oklch(0.69 0.191 25)",
            "500": "oklch(0.63 0.204 25)",
            "600": "oklch(0.55 0.195 25)",
            "700": "oklch(0.46 0.155 25)",
            "800": "oklch(0.37 0.108 25)",
            "900": "oklch(0.28 0.055 25)",
        },
        "info": {
            "50": "oklch(0.97 0.027 200)",
            "100": "oklch(0.93 0.055 200)",
            "200": "oklch(0.87 0.108 200)",
            "300": "oklch(0.78 0.155 200)",
            "400": "oklch(0.69 0.191 200)",
            "500": "oklch(0.64 0.204 200)",
            "600": "oklch(0.55 0.195 200)",
            "700": "oklch(0.46 0.155 200)",
            "800": "oklch(0.37 0.108 200)",
            "900": "oklch(0.28 0.055 200)",
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