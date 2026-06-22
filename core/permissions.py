from django.db.models import Q

from .models import UserProfile


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return UserProfile.ROLE_SUPER_ADMIN
    return get_or_create_profile(user).role


def user_can_manage_org(user):
    role = user_role(user)
    return user.is_superuser or role in (
        UserProfile.ROLE_SUPER_ADMIN,
        UserProfile.ROLE_FACULTY_ADMIN,
        UserProfile.ROLE_DEPT_ADMIN,
    )


def user_can_manage_items(user):
    role = user_role(user)
    return user.is_superuser or role in (
        UserProfile.ROLE_SUPER_ADMIN,
        UserProfile.ROLE_FACULTY_ADMIN,
        UserProfile.ROLE_DEPT_ADMIN,
    )


def user_can_run_audits(user):
    role = user_role(user)
    return user.is_superuser or role in (
        UserProfile.ROLE_SUPER_ADMIN,
        UserProfile.ROLE_FACULTY_ADMIN,
        UserProfile.ROLE_DEPT_ADMIN,
        UserProfile.ROLE_AUDITOR,
    )


def scope_queryset_for_user(qs, user, department_field='department', faculty_field='department__faculty'):
    if not user.is_authenticated:
        return qs.none()
    if user.is_superuser:
        return qs
    profile = get_or_create_profile(user)
    if profile.role == UserProfile.ROLE_SUPER_ADMIN:
        return qs
    if profile.role == UserProfile.ROLE_FACULTY_ADMIN and profile.faculty_id:
        return qs.filter(**{faculty_field: profile.faculty_id})
    if profile.role in (UserProfile.ROLE_DEPT_ADMIN, UserProfile.ROLE_AUDITOR, UserProfile.ROLE_VIEWER):
        if profile.department_id:
            return qs.filter(**{department_field: profile.department_id})
        if profile.faculty_id:
            return qs.filter(**{faculty_field: profile.faculty_id})
    return qs
