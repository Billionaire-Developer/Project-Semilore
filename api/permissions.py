from rest_framework import permissions

from core.models import UserProfile
from core.permissions import get_or_create_profile


class IsInspector(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_superuser or request.user.is_staff:
                return True
            profile = get_or_create_profile(request.user)
            return profile.role in (
                UserProfile.ROLE_SUPER_ADMIN,
                UserProfile.ROLE_FACULTY_ADMIN,
                UserProfile.ROLE_DEPT_ADMIN,
                UserProfile.ROLE_AUDITOR,
            ) or request.user.groups.filter(name='Inspectors').exists()
        return False


class IsOrgAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        profile = get_or_create_profile(request.user)
        return profile.role in (
            UserProfile.ROLE_SUPER_ADMIN,
            UserProfile.ROLE_FACULTY_ADMIN,
            UserProfile.ROLE_DEPT_ADMIN,
        )


class IsItemManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        profile = get_or_create_profile(request.user)
        return profile.role in (
            UserProfile.ROLE_SUPER_ADMIN,
            UserProfile.ROLE_FACULTY_ADMIN,
            UserProfile.ROLE_DEPT_ADMIN,
        )
