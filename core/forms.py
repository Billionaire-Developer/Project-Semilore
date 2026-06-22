from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import (
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

User = get_user_model()

TW_INPUT = 'form-input block w-full rounded-lg border-outline-variant bg-surface-bright text-on-surface px-4 py-3 focus:outline-none transition-shadow font-body-md text-body-md'
TW_SELECT = 'form-select block w-full rounded-lg border-outline-variant bg-surface-bright text-on-surface px-4 py-3 focus:outline-none transition-shadow font-body-md text-body-md'
TW_CHECKBOX = 'w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary focus:ring-2 bg-surface-bright transition-shadow'


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': TW_INPUT, 'placeholder': 'Username', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TW_INPUT, 'placeholder': 'Password'})
    )


class FacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ('code', 'name')
        widgets = {
            'code': forms.TextInput(attrs={'class': TW_INPUT}),
            'name': forms.TextInput(attrs={'class': TW_INPUT}),
        }


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('faculty', 'code', 'name')
        widgets = {
            'faculty': forms.Select(attrs={'class': TW_SELECT}),
            'code': forms.TextInput(attrs={'class': TW_INPUT}),
            'name': forms.TextInput(attrs={'class': TW_INPUT}),
        }


class OfficeForm(forms.ModelForm):
    class Meta:
        model = Office
        fields = ('department', 'code', 'name', 'building', 'room', 'floor')
        widgets = {
            'department': forms.Select(attrs={'class': TW_SELECT}),
            'code': forms.TextInput(attrs={'class': TW_INPUT}),
            'name': forms.TextInput(attrs={'class': TW_INPUT}),
            'building': forms.TextInput(attrs={'class': TW_INPUT}),
            'room': forms.TextInput(attrs={'class': TW_INPUT}),
            'floor': forms.TextInput(attrs={'class': TW_INPUT}),
        }


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        exclude = (
            'uuid', 'uid', 'qr_code_image', 'average_condition',
            'last_inspection_at', 'current_holder',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': TW_INPUT}),
            'category': forms.TextInput(attrs={'class': TW_INPUT}),
            'serial_number': forms.TextInput(attrs={'class': TW_INPUT}),
            'department': forms.Select(attrs={'class': TW_SELECT}),
            'office': forms.Select(attrs={'class': TW_SELECT}),
            'purchase_date': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'warranty_until': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
            'status': forms.Select(attrs={'class': TW_SELECT}),
        }


class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        exclude = ('inspector', 'item', 'is_audit_auto')
        widgets = {
            'condition_score': forms.NumberInput(attrs={'class': TW_INPUT, 'min': 1, 'max': 5}),
            'functional': forms.CheckboxInput(attrs={'class': TW_CHECKBOX}),
            'comments': forms.Textarea(attrs={'class': TW_INPUT, 'rows': 3}),
            'next_due_date': forms.DateInput(attrs={'class': TW_INPUT, 'type': 'date'}),
        }


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        exclude = ('moved_by', 'from_department', 'from_office')
        widgets = {
            'item': forms.Select(attrs={'class': TW_SELECT}),
            'to_department': forms.Select(attrs={'class': TW_SELECT}),
            'to_office': forms.Select(attrs={'class': TW_SELECT}),
            'notes': forms.Textarea(attrs={'class': TW_INPUT, 'rows': 3}),
        }


class AuditSessionForm(forms.ModelForm):
    class Meta:
        model = AuditSession
        fields = ('title', 'department', 'office', 'notes')
        widgets = {
            'title': forms.TextInput(attrs={'class': TW_INPUT}),
            'department': forms.Select(attrs={'class': TW_SELECT}),
            'office': forms.Select(attrs={'class': TW_SELECT}),
            'notes': forms.Textarea(attrs={'class': TW_INPUT, 'rows': 3}),
        }


class AuditVerificationForm(forms.Form):
    status = forms.ChoiceField(
        choices=AuditVerification.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': TW_SELECT}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TW_INPUT, 'rows': 2}),
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('role', 'faculty', 'department')
        widgets = {
            'role': forms.Select(attrs={'class': TW_SELECT}),
            'faculty': forms.Select(attrs={'class': TW_SELECT}),
            'department': forms.Select(attrs={'class': TW_SELECT}),
        }
