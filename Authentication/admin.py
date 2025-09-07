from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from django import forms

from unfold.admin import ModelAdmin
from .models import UserProfile

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

# Unregister default models
admin.site.unregister(User)
admin.site.unregister(Group)

# Unregister social account models if already registered
for m in (SocialAccount, SocialApp, SocialToken):
    try:
        admin.site.unregister(m)
    except admin.sites.NotRegistered:
        pass

# Unregister Site if already registered
try:
    admin.site.unregister(Site)
except admin.sites.NotRegistered:
    pass


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_type', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__user_type')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    def get_user_type(self, obj):
        return obj.profile.get_user_type_display() if hasattr(obj, 'profile') else 'N/A'
    get_user_type.short_description = 'User Type'


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'user_type', 'phone_number', 'is_verified', 'created_at')
    list_filter = ('user_type', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('user', 'user_type')}),
        ('Personal info', {'fields': ('phone_number', 'address', 'date_of_birth')}),
        ('Status', {'fields': ('is_verified',)}),
        ('Important dates', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    fieldsets = (
        (None, {
            'fields': ('name', 'permissions')
        }),
    )


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ('name', 'codename', 'content_type')
    search_fields = ('name', 'codename')
    list_filter = ('content_type',)
    fieldsets = (
        (None, {
            'fields': ('name', 'codename', 'content_type')
        }),
    )


# ---- SocialAccount ----
@admin.register(SocialAccount)
class SocialAccountAdmin(ModelAdmin):
    list_display = ("id", "user", "provider", "uid", "last_login")
    search_fields = ("user__username", "user__email", "provider", "uid")
    list_filter = ("provider",)
    raw_id_fields = ("user",)
    fieldsets = (
        (_("Account"), {"fields": (("user", "provider", "uid"),)}),
        (_("Meta"), {"fields": (("last_login", "date_joined"),)}),
        (_("Profile Data"), {"fields": (("extra_data",),)}),
    )
    readonly_fields = ("extra_data", "last_login", "date_joined")


# ---- SocialApp ----
class SocialAppAdminForm(forms.ModelForm):
    class Meta:
        model = SocialApp
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ensure provider field shows as dropdown with choices
        if "provider" in self.fields:
            # Get provider choices from the model
            provider_choices = getattr(SocialApp._meta.get_field('provider'), 'choices', None)
            if provider_choices:
                self.fields["provider"].widget = forms.Select(choices=provider_choices)
            else:
                # If no choices defined in model, create common provider choices
                common_providers = [
                    ('google', 'Google'),
                    ('facebook', 'Facebook'),
                    ('twitter', 'Twitter'),
                    ('github', 'GitHub'),
                    ('linkedin', 'LinkedIn'),
                    ('microsoft', 'Microsoft'),
                    ('apple', 'Apple'),
                ]
                self.fields["provider"].widget = forms.Select(choices=[('', '---------')] + common_providers)
        
        # Don't override sites field widget - let filter_horizontal handle it
        if "sites" in self.fields:
            self.fields["sites"].help_text = _("Select the sites where this app is active.")


@admin.register(SocialApp)
class SocialAppAdmin(ModelAdmin):
    form = SocialAppAdminForm
    list_display = ("id", "name", "provider", "client_id")
    search_fields = ("name", "provider", "client_id")
    list_filter = ("provider",)
    filter_horizontal = ("sites",)
    
    fieldsets = (
        (_("App Info"), {
            "fields": (("name", "provider"), ("client_id", "secret"))
        }),
        (_("Configuration"), {
            "fields": ("key",),
        }),
        (_("Sites"), {
            "fields": ("sites",),
            "description": _("Select the sites where this social app will be active.")
        }),
    )

    class Media:
        css = {
            'all': ('admin/css/widgets.css',),
        }
        js = ('admin/js/core.js', 'admin/js/SelectBox.js', 'admin/js/SelectFilter2.js')


# ---- SocialToken ----
@admin.register(SocialToken)
class SocialTokenAdmin(ModelAdmin):
    list_display = ("id", "account", "app", "expires_at")
    search_fields = ("account__user__username", "account__uid", "app__name")
    list_filter = ("app__provider", "expires_at")
    raw_id_fields = ("account", "app")
    fieldsets = (
        (_("Token"), {"fields": (("account", "app"), ("token", "token_secret"), ("expires_at",))}),
    )


# ---- Site ----
@admin.register(Site)
class SiteAdmin(ModelAdmin):
    list_display = ("id", "domain", "name")
    search_fields = ("domain", "name")
    fieldsets = (
        (_("Site Info"), {"fields": (("domain", "name"),)}),
    )


# Register User admin
admin.site.register(User, UserAdmin)