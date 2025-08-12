
# En tu archivo urls.py principal (aerolinea/urls.py)
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from gestion import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Página principal
    path('', views.panel_resumen, name='panel_resumen'),  # o la vista que uses
   path('', views.home_view, name='home'), 
    # Otras páginas principales
    path('reservar/', views.reservar_asiento, name='reservar_asiento'),
    path('reportes/', views.reporte_pasajeros, name='reporte_pasajeros'),
    
    # URLs de autenticación con redirección explícita
    p path('admin/', admin.site.urls),

    path('', views.panel_resumen, name='panel_resumen'),

    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),

    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='login'
    ), name='logout'),

    path('accounts/', include('django.contrib.auth.urls')),
    
]