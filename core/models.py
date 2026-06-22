from django.db import models, transaction
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
import uuid
import os


def qr_upload_path(instance, filename):
    return os.path.join('qrcodes', f"{instance.uuid}.png")


class Faculty(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = 'faculties'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    next_uid_sequence = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('faculty', 'code')

    def __str__(self):
        return f"{self.code} ({self.faculty.code})"


class Office(models.Model):
    """Merged office/location: department office with optional building and room."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='offices')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    building = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=50, blank=True)
    floor = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ('department', 'code')
        ordering = ['department', 'name']

    def __str__(self):
        parts = [self.name]
        if self.building:
            parts.append(self.building)
        if self.room:
            parts.append(self.room)
        return ' — '.join(parts)


class UserProfile(models.Model):
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_FACULTY_ADMIN = 'faculty_admin'
    ROLE_DEPT_ADMIN = 'dept_admin'
    ROLE_AUDITOR = 'auditor'
    ROLE_VIEWER = 'viewer'

    ROLES = [
        (ROLE_SUPER_ADMIN, 'Super Admin'),
        (ROLE_FACULTY_ADMIN, 'Faculty Admin'),
        (ROLE_DEPT_ADMIN, 'Department Admin'),
        (ROLE_AUDITOR, 'Auditor / Tracker'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLES, default=ROLE_VIEWER)
    faculty = models.ForeignKey(Faculty, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role in (self.ROLE_SUPER_ADMIN, self.ROLE_FACULTY_ADMIN, self.ROLE_DEPT_ADMIN)

    @property
    def can_manage_items(self):
        return self.role in (self.ROLE_SUPER_ADMIN, self.ROLE_FACULTY_ADMIN, self.ROLE_DEPT_ADMIN)

    @property
    def can_run_audits(self):
        return self.role in (self.ROLE_SUPER_ADMIN, self.ROLE_FACULTY_ADMIN, self.ROLE_DEPT_ADMIN, self.ROLE_AUDITOR)


class Item(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_DISPOSED = 'disposed'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_DISPOSED, 'Disposed'),
    ]

    uid = models.CharField(max_length=64, unique=True, db_index=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='items')
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    current_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='held_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    qr_code_image = models.ImageField(upload_to=qr_upload_path, null=True, blank=True)
    last_inspection_at = models.DateTimeField(null=True, blank=True)
    average_condition = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.uid} - {self.name}"

    @staticmethod
    def generate_uid(department):
        with transaction.atomic():
            dept = Department.objects.select_for_update().get(pk=department.pk)
            seq = dept.next_uid_sequence
            dept.next_uid_sequence = seq + 1
            dept.save(update_fields=['next_uid_sequence'])
        return f"{dept.faculty.code}-{dept.code}-{str(seq).zfill(6)}"


class Inspection(models.Model):
    item = models.ForeignKey(Item, related_name='inspections', on_delete=models.CASCADE)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    inspected_at = models.DateTimeField(auto_now_add=True)
    condition_score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    functional = models.BooleanField(default=True)
    comments = models.TextField(blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    photos = models.JSONField(null=True, blank=True)
    is_audit_auto = models.BooleanField(default=False)

    class Meta:
        ordering = ['-inspected_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        avg = Inspection.objects.filter(item=self.item).aggregate(
            models.Avg('condition_score')
        )['condition_score__avg']
        self.item.average_condition = round(avg or 0, 2)
        self.item.last_inspection_at = self.inspected_at
        self.item.save(update_fields=['average_condition', 'last_inspection_at'])


class Transfer(models.Model):
    item = models.ForeignKey(Item, related_name='transfers', on_delete=models.CASCADE)
    from_department = models.ForeignKey(Department, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    to_department = models.ForeignKey(Department, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    from_office = models.ForeignKey(Office, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    to_office = models.ForeignKey(Office, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    moved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    moved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-moved_at']


class AuditSession(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    ]

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='audit_sessions')
    office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_sessions')
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='started_audits')
    started_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return self.title

    @property
    def expected_count(self):
        qs = Item.objects.filter(department=self.department, status=Item.STATUS_ACTIVE)
        if self.office_id:
            qs = qs.filter(office=self.office)
        return qs.count()

    @property
    def verified_count(self):
        return self.verifications.filter(status=AuditVerification.STATUS_VERIFIED).count()

    @property
    def progress_pct(self):
        total = self.expected_count
        if not total:
            return 0
        return round((self.verified_count / total) * 100, 1)

    def close(self):
        self.status = self.STATUS_CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])


class AuditVerification(models.Model):
    STATUS_VERIFIED = 'verified'
    STATUS_MISSING = 'missing'
    STATUS_WRONG_LOCATION = 'wrong_location'
    STATUS_DAMAGED = 'damaged'
    STATUS_CHOICES = [
        (STATUS_VERIFIED, 'Verified — present'),
        (STATUS_MISSING, 'Missing — not found'),
        (STATUS_WRONG_LOCATION, 'Wrong location'),
        (STATUS_DAMAGED, 'Present but damaged'),
    ]

    SCAN_QR = 'qr_scan'
    SCAN_MANUAL_UID = 'manual_uid'
    SCAN_MANUAL_SEARCH = 'manual_search'
    SCAN_METHODS = [
        (SCAN_QR, 'QR scan'),
        (SCAN_MANUAL_UID, 'Manual UID'),
        (SCAN_MANUAL_SEARCH, 'Manual search'),
    ]

    session = models.ForeignKey(AuditSession, related_name='verifications', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, related_name='audit_verifications', on_delete=models.CASCADE)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_VERIFIED)
    notes = models.TextField(blank=True)
    scan_method = models.CharField(max_length=20, choices=SCAN_METHODS, default=SCAN_QR)

    class Meta:
        unique_together = ('session', 'item')
        ordering = ['-verified_at']


class AuditLog(models.Model):
    ACTIONS = [
        ('create', 'create'),
        ('update', 'update'),
        ('delete', 'delete'),
        ('inspect', 'inspect'),
        ('transfer', 'transfer'),
        ('audit_verify', 'audit_verify'),
    ]
    action = models.CharField(max_length=20, choices=ACTIONS)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    model_name = models.CharField(max_length=100)
    object_pk = models.CharField(max_length=200, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
