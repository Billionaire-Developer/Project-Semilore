from core.permissions import get_or_create_profile, user_can_run_audits


def site_context(request):
    profile = None
    if request.user.is_authenticated:
        profile = get_or_create_profile(request.user)
    return {
        'user_profile': profile,
        'can_manage_org': request.user.is_superuser or (
            profile and profile.is_admin_role
        ) if request.user.is_authenticated else False,
        'can_run_audits': request.user.is_superuser or user_can_run_audits(request.user),
    }
