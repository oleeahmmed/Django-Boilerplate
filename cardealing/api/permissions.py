from rest_framework import permissions
from Authentication.models import UserProfile

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.user_type == 'admin'
        except UserProfile.DoesNotExist:
            return False

class IsDealer(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.user_type == 'dealer'
        except UserProfile.DoesNotExist:
            return False

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.user_type == 'customer'
        except UserProfile.DoesNotExist:
            return False

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or IsAdmin().has_permission(request, view)