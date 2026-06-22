from django.db import transaction

from core.models import AuditVerification, Inspection, Item


def verify_item_in_session(session, item, user, status=AuditVerification.STATUS_VERIFIED,
                           notes='', scan_method=AuditVerification.SCAN_QR):
    """
    Record audit verification and auto-create a minimal inspection record.
    Returns (verification, created).
    """
    if session.status != session.STATUS_ACTIVE:
        raise ValueError('Audit session is not active.')

    with transaction.atomic():
        verification, created = AuditVerification.objects.update_or_create(
            session=session,
            item=item,
            defaults={
                'verified_by': user,
                'status': status,
                'notes': notes,
                'scan_method': scan_method,
            },
        )

        if created:
            Inspection.objects.create(
                item=item,
                inspector=user,
                condition_score=3,
                functional=status != AuditVerification.STATUS_DAMAGED,
                comments=f"Auto inspection during audit: {session.title}",
                is_audit_auto=True,
            )

    return verification, created


def session_report_data(session):
    """Build reconciliation data for a closed or active audit session."""
    expected_qs = Item.objects.filter(department=session.department, status=Item.STATUS_ACTIVE)
    if session.office_id:
        expected_qs = expected_qs.filter(office=session.office)
    expected_ids = set(expected_qs.values_list('id', flat=True))

    verifications = session.verifications.select_related('item', 'verified_by').all()
    verified_ids = set()
    missing_items = []
    unexpected = []
    damaged = []

    for v in verifications:
        if v.status == AuditVerification.STATUS_VERIFIED:
            verified_ids.add(v.item_id)
            if v.item_id not in expected_ids:
                unexpected.append(v)
        elif v.status == AuditVerification.STATUS_DAMAGED:
            damaged.append(v)
            verified_ids.add(v.item_id)
        elif v.status == AuditVerification.STATUS_WRONG_LOCATION:
            unexpected.append(v)

    for item in expected_qs:
        if item.id not in verified_ids:
            missing_items.append(item)

    return {
        'session': session,
        'expected_count': len(expected_ids),
        'verified_count': len(verified_ids & expected_ids),
        'missing_items': missing_items,
        'unexpected': unexpected,
        'damaged': damaged,
        'progress_pct': session.progress_pct,
    }
