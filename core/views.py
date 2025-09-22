# inventory/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    TemplateView, ListView, DetailView,
    CreateView, UpdateView
)
from django.urls import reverse_lazy
from django.db.models import Count, Avg
from .models import Faculty, Department, Location, Item, Inspection, Transfer, AuditLog
from .forms import ItemForm, InspectionForm, TransferForm   # create these forms

# ----- Mixins -----
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

# ----- Dashboard -----
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["item_count"] = Item.objects.count()
        ctx["faculty_count"] = Faculty.objects.count()
        ctx["inspection_due"] = Item.objects.filter(
            inspections__next_due_date__isnull=False
        ).count()
        ctx["low_condition"] = Item.objects.filter(
            average_condition__lt=2.5
        ).count()
        ctx["recent_transfers"] = Transfer.objects.select_related(
            "item", "to_department"
        ).order_by("-moved_at")[:10]
        ctx["recent_audit"] = AuditLog.objects.order_by("-timestamp")[:10]
        return ctx

# ----- Item Views -----
class ItemListView(LoginRequiredMixin, ListView):
    model = Item
    paginate_by = 20
    template_name = "items/item_list.html"
    ordering = ["-created_at"]

class ItemDetailView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = "items/item_detail.html"

class ItemCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "items/item_form.html"
    success_url = reverse_lazy("item-list")

class ItemUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = "items/item_form.html"
    success_url = reverse_lazy("item-list")

# ----- Inspection Views -----
class InspectionCreateView(LoginRequiredMixin, CreateView):
    model = Inspection
    form_class = InspectionForm
    template_name = "inspections/inspection_form.html"

    def form_valid(self, form):
        form.instance.inspector = self.request.user
        form.instance.item = get_object_or_404(Item, pk=self.kwargs["item_pk"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("item-detail", kwargs={"pk": self.kwargs["item_pk"]})

class InspectionListView(LoginRequiredMixin, ListView):
    model = Inspection
    template_name = "inspections/inspection_list.html"
    ordering = ["-inspected_at"]

# ----- Transfer Views -----
class TransferCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Transfer
    form_class = TransferForm
    template_name = "transfers/transfer_form.html"

    def form_valid(self, form):
        form.instance.moved_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("transfer-list")

class TransferListView(LoginRequiredMixin, ListView):
    model = Transfer
    template_name = "transfers/transfer_list.html"
    ordering = ["-moved_at"]
