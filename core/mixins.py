from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .permissions import (
    user_can_manage_items,
    user_can_manage_org,
    user_can_run_audits,
)


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or user_can_manage_items(self.request.user)


class OrgAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or user_can_manage_org(self.request.user)


class AuditorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or user_can_run_audits(self.request.user)
