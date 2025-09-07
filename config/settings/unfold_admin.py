from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.utils.functional import lazy

static_lazy = lazy(static, str)

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
        "navigation": [
            {
                "title": _("Data And Analytics"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": "/admin/",
                        "permission": lambda request: request.user.is_superuser,
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
        ],
    },
}