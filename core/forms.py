from django import forms
from .models import Item, Inspection, Transfer

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        exclude = ("uuid", "uid", "qr_code_image", "average_condition",
                   "last_inspection_at", "current_holder")

class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        exclude = ("inspector", "item",)

class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        exclude = ("moved_by",)
