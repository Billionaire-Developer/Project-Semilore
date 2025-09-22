from django.contrib import admin
from .models import Faculty, Department, Location, Item, Inspection, Transfer, AuditLog

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('code','name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code','name','faculty','next_uid_sequence')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('building','room','department')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('uid','name','department','location','status','last_inspection_at')

@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ('item','inspected_at','inspector','condition_score')

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('item','moved_at','moved_by')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action','model_name','object_pk','actor','timestamp')
