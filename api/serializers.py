from rest_framework import serializers

from core.models import (
    AuditSession,
    AuditVerification,
    Department,
    Faculty,
    Inspection,
    Item,
    Office,
    Transfer,
)


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)

    class Meta:
        model = Department
        fields = '__all__'


class OfficeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Office
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    verify_url = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    office_name = serializers.CharField(source='office.name', read_only=True, allow_null=True)

    class Meta:
        model = Item
        read_only_fields = (
            'uid', 'uuid', 'qr_code_image', 'last_inspection_at', 'average_condition', 'verify_url',
        )
        fields = '__all__'

    def get_verify_url(self, obj):
        from core.services.qr import item_verify_url
        return item_verify_url(obj)


class InspectionSerializer(serializers.ModelSerializer):
    inspector = serializers.PrimaryKeyRelatedField(read_only=True)
    item_uid = serializers.CharField(source='item.uid', read_only=True)

    class Meta:
        model = Inspection
        fields = '__all__'
        read_only_fields = ('inspected_at', 'inspector', 'is_audit_auto')


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'


class AuditVerificationSerializer(serializers.ModelSerializer):
    item_uid = serializers.CharField(source='item.uid', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = AuditVerification
        fields = '__all__'
        read_only_fields = ('verified_by', 'verified_at')


class AuditSessionSerializer(serializers.ModelSerializer):
    expected_count = serializers.IntegerField(read_only=True)
    verified_count = serializers.IntegerField(read_only=True)
    progress_pct = serializers.FloatField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    office_name = serializers.CharField(source='office.name', read_only=True, allow_null=True)

    class Meta:
        model = AuditSession
        fields = '__all__'
        read_only_fields = ('started_by', 'started_at', 'closed_at')


class AuditVerifyRequestSerializer(serializers.Serializer):
    item_uuid = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=AuditVerification.STATUS_CHOICES,
        default=AuditVerification.STATUS_VERIFIED,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    scan_method = serializers.ChoiceField(
        choices=AuditVerification.SCAN_METHODS,
        default=AuditVerification.SCAN_QR,
    )
