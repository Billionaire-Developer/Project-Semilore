from django.urls import include, path
from rest_framework import routers

from .views import (
    AuditSessionViewSet,
    DepartmentViewSet,
    FacultyViewSet,
    InspectionViewSet,
    ItemViewSet,
    OfficeViewSet,
)

router = routers.DefaultRouter()
router.register('items', ItemViewSet, basename='item')
router.register('inspections', InspectionViewSet, basename='inspection')
router.register('faculties', FacultyViewSet, basename='faculty')
router.register('departments', DepartmentViewSet, basename='department')
router.register('offices', OfficeViewSet, basename='office')
router.register('audit-sessions', AuditSessionViewSet, basename='audit-session')

urlpatterns = [
    path('', include(router.urls)),
]
