from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from core.views import InventoryLoginView, InventoryLogoutView, ProfileView, InventorySignupView, InspectionPDFView, index
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('core/', include('core.urls')),
    path('accounts/login/', InventoryLoginView.as_view(), name='login'),
    path('accounts/signup/', InventorySignupView.as_view(), name='signup'),
    path('accounts/logout/', InventoryLogoutView.as_view(), name='logout'),
    path('accounts/profile/', ProfileView.as_view(), name='profile'),
    path('reports/inspection-pdf/', InspectionPDFView.as_view(), name='inspection-pdf'),
    path('', index, name='index'),
    path('home/', index, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
