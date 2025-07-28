from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_resumen, name='panel_resumen'),
    path('vuelos/', views.vuelos_disponibles, name='vuelos_disponibles'),
    path('reservar/', views.reservar_asiento, name='reservar_asiento'),
    path('boleto/<int:reserva_id>/', views.ver_boleto, name='ver_boleto'),
    path('boleto/<int:reserva_id>/pdf/', views.generar_pdf_boleto, name='boleto_pdf'),
    path('boleto/<int:boleto_id>/anular/', views.anular_boleto, name='anular_boleto'),
    path('reporte/', views.reporte_pasajeros, name='reporte_pasajeros'),
    path('reporte/<int:vuelo_id>/pdf/', views.exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reporte/<int:vuelo_id>/csv/', views.exportar_reporte_csv, name='exportar_reporte_csv'),
]

