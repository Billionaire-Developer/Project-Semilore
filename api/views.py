from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from core.models import Item, Inspection, Transfer, Faculty, Department, Location
from .serializers import ItemSerializer, InspectionSerializer, FacultySerializer, DepartmentSerializer, LocationSerializer
from django.db import transaction
from django.shortcuts import get_object_or_404
from .permissions import IsInspector
from django.core.files.base import ContentFile
import qrcode
import io
import logging

logger = logging.getLogger(__name__)

class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related('department__faculty','location').all().order_by('-created_at')
    serializer_class = ItemSerializer

    def perform_create(self, serializer):
        department = serializer.validated_data.get('department')
        if not department:
            raise serializers.ValidationError("Department is required to generate UID.")
        uid = Item.generate_uid(department)
        serializer.save(uid=uid)

        item = serializer.instance
        try:
            qr = qrcode.make(uid)
            buf = io.BytesIO()
            qr.save(buf, format='PNG')
            buf.seek(0)
            item.qr_code_image.save(f"{uid}.png", ContentFile(buf.read()), save=True)
        except Exception:
            logger.exception("QR generation failed")

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
            except Exception as e:
                logger.exception("Failed to create inspection")
                return Response({'detail': 'Failed to create inspection'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        item = self.get_object()
        data = request.data
        try:
            to_dept_id = data.get('to_department')
            to_loc_id = data.get('to_location')
            to_dept = Department.objects.get(pk=to_dept_id) if to_dept_id else None
            to_loc = Location.objects.get(pk=to_loc_id) if to_loc_id else None
            tr = Transfer.objects.create(
                item=item,
                from_department=item.department,
                to_department=to_dept,
                from_location=item.location,
                to_location=to_loc,
                moved_by=request.user,
                notes=data.get('notes',''),
            )
            item.department = to_dept or item.department
            item.location = to_loc or item.location
            item.save()
            return Response({'detail':'transfer recorded'}, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Transfer failed")
            return Response({'detail':'transfer failed'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bulk_import(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'detail':'file required'}, status=status.HTTP_400_BAD_REQUEST)
        import csv, codecs
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
                    department=department
                )
                created.append(item.uid)
            except Exception as e:
                logger.exception("bulk import row failed")
                errors.append({'row': i, 'error': str(e)})
        return Response({'created': created, 'errors': errors})

class InspectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inspection.objects.select_related('item','inspector').all().order_by('-inspected_at')
    serializer_class = InspectionSerializer
