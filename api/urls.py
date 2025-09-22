from django.urls import path, include
from rest_framework import routers
from .views import ItemViewSet, InspectionViewSet, FacultyViewSet, DepartmentViewSet, LocationViewSet

router = routers.DefaultRouter()
router.register('items', ItemViewSet, basename='item')
router.register('inspections', InspectionViewSet, basename='inspection')
router.register('faculties', FacultyViewSet)
router.register('departments', DepartmentViewSet)
router.register('locations', LocationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
