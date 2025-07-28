from django.contrib import admin
from django.urls import path, include  # <== agregá include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gestion.urls')),  # <== conectamos las URLs de la app
]
