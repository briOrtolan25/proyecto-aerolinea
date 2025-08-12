from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

import os
import io
import base64
import qrcode
import csv

from .models import Vuelo, Asiento, Reserva, Boleto, Pasajero
from .forms import ReservaForm, RegistroForm


@login_required(login_url='login')
def home_view(request):
    return render(request, 'gestion/base.html')


def login_view(request):
    next_url = request.GET.get('next', '/')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(next_url)
        else:
            messages.error(request, "Usuario o contraseña inválidos.")
    else:
        form = AuthenticationForm()

    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ingresa tu usuario'})
    form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ingresa tu contraseña'})

    return render(request, 'gestion/login.html', {'form': form, 'next': next_url})


@login_required(login_url='login')
def logout_view(request):
    username = request.user.username
    logout(request)
    messages.success(request, f'¡Hasta luego {username}!')
    return redirect('login')


def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Corrige los errores para completar el registro.")
    else:
        form = RegistroForm()
    return render(request, 'accounts/registro.html', {'form': form})


@login_required(login_url='login')
def vuelos_disponibles(request):
    vuelos = Vuelo.objects.all().order_by('fecha_salida')
    return render(request, 'gestion/vuelos.html', {'vuelos': vuelos})


@login_required(login_url='login')
def reservar_asiento(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST, usuario=request.user)
        if form.is_valid():
            reserva = form.save()
            messages.success(request, "Reserva realizada con éxito.")
            # Redirigir a la página del boleto con el id de la reserva
            return redirect('ver_boleto', reserva_id=reserva.id)
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        vuelo_id = request.GET.get('vuelo')
        if vuelo_id:
            form = ReservaForm(usuario=request.user, initial={'vuelo': vuelo_id})
        else:
            form = ReservaForm(usuario=request.user)

    return render(request, 'gestion/reservar_asiento.html', {'form': form})


@login_required(login_url='login')
def ver_boleto(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, pasajero=request.user)
    boleto = getattr(reserva, 'boleto', None)
    return render(request, 'gestion/boleto.html', {'reserva': reserva, 'boleto': boleto})


@login_required(login_url='login')
def generar_pdf_boleto(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    # Generar QR en base64
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Reserva ID: {reserva.id}")
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img_qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Cargar logo en base64 desde static
    logo_path = os.path.join('gestion', 'static', 'gestion', 'img', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode('utf-8')
    else:
        logo_base64 = None

    # Renderizar plantilla
    template = get_template("boleto_pdf.html")
    html = template.render({
        "reserva": reserva,
        "qr_base64": qr_base64,
        "logo_base64": logo_base64
    })

    # Generar PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="boleto_{reserva.id}.pdf"'

    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=response, encoding='UTF-8')

    if pisa_status.err:
        return HttpResponse("Hubo un error al generar el PDF.", status=500)

    return response


@login_required(login_url='login')
def anular_boleto(request, boleto_id):
    boleto = get_object_or_404(Boleto, id=boleto_id)
    boleto.anular()
    messages.success(request, f"Boleto {boleto.codigo_barra} anulado correctamente.")
    return redirect('ver_boleto', reserva_id=boleto.reserva.id)


@login_required(login_url='login')
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


@login_required(login_url='login')
def exportar_reporte_pdf(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    reservas = Reserva.objects.filter(vuelo=vuelo)
    template = get_template('gestion/reporte_pdf.html')
    html = template.render({'vuelo': vuelo, 'reservas': reservas})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_pasajeros_vuelo_{vuelo.id}.pdf"'
    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('UTF-8')), dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
    return response


@login_required(login_url='login')
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
            reserva.precio_final,
            reserva.codigo_reserva
        ])
    return response


@login_required(login_url='login')
def crear_reserva(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Reserva creada correctamente.")
            return redirect('lista_reservas')  # Cambia a la url que quieras
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = ReservaForm(usuario=request.user)
    return render(request, 'gestion/crear_reserva.html', {'form': form})


@login_required(login_url='login')
def panel_resumen(request):
    total_vuelos = Vuelo.objects.count()
    total_reservas = Reserva.objects.count()
    total_pasajeros = Pasajero.objects.count()
    total_asientos = Asiento.objects.count()
    asientos_ocupados = Asiento.objects.exclude(estado=Asiento.Estado.DISPONIBLE).count()
    ingresos = Reserva.objects.aggregate(total=Sum('precio_final'))['total'] or 0
    asientos_disponibles = Asiento.objects.filter(estado=Asiento.Estado.DISPONIBLE).count()

    return render(request, 'gestion/resumen.html', {
        'total_vuelos': total_vuelos,
        'total_reservas': total_reservas,
        'total_pasajeros': total_pasajeros,
        'asientos_ocupados': asientos_ocupados,
        'asientos_disponibles': asientos_disponibles,
        'ingresos_totales': ingresos,
    })
