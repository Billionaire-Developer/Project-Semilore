from celery import shared_task
from django.utils import timezone
from .models import Item, Inspection
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_overdue_inspections():
    today = timezone.now().date()
    overdue = Inspection.objects.filter(next_due_date__lt=today).select_related('item','inspector')
    recipients = {}
    for ins in overdue:
        key = ins.item.current_holder.email if ins.item.current_holder else None
        recipients.setdefault(key, []).append(ins)

    for recipient, items in recipients.items():
        if not recipient:
            continue
        try:
            send_mail(
                subject='Overdue inventory inspections',
                message=f'There are {len(items)} overdue inspections.',
                from_email='noreply@example.com',
                recipient_list=[recipient],
                fail_silently=True,
            )
        except Exception:
            logger.exception("Failed to send overdue email")
