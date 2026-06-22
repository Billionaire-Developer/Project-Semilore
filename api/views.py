import codecs
import csv
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import AuditSession, AuditVerification, Department, Faculty, Inspection, Item, Office, Transfer
from core.permissions import scope_queryset_for_user
from core.services.audit import session_report_data, verify_item_in_session
from core.services.qr import generate_qr_for_item, item_verify_url

from .permissions import IsInspector, IsItemManager, IsOrgAdmin
from .serializers import (
    AuditSessionSerializer,
    AuditVerificationSerializer,
    AuditVerifyRequestSerializer,
    DepartmentSerializer,
    FacultySerializer,
    InspectionSerializer,
    ItemSerializer,
    OfficeSerializer,
    TransferSerializer,
)

logger = logging.getLogger(__name__)


class ScopedMixin:
    department_field = 'department'
    faculty_field = 'department__faculty'

    def scope(self, qs):
        return scope_queryset_for_user(qs, self.request.user, self.department_field, self.faculty_field)


class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [IsOrgAdmin]


class DepartmentViewSet(ScopedMixin, viewsets.ModelViewSet):
    queryset = Department.objects.select_related('faculty').all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        return self.scope(super().get_queryset())


class OfficeViewSet(ScopedMixin, viewsets.ModelViewSet):
    queryset = Office.objects.select_related('department__faculty').all()
    serializer_class = OfficeSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        return self.scope(super().get_queryset())


class ItemViewSet(ScopedMixin, viewsets.ModelViewSet):
    queryset = Item.objects.select_related('department__faculty', 'office').all().order_by('-created_at')
    serializer_class = ItemSerializer
    search_fields = ['uid', 'name', 'serial_number', 'category']

    def get_queryset(self):
        from django.db.models import Q
        qs = self.scope(super().get_queryset())
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(uid__icontains=q) | Q(serial_number__icontains=q)
            )
        return qs

    def perform_create(self, serializer):
        department = serializer.validated_data.get('department')
        if not department:
            raise serializers.ValidationError({'department': 'Required to generate UID.'})
        uid = Item.generate_uid(department)
        serializer.save(uid=uid)
        generate_qr_for_item(serializer.instance)

    @action(detail=False, methods=['get'], url_path='by-uuid/(?P<item_uuid>[0-9a-f-]+)')
    def by_uuid(self, request, item_uuid=None):
        item = get_object_or_404(self.get_queryset(), uuid=item_uuid)
        return Response(ItemSerializer(item, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsItemManager])
    def regenerate_qr(self, request, pk=None):
        item = self.get_object()
        ok = generate_qr_for_item(item)
        if not ok:
            return Response({'detail': 'QR generation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'detail': 'QR regenerated', 'verify_url': item_verify_url(item)})

    @action(detail=True, methods=['post'], permission_classes=[IsInspector])
    def inspect(self, request, pk=None):
        item = self.get_object()
        data = request.data.copy()
        data['item'] = item.pk
        serializer = InspectionSerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    inspection = serializer.save(inspector=request.user)
                return Response(InspectionSerializer(inspection).data, status=status.HTTP_201_CREATED)
            except Exception:
                logger.exception('Failed to create inspection')
                return Response({'detail': 'Failed to create inspection'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsItemManager])
    def transfer(self, request, pk=None):
        item = self.get_object()
        data = request.data
        try:
            to_dept_id = data.get('to_department')
            to_office_id = data.get('to_office')
            to_dept = Department.objects.get(pk=to_dept_id) if to_dept_id else None
            to_office = Office.objects.get(pk=to_office_id) if to_office_id else None
            Transfer.objects.create(
                item=item,
                from_department=item.department,
                to_department=to_dept,
                from_office=item.office,
                to_office=to_office,
                moved_by=request.user,
                notes=data.get('notes', ''),
            )
            item.department = to_dept or item.department
            item.office = to_office or item.office
            item.save(update_fields=['department', 'office'])
            return Response({'detail': 'transfer recorded'}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception('Transfer failed')
            return Response({'detail': 'transfer failed'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsItemManager])
    def bulk_import(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'detail': 'file required'}, status=status.HTTP_400_BAD_REQUEST)
        reader = csv.DictReader(codecs.iterdecode(f, 'utf-8'))
        created = []
        errors = []
        for i, row in enumerate(reader, 1):
            try:
                dept_code = row.get('department_code')
                fac_code = row.get('faculty_code')
                faculty = Faculty.objects.filter(code=fac_code).first()
                department = Department.objects.filter(code=dept_code, faculty=faculty).first()
                if not department:
                    errors.append({'row': i, 'error': 'department not found'})
                    continue
                uid = Item.generate_uid(department)
                item = Item.objects.create(
                    uid=uid,
                    name=row.get('name') or 'Unnamed',
                    category=row.get('category') or '',
                    serial_number=row.get('serial_number') or None,
                    department=department,
                )
                generate_qr_for_item(item)
                created.append(item.uid)
            except Exception as e:
                logger.exception('bulk import row failed')
                errors.append({'row': i, 'error': str(e)})
        return Response({'created': created, 'errors': errors})


class InspectionViewSet(ScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Inspection.objects.select_related('item', 'inspector').all().order_by('-inspected_at')
    serializer_class = InspectionSerializer
    department_field = 'item__department'
    faculty_field = 'item__department__faculty'

    def get_queryset(self):
        return self.scope(super().get_queryset())


class AuditSessionViewSet(ScopedMixin, viewsets.ModelViewSet):
    queryset = AuditSession.objects.select_related('department', 'office', 'started_by').all()
    serializer_class = AuditSessionSerializer
    permission_classes = [IsInspector]

    def get_queryset(self):
        return self.scope(super().get_queryset())

    def perform_create(self, serializer):
        serializer.save(started_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        session = self.get_object()
        session.status = AuditSession.STATUS_ACTIVE
        session.save(update_fields=['status'])
        return Response(AuditSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        session = self.get_object()
        session.close()
        return Response(AuditSessionSerializer(session).data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        session = self.get_object()
        report = session_report_data(session)
        return Response({
            'expected': report['expected_count'],
            'verified': report['verified_count'],
            'progress_pct': session.progress_pct,
            'missing_count': len(report['missing_items']),
            'unexpected_count': len(report['unexpected']),
        })

    @action(detail=True, methods=['get'])
    def verifications(self, request, pk=None):
        session = self.get_object()
        qs = session.verifications.select_related('item', 'verified_by')
        return Response(AuditVerificationSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        session = self.get_object()
        report = session_report_data(session)
        return Response({
            'session': AuditSessionSerializer(session).data,
            'expected_count': report['expected_count'],
            'verified_count': report['verified_count'],
            'missing': [{'uid': i.uid, 'name': i.name} for i in report['missing_items']],
            'unexpected': [
                {'uid': v.item.uid, 'name': v.item.name, 'status': v.status}
                for v in report['unexpected']
            ],
            'damaged': [
                {'uid': v.item.uid, 'name': v.item.name}
                for v in report['damaged']
            ],
        })

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        session = self.get_object()
        if session.status != AuditSession.STATUS_ACTIVE:
            return Response({'detail': 'Session is not active'}, status=status.HTTP_400_BAD_REQUEST)
        ser = AuditVerifyRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = self.scope(Item.objects.all()).get(uuid=ser.validated_data['item_uuid'])
        except Item.DoesNotExist:
            return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            verification, created = verify_item_in_session(
                session=session,
                item=item,
                user=request.user,
                status=ser.validated_data['status'],
                notes=ser.validated_data.get('notes', ''),
                scan_method=ser.validated_data.get('scan_method', AuditVerification.SCAN_QR),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        report = session_report_data(session)
        return Response({
            'verification': AuditVerificationSerializer(verification).data,
            'created': created,
            'progress': {
                'expected': report['expected_count'],
                'verified': report['verified_count'],
                'progress_pct': session.progress_pct,
            },
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
