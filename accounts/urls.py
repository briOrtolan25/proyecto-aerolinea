# aerolinea/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from gestion import views

urlpatterns = [
    # Públicas
    path('', views.InicioView.as_view(), name='inicio'),
    path('vuelos/', views.ListaVuelosView.as_view(), name='lista_vuelos'),
    path('vuelos/<int:pk>/', views.DetalleVueloView.as_view(), name='detalle_vuelo'),
    
    # Autenticación
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Usuario autenticado
    path('reservas/', views.ListaReservasView.as_view(), name='lista_reservas'),
    path('reservas/<int:vuelo_id>/crear/', views.CrearReservaView.as_view(), name='crear_reserva'),
    path('reservas/<int:pk>/', views.DetalleReservaView.as_view(), name='detalle_reserva'),
    path('perfil/', views.perfil_view, name='perfil'),
    
    # Staff
    path('gestion/reservas/', views.GestionReservasView.as_view(), name='gestion_reservas'),
]