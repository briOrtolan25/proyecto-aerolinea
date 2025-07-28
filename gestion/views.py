from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib import messages

import os
import io
import base64
import qrcode
import csv

from django.db.models import Sum, Count, Q
from django.conf import settings
from .models import Vuelo, Asiento, Reserva, Boleto, Pasajero
from .forms import ReservaForm

# Vista: Lista de vuelos
def vuelos_disponibles(request):
    vuelos = Vuelo.objects.all().order_by('fecha_salida')
    return render(request, 'gestion/vuelos.html', {'vuelos': vuelos})

# Vista: Formulario de reserva (con validaciones + mensajes)
def reservar_asiento(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            asiento = form.cleaned_data['asiento']
            if asiento.estado == 'disponible':
                asiento.estado = 'reservado'
                asiento.save()
                reserva = form.save()

                Boleto.objects.create(
                    reserva=reserva,
                    codigo_barra=reserva.codigo_reserva,
                    estado='activo'
                )

                return redirect('ver_boleto', reserva_id=reserva.id)
        else:
            messages.warning(request, '⚠️ Por favor corregí los errores del formulario.')
    else:
        form = ReservaForm()

    form.fields['asiento'].queryset = Asiento.objects.filter(estado='disponible')
    return render(request, 'gestion/reserva.html', {'form': form})

# Vista: Ver boleto en pantalla
def ver_boleto(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    boleto = reserva.boleto
    return render(request, 'gestion/boleto.html', {'reserva': reserva, 'boleto': boleto})

# Vista: Generar PDF con logo y QR
def generar_pdf_boleto(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    boleto = reserva.boleto

    logo_path = os.path.join(settings.BASE_DIR, "static", "logo.jpg")
    with open(logo_path, "rb") as image_file:
        logo_base64 = base64.b64encode(image_file.read()).decode()

    qr_data = f"""
Reserva: {reserva.codigo_reserva}
Pasajero: {reserva.pasajero.nombre}
Vuelo: {reserva.vuelo.origen} → {reserva.vuelo.destino}
Asiento: {reserva.asiento.numero}
Precio: ${reserva.precio}
"""
    qr_img = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()

    template = get_template('gestion/boleto_pdf.html')
    html = template.render({
        'reserva': reserva,
        'boleto': boleto,
        'logo_base64': logo_base64,
        'qr_data': qr_image_base64,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="boleto_{reserva.codigo_reserva}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF')
    return response

# Vista: Anular boleto desde la web
def anular_boleto(request, boleto_id):
    boleto = get_object_or_404(Boleto, id=boleto_id)
    boleto.anular()
    messages.success(request, f"Boleto {boleto.codigo_barra} anulado correctamente.")
    return redirect('ver_boleto', reserva_id=boleto.reserva.id)

# Vista: Reporte de pasajeros por vuelo
def reporte_pasajeros(request):
    vuelos = Vuelo.objects.all().order_by('fecha_salida')
    vuelo_id = request.GET.get('vuelo_id')
    reservas = None

    if vuelo_id:
        reservas = Reserva.objects.filter(vuelo_id=vuelo_id)

    return render(request, 'gestion/reporte_pasajeros.html', {
        'vuelos': vuelos,
        'reservas': reservas,
        'vuelo_seleccionado': vuelo_id,
    })

# Exportar PDF del reporte
def exportar_reporte_pdf(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    reservas = Reserva.objects.filter(vuelo=vuelo)
    template = get_template('gestion/reporte_pdf.html')
    html = template.render({'vuelo': vuelo, 'reservas': reservas})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_pasajeros_vuelo_{vuelo.id}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF')
    return response

# Exportar CSV del reporte
def exportar_reporte_csv(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    reservas = Reserva.objects.filter(vuelo=vuelo)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_pasajeros_vuelo_{vuelo.id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Pasajero', 'Documento', 'Asiento', 'Precio', 'Código Reserva'])
    for reserva in reservas:
        writer.writerow([
            reserva.pasajero.nombre,
            reserva.pasajero.documento,
            reserva.asiento.numero,
            reserva.precio,
            reserva.codigo_reserva
        ])
    return response

# ✅ Panel resumen general del sistema
def panel_resumen(request):
    
    total_vuelos = Vuelo.objects.count()
    total_reservas = Reserva.objects.count()
    total_pasajeros = Pasajero.objects.count()
    total_asientos = Asiento.objects.count()
    asientos_ocupados = Asiento.objects.exclude(estado='disponible').count()
    asientos_disponibles = Asiento.objects.filter(estado='disponible').count()
    ingresos = Reserva.objects.aggregate(total=Sum('precio'))['total'] or 0
    print("💸 INGRESOS TOTALES:", ingresos)

    return render(request, 'gestion/resumen.html', {
        'total_vuelos': total_vuelos,
        'total_reservas': total_reservas,
        'total_pasajeros': total_pasajeros,
        'asientos_ocupados': asientos_ocupados,
        'asientos_disponibles': asientos_disponibles,
        'ingresos_totales': ingresos, 
    })
