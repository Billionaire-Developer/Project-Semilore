from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Item, Inspection, Transfer, AuditLog
import json

def log_action(action, instance, actor=None, extra=None):
    try:
        AuditLog.objects.create(
            action=action,
            actor=actor,
            model_name=instance.__class__.__name__,
            object_pk=str(getattr(instance, 'pk', None)),
            data=extra or {}
        )
    except Exception:
        import logging
        logging.exception("Failed to write audit log")

@receiver(post_save, sender=Item)
def item_saved(sender, instance, created, **kwargs):
    log_action('create' if created else 'update', instance)

@receiver(post_save, sender=Inspection)
def inspection_saved(sender, instance, created, **kwargs):
    if created:
        log_action('inspect', instance, actor=instance.inspector, extra={
            'condition_score': instance.condition_score,
            'functional': instance.functional,
            'next_due_date': str(instance.next_due_date) if instance.next_due_date else None
        })

@receiver(post_save, sender=Transfer)
def transfer_saved(sender, instance, created, **kwargs):
    if created:
        log_action('transfer', instance, actor=instance.moved_by, extra={'notes': instance.notes})

@receiver(pre_delete)
def on_delete(sender, instance, **kwargs):
    try:
        if hasattr(instance, 'pk'):
            AuditLog.objects.create(action='delete', actor=None, model_name=sender.__name__, object_pk=str(instance.pk), data={})
    except Exception:
        import logging
        logging.exception("Failed to write audit log for delete")
