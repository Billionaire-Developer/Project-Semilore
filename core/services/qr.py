import io
import logging

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def item_verify_url(item):
    domain = settings.INVENTORY_QR_DOMAIN.rstrip('/')
    return f"{domain}/core/verify/{item.uuid}/"


def generate_qr_for_item(item, save=True):
    """Generate QR image encoding the fixed production verify URL with item UUID."""
    url = item_verify_url(item)
    try:
        qr = qrcode.make(url)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        buf.seek(0)
        filename = f"{item.uuid}.png"
        if item.qr_code_image:
            item.qr_code_image.delete(save=False)
        item.qr_code_image.save(filename, ContentFile(buf.read()), save=save)
        return True
    except Exception:
        logger.exception("QR generation failed for item %s", item.uid)
        return False
