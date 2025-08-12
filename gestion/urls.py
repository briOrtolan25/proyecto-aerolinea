from django.urls import path
from gestion.views import (
    login_view,
    logout_view,
    home_view,
    registro_view,
    vuelos_disponibles,
    crear_reserva,
    reservar_asiento,
    ver_boleto,
    generar_pdf_boleto,
    anular_boleto,
    reporte_pasajeros,
    exportar_reporte_pdf,
    exportar_reporte_csv,
    panel_resumen,
)

urlpatterns = [
    path('', home_view, name='home'),

    # Autenticación
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('registro/', registro_view, name='registro'),

    # Vuelos
    path('vuelos/', vuelos_disponibles, name='vuelos_disponibles'),

    # Reservas
    path('reserva/crear/', crear_reserva, name='crear_reserva'),
    path('reserva/asiento/', reservar_asiento, name='reservar_asiento'),

    # Boletos
    path('boleto/<int:reserva_id>/', ver_boleto, name='ver_boleto'),
    path('boleto/pdf/<int:reserva_id>/', generar_pdf_boleto, name='generar_pdf_boleto'),
    path('boleto/anular/<int:boleto_id>/', anular_boleto, name='anular_boleto'),

    # Reportes pasajeros
    path('reporte/pasajeros/', reporte_pasajeros, name='reporte_pasajeros'),
    path('reporte/pdf/<int:vuelo_id>/', exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reporte/csv/<int:vuelo_id>/', exportar_reporte_csv, name='exportar_reporte_csv'),

    # Panel resumen
    path('panel/', panel_resumen, name='panel_resumen'),
]
