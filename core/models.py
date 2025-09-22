from django.db import models, transaction
from django.conf import settings
import uuid
import os
from django.utils import timezone

def qr_upload_path(instance, filename):
    return os.path.join('qrcodes', f"{instance.uid}.png")

class Faculty(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    next_uid_sequence = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('faculty', 'code')

    def __str__(self):
        return f"{self.code} ({self.faculty.code})"

class Location(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    building = models.CharField(max_length=100)
    room = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.building} - {self.room}"

class Item(models.Model):
    uid = models.CharField(max_length=64, unique=True, db_index=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    current_holder = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, default='active')
    qr_code_image = models.ImageField(upload_to=qr_upload_path, null=True, blank=True)
    last_inspection_at = models.DateTimeField(null=True, blank=True)
    average_condition = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.uid} - {self.name}"

    @staticmethod
    def generate_uid(department):
        # atomic increment of department.next_uid_sequence
        with transaction.atomic():
            dept = Department.objects.select_for_update().get(pk=department.pk)
            seq = dept.next_uid_sequence
            dept.next_uid_sequence = seq + 1
            dept.save()
        return f"{dept.faculty.code}-{dept.code}-{str(seq).zfill(6)}"

from django.core.validators import MaxValueValidator, MinValueValidator

class Inspection(models.Model):
    item = models.ForeignKey(Item, related_name='inspections', on_delete=models.CASCADE)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    inspected_at = models.DateTimeField(auto_now_add=True)
    condition_score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    functional = models.BooleanField(default=True)
    comments = models.TextField(blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    photos = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # update item aggregates
        ins = Inspection.objects.filter(item=self.item)
        avg = ins.aggregate(models.Avg('condition_score'))['condition_score__avg']
        self.item.average_condition = round(avg or 0, 2)
        self.item.last_inspection_at = self.inspected_at
        self.item.save(update_fields=['average_condition', 'last_inspection_at'])

class Transfer(models.Model):
    item = models.ForeignKey(Item, related_name='transfers', on_delete=models.CASCADE)
    from_department = models.ForeignKey(Department, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    to_department = models.ForeignKey(Department, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    from_location = models.ForeignKey(Location, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    to_location = models.ForeignKey(Location, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    moved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    moved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

class AuditLog(models.Model):
    ACTIONS = [
        ('create', 'create'),
        ('update', 'update'),
        ('delete', 'delete'),
        ('inspect', 'inspect'),
        ('transfer', 'transfer'),
    ]
    action = models.CharField(max_length=20, choices=ACTIONS)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    model_name = models.CharField(max_length=100)
    object_pk = models.CharField(max_length=200, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.JSONField(null=True, blank=True)
