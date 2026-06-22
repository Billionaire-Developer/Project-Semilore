from django.urls import path

from core import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Items
    path('items/', views.ItemListView.as_view(), name='item-list'),
    path('items/add/', views.ItemCreateView.as_view(), name='item-add'),
    path('items/<int:pk>/', views.ItemDetailView.as_view(), name='item-detail'),
    path('items/<int:pk>/edit/', views.ItemUpdateView.as_view(), name='item-edit'),
    path('items/<int:pk>/label/', views.ItemLabelPrintView.as_view(), name='item-label'),
    path('items/<int:item_pk>/inspect/', views.InspectionCreateView.as_view(), name='inspection-add'),

    # Verify (QR landing)
    path('verify/<uuid:uuid>/', views.VerifyItemView.as_view(), name='verify-item'),

    # Inspections & transfers
    path('inspections/', views.InspectionListView.as_view(), name='inspection-list'),
    path('transfers/', views.TransferListView.as_view(), name='transfer-list'),
    path('transfers/add/', views.TransferCreateView.as_view(), name='transfer-add'),

    # Org
    path('org/faculties/', views.FacultyListView.as_view(), name='faculty-list'),
    path('org/faculties/add/', views.FacultyCreateView.as_view(), name='faculty-add'),
    path('org/departments/', views.DepartmentListView.as_view(), name='department-list'),
    path('org/departments/add/', views.DepartmentCreateView.as_view(), name='department-add'),
    path('org/offices/', views.OfficeListView.as_view(), name='office-list'),
    path('org/offices/add/', views.OfficeCreateView.as_view(), name='office-add'),

    # Audits
    path('audits/', views.AuditSessionListView.as_view(), name='audit-list'),
    path('audits/add/', views.AuditSessionCreateView.as_view(), name='audit-add'),
    path('audits/<int:pk>/', views.AuditSessionDetailView.as_view(), name='audit-session-detail'),
    path('audits/<int:pk>/activate/', views.AuditSessionActivateView.as_view(), name='audit-activate'),
    path('audits/<int:pk>/close/', views.AuditSessionCloseView.as_view(), name='audit-close'),
    path('audits/<int:pk>/report/', views.AuditReportView.as_view(), name='audit-report'),
    path('audits/<int:pk>/scanner/', views.AuditScannerView.as_view(), name='audit-scanner'),
    path('audits/<int:pk>/verify/', views.AuditVerifyAPIView.as_view(), name='audit-verify-api'),
    path('items/lookup/', views.ItemLookupByUIDView.as_view(), name='item-lookup'),
]
