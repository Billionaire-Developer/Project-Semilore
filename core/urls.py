from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
     path("", views.DashboardView.as_view(), name="dashboard"),

    # Items
    path("items/", views.ItemListView.as_view(), name="item-list"),
    path("items/<int:pk>/", views.ItemDetailView.as_view(), name="item-detail"),
    path("items/add/", views.ItemCreateView.as_view(), name="item-add"),
    path("items/<int:pk>/edit/", views.ItemUpdateView.as_view(), name="item-edit"),
    path("items/<int:item_pk>/inspect/", views.InspectionCreateView.as_view(), name="inspection-add"),
    path("inspections/", views.InspectionListView.as_view(), name="inspection-list"),
    path("transfers/", views.TransferListView.as_view(), name="transfer-list"),
    path("transfers/add/", views.TransferCreateView.as_view(), name="transfer-add"),
]



if settings.DEBUG:
    urlpatterns +=static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

