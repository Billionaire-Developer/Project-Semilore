import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AuditSessionForm,
    AuditVerificationForm,
    DepartmentForm,
    FacultyForm,
    InspectionForm,
    ItemForm,
    LoginForm,
    OfficeForm,
    TransferForm,
    UserProfileForm,
)
from .mixins import AuditorRequiredMixin, OrgAdminRequiredMixin, StaffRequiredMixin
from .models import (
    AuditLog,
    AuditSession,
    AuditVerification,
    Department,
    Faculty,
    Inspection,
    Item,
    Office,
    Transfer,
    UserProfile,
)
from .permissions import get_or_create_profile, scope_queryset_for_user, user_can_manage_items
from .services.audit import session_report_data, verify_item_in_session
from .services.qr import generate_qr_for_item, item_verify_url


# ----- Auth -----
class InventoryLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hide_sidebar'] = True
        return ctx


class InventoryLogoutView(LogoutView):
    next_page = reverse_lazy('login')


class InventorySignupView(CreateView):
    form_class = UserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hide_sidebar'] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Account created successfully. Please log in.")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return get_or_create_profile(self.request.user)


# ----- Dashboard -----
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = scope_queryset_for_user(Item.objects.all(), self.request.user)
        sessions = scope_queryset_for_user(
            AuditSession.objects.all(), self.request.user, department_field='department'
        )
        ctx['item_count'] = items.count()
        ctx['faculty_count'] = Faculty.objects.count()
        ctx['active_audits'] = sessions.filter(status=AuditSession.STATUS_ACTIVE).count()
        ctx['low_condition'] = items.filter(average_condition__lt=2.5).count()
        ctx['recent_transfers'] = Transfer.objects.select_related(
            'item', 'to_department', 'to_office'
        ).order_by('-moved_at')[:10]
        ctx['recent_activity'] = AuditLog.objects.order_by('-timestamp')[:10]
        ctx['active_sessions'] = sessions.filter(status=AuditSession.STATUS_ACTIVE)[:5]
        return ctx


# ----- Org management -----
class FacultyListView(LoginRequiredMixin, OrgAdminRequiredMixin, ListView):
    model = Faculty
    template_name = 'org/faculty_list.html'
    context_object_name = 'faculties'


class FacultyCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    model = Faculty
    form_class = FacultyForm
    template_name = 'org/faculty_form.html'
    success_url = reverse_lazy('faculty-list')


class DepartmentListView(LoginRequiredMixin, OrgAdminRequiredMixin, ListView):
    model = Department
    template_name = 'org/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        return scope_queryset_for_user(
            Department.objects.select_related('faculty'), self.request.user, department_field='pk', faculty_field='faculty'
        )


class DepartmentCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'org/department_form.html'
    success_url = reverse_lazy('department-list')


class OfficeListView(LoginRequiredMixin, OrgAdminRequiredMixin, ListView):
    model = Office
    template_name = 'org/office_list.html'
    context_object_name = 'offices'

    def get_queryset(self):
        return scope_queryset_for_user(
            Office.objects.select_related('department__faculty'), self.request.user
        )


class OfficeCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    model = Office
    form_class = OfficeForm
    template_name = 'org/office_form.html'
    success_url = reverse_lazy('office-list')


# ----- Items -----
class ItemListView(LoginRequiredMixin, ListView):
    model = Item
    paginate_by = 20
    template_name = 'items/item_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        qs = scope_queryset_for_user(
            Item.objects.select_related('department__faculty', 'office'), self.request.user
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(uid__icontains=q) | Q(name__icontains=q) | Q(category__icontains=q) | Q(serial_number__icontains=q)
            )
        dept = self.request.GET.get('department')
        if dept:
            qs = qs.filter(department_id=dept)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = scope_queryset_for_user(Department.objects.all(), self.request.user, department_field='pk', faculty_field='faculty')
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx


class ItemDetailView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'items/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return scope_queryset_for_user(
            Item.objects.select_related('department__faculty', 'office'), self.request.user
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['verify_url'] = item_verify_url(self.object)
        ctx['inspections'] = self.object.inspections.select_related('inspector')[:10]
        ctx['transfers'] = self.object.transfers.select_related('to_department', 'to_office')[:10]
        ctx['can_edit'] = user_can_manage_items(self.request.user)
        return ctx


class ItemCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'items/item_form.html'
    success_url = reverse_lazy('item-list')

    def form_valid(self, form):
        department = form.cleaned_data['department']
        form.instance.uid = Item.generate_uid(department)
        response = super().form_valid(form)
        generate_qr_for_item(self.object)
        messages.success(self.request, f'Item {self.object.uid} created with QR code.')
        return response


class ItemUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = 'items/item_form.html'

    def get_success_url(self):
        return reverse('item-detail', kwargs={'pk': self.object.pk})

    def get_queryset(self):
        return scope_queryset_for_user(Item.objects.all(), self.request.user)


class ItemLabelPrintView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'items/item_label_print.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['verify_url'] = item_verify_url(self.object)
        return ctx


# ----- Verify (QR landing) -----
class VerifyItemView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'audits/verify_item.html'
    context_object_name = 'item'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_queryset(self):
        return Item.objects.select_related('department__faculty', 'office')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['verify_url'] = item_verify_url(self.object)
        ctx['active_session'] = AuditSession.objects.filter(
            status=AuditSession.STATUS_ACTIVE,
            department=self.object.department,
        ).first()
        if self.object.office_id and ctx['active_session'] and ctx['active_session'].office_id:
            if ctx['active_session'].office_id != self.object.office_id:
                ctx['scope_warning'] = True
        ctx['verification_form'] = AuditVerificationForm(initial={'status': AuditVerification.STATUS_VERIFIED})
        return ctx

    def post(self, request, uuid):
        item = self.get_object()
        session_id = request.POST.get('session_id')
        session = get_object_or_404(AuditSession, pk=session_id, status=AuditSession.STATUS_ACTIVE)
        form = AuditVerificationForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Invalid verification data.')
            return redirect('verify-item', uuid=item.uuid)

        try:
            verify_item_in_session(
                session=session,
                item=item,
                user=request.user,
                status=form.cleaned_data['status'],
                notes=form.cleaned_data.get('notes', ''),
                scan_method=AuditVerification.SCAN_QR,
            )
            messages.success(request, f'{item.uid} verified in audit "{session.title}".')
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect('audit-session-detail', pk=session.pk)


# ----- Inspections -----
class InspectionCreateView(LoginRequiredMixin, CreateView):
    model = Inspection
    form_class = InspectionForm
    template_name = 'inspections/inspection_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(Item, pk=self.kwargs['item_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.inspector = self.request.user
        form.instance.item = self.item
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('item-detail', kwargs={'pk': self.item.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['item'] = self.item
        return ctx


class InspectionListView(LoginRequiredMixin, ListView):
    model = Inspection
    template_name = 'inspections/inspection_list.html'
    paginate_by = 25

    def get_queryset(self):
        qs = Inspection.objects.select_related('item', 'inspector')
        return scope_queryset_for_user(qs, self.request.user, department_field='item__department', faculty_field='item__department__faculty')


# ----- Transfers -----
class TransferCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Transfer
    form_class = TransferForm
    template_name = 'transfers/transfer_form.html'
    success_url = reverse_lazy('transfer-list')

    def form_valid(self, form):
        form.instance.moved_by = self.request.user
        item = form.cleaned_data['item']
        form.instance.from_department = item.department
        form.instance.from_office = item.office
        response = super().form_valid(form)
        item.department = form.cleaned_data['to_department'] or item.department
        item.office = form.cleaned_data.get('to_office') or item.office
        item.save(update_fields=['department', 'office'])
        return response


class TransferListView(LoginRequiredMixin, ListView):
    model = Transfer
    template_name = 'transfers/transfer_list.html'
    paginate_by = 25

    def get_queryset(self):
        qs = Transfer.objects.select_related('item', 'to_department', 'to_office', 'moved_by')
        return scope_queryset_for_user(qs, self.request.user, department_field='item__department', faculty_field='item__department__faculty')


# ----- Audit sessions -----
class AuditSessionListView(LoginRequiredMixin, ListView):
    model = AuditSession
    template_name = 'audits/session_list.html'
    paginate_by = 20
    context_object_name = 'sessions'

    def get_queryset(self):
        return scope_queryset_for_user(
            AuditSession.objects.select_related('department', 'office', 'started_by'),
            self.request.user,
            department_field='department',
        )


class AuditSessionCreateView(LoginRequiredMixin, AuditorRequiredMixin, CreateView):
    model = AuditSession
    form_class = AuditSessionForm
    template_name = 'audits/session_form.html'

    def form_valid(self, form):
        form.instance.started_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('audit-session-detail', kwargs={'pk': self.object.pk})


class AuditSessionDetailView(LoginRequiredMixin, DetailView):
    model = AuditSession
    template_name = 'audits/session_detail.html'
    context_object_name = 'session'

    def get_queryset(self):
        return scope_queryset_for_user(
            AuditSession.objects.select_related('department', 'office', 'started_by'),
            self.request.user,
            department_field='department',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['report'] = session_report_data(self.object)
        ctx['verifications'] = self.object.verifications.select_related('item', 'verified_by')[:50]
        return ctx


class AuditSessionActivateView(LoginRequiredMixin, AuditorRequiredMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(AuditSession, pk=pk)
        session.status = AuditSession.STATUS_ACTIVE
        session.save(update_fields=['status'])
        messages.success(request, f'Audit "{session.title}" is now active.')
        return redirect('audit-session-detail', pk=pk)


class AuditSessionCloseView(LoginRequiredMixin, AuditorRequiredMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(AuditSession, pk=pk)
        session.close()
        messages.success(request, f'Audit "{session.title}" closed.')
        return redirect('audit-report', pk=pk)


class AuditReportView(LoginRequiredMixin, DetailView):
    model = AuditSession
    template_name = 'audits/report.html'
    context_object_name = 'session'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['report'] = session_report_data(self.object)
        return ctx


class AuditScannerView(LoginRequiredMixin, AuditorRequiredMixin, DetailView):
    model = AuditSession
    template_name = 'audits/scanner.html'
    context_object_name = 'session'

    def get_queryset(self):
        return AuditSession.objects.filter(status=AuditSession.STATUS_ACTIVE)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['report'] = session_report_data(self.object)
        ctx['show_bottom_nav'] = True
        ctx['hide_sidebar'] = True
        return ctx


class AuditVerifyAPIView(LoginRequiredMixin, AuditorRequiredMixin, View):
    """JSON endpoint for scanner with retry-on-reconnect support."""

    def post(self, request, pk):
        session = get_object_or_404(AuditSession, pk=pk, status=AuditSession.STATUS_ACTIVE)
        item_uuid = request.POST.get('item_uuid', '').strip()
        status_val = request.POST.get('status', AuditVerification.STATUS_VERIFIED)
        notes = request.POST.get('notes', '')
        scan_method = request.POST.get('scan_method', AuditVerification.SCAN_QR)

        if not item_uuid:
            return JsonResponse({'ok': False, 'error': 'item_uuid required'}, status=400)

        try:
            item = Item.objects.get(uuid=item_uuid)
        except Item.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Item not found'}, status=404)

        try:
            verification, created = verify_item_in_session(
                session=session,
                item=item,
                user=request.user,
                status=status_val,
                notes=notes,
                scan_method=scan_method,
            )
        except ValueError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

        report = session_report_data(session)
        return JsonResponse({
            'ok': True,
            'created': created,
            'item': {'uid': item.uid, 'name': item.name, 'uuid': str(item.uuid)},
            'progress': {
                'expected': report['expected_count'],
                'verified': report['verified_count'],
                'pct': session.progress_pct,
            },
        })


class ItemLookupByUIDView(LoginRequiredMixin, View):
    def get(self, request):
        uid = request.GET.get('uid', '').strip()
        if not uid:
            return JsonResponse({'ok': False, 'error': 'uid required'}, status=400)
        try:
            item = scope_queryset_for_user(Item.objects.all(), request.user).get(uid=uid)
        except Item.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Item not found'}, status=404)
        return JsonResponse({
            'ok': True,
            'item': {'uid': item.uid, 'name': item.name, 'uuid': str(item.uuid)},
        })


# ----- PDF Report -----
class InspectionPDFView(LoginRequiredMixin, View):
    """
    Generates a downloadable PDF inspection report for a single Inspection.
    URL params:
      ?inspection=<pk>  — generate report for that specific inspection
    """

    def get(self, request):
        from weasyprint import HTML
        from django.conf import settings

        inspection_pk = request.GET.get('inspection')
        if not inspection_pk:
            messages.error(request, 'No inspection specified.')
            return redirect('inspection-list')

        inspection = get_object_or_404(
            Inspection.objects.select_related('item__department', 'item__office', 'inspector'),
            pk=inspection_pk,
        )

        verify_url = item_verify_url(inspection.item)

        # Build an absolute filesystem path to the QR image for WeasyPrint
        qr_absolute_path = ''
        if inspection.item.qr_code_image:
            qr_absolute_path = (
                'file:///' +
                os.path.abspath(inspection.item.qr_code_image.path).replace('\\', '/')
            )

        context = {
            'inspection': inspection,
            'verify_url': verify_url,
            'qr_absolute_path': qr_absolute_path,
            'generated_at': datetime.now(),
        }

        html_string = render_to_string('inspections/inspection_pdf.html', context, request=request)

        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        filename = f"inspection-{inspection.item.uid}-{inspection.pk}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
