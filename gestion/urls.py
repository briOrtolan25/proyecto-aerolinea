from django.urls import path
from django.shortcuts import redirect
from . import views
from gestion.views import (
    login_view,
    logout_view,
    registro_view,
    vuelos_disponibles,
    reservar_asiento,
    ver_boleto,
    generar_pdf_boleto,
    reporte_pasajeros,
    exportar_reporte_pdf,
    exportar_reporte_csv,
    vuelo_admin,
    editar_vuelo,
    agregar_vuelo,
    cancelar_vuelo,
)

# Vista raíz que redirige según el rol
def home_redirect(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'rol') and request.user.rol == request.user.Rol.ADMIN:
            return redirect('vuelo_admin')
        else:
            return redirect('vuelos_disponibles')
    return redirect('login')


urlpatterns = [
    # Raíz
    path('', home_redirect, name='home'),

    # Autenticación
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('registro/', registro_view, name='registro'),

    # Vuelos para pasajeros
    path('vuelos/', vuelos_disponibles, name='vuelos_disponibles'),
    path('reservar_asiento/', reservar_asiento, name='reservar_asiento'),

    # Boletos
    path('boleto/<int:reserva_id>/', ver_boleto, name='ver_boleto'),
    path('boleto/pdf/<int:reserva_id>/', generar_pdf_boleto, name='generar_pdf_boleto'),

    # Panel de administración de vuelos (solo admin) — prefijo panel/
    path('panel/vuelos/', vuelo_admin, name='vuelo_admin'),
    path('panel/vuelos/agregar/', agregar_vuelo, name='agregar_vuelo_admin'),
    path('panel/vuelos/editar/<int:vuelo_id>/', editar_vuelo, name='editar_vuelo'),
    path('panel/vuelos/cancelar/<int:vuelo_id>/', cancelar_vuelo, name='cancelar_vuelo'),

    # Reportes de pasajeros (solo admin)
    path('panel/reporte/pasajeros/<int:vuelo_id>/', reporte_pasajeros, name='reporte_pasajeros'),
    path('panel/reporte/pdf/<int:vuelo_id>/', exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('panel/reporte/csv/<int:vuelo_id>/', exportar_reporte_csv, name='exportar_reporte_csv'),
]
