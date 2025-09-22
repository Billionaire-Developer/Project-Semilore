from rest_framework import permissions

class IsInspector(permissions.BasePermission):
    """
    Simple custom permission: allow create inspection if user is in 'Inspectors' group
    or is staff.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff:
                return True
            return request.user.groups.filter(name='Inspectors').exists()
        return False
