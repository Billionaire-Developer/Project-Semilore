from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

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


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'faculty', 'next_uid_sequence')
    list_filter = ('faculty',)
    search_fields = ('code', 'name')


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'building', 'room', 'floor')
    list_filter = ('department__faculty', 'department')
    search_fields = ('code', 'name', 'building', 'room')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('uid', 'uuid', 'name', 'department', 'office', 'status', 'last_inspection_at')
    list_filter = ('status', 'department', 'category')
    search_fields = ('uid', 'uuid', 'name', 'serial_number')
    readonly_fields = ('uuid', 'uid', 'qr_code_image')


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ('item', 'inspected_at', 'inspector', 'condition_score', 'is_audit_auto')
    list_filter = ('is_audit_auto', 'functional')


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('item', 'moved_at', 'moved_by', 'to_department', 'to_office')


@admin.register(AuditSession)
class AuditSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'office', 'status', 'started_by', 'started_at', 'closed_at')
    list_filter = ('status', 'department')


@admin.register(AuditVerification)
class AuditVerificationAdmin(admin.ModelAdmin):
    list_display = ('session', 'item', 'status', 'verified_by', 'verified_at', 'scan_method')
    list_filter = ('status', 'scan_method')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'model_name', 'object_pk', 'actor', 'timestamp')
    list_filter = ('action', 'model_name')
    readonly_fields = ('action', 'actor', 'model_name', 'object_pk', 'timestamp', 'data')
