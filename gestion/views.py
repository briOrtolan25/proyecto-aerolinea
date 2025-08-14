from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.utils import timezone
from django import forms
import os, io, base64, qrcode, csv

from .models import Vuelo, Asiento, Reserva, Boleto, Usuario
from .forms import ReservaForm, RegistroForm, VueloForm

# -------------------------------
# FORMULARIO LOGIN PERSONALIZADO
# -------------------------------
class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Usuario'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Contraseña'}))

    def clean(self):
        cleaned_data = super().clean()
        user = authenticate(
            username=cleaned_data.get('username'),
            password=cleaned_data.get('password')
        )
        if not user:
            raise forms.ValidationError("Usuario o contraseña inválidos.")
        cleaned_data['user'] = user
        return cleaned_data

# -------------------------------
# DECORADORES PARA ROLES
# -------------------------------
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.rol == Usuario.Rol.ADMIN, login_url='login')(view_func)

def pasajero_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.rol == Usuario.Rol.PASAJERO, login_url='login')(view_func)

# -------------------------------
# LOGIN / LOGOUT / REGISTRO
# -------------------------------
def login_view(request):
    next_url = request.GET.get('next', '/')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            auth_login(request, form.cleaned_data['user'])
            return redirect(next_url)
        else:
            messages.error(request, "Usuario o contraseña inválidos.")
    else:
        form = LoginForm()
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
            return redirect('vuelos_disponibles')
        else:
            messages.error(request, "Corrige los errores para completar el registro.")
    else:
        form = RegistroForm()
    return render(request, 'gestion/registro.html', {'form': form})

# -------------------------------
# VISTAS DE PASAJERO
# -------------------------------
@login_required(login_url='login')
@pasajero_required
def vuelos_disponibles_pasajero(request):
    vuelos = Vuelo.objects.filter(fecha_salida__gte=timezone.now()).order_by('fecha_salida')
    return render(request, 'gestion/vuelos.html', {'vuelos': vuelos})

@login_required(login_url='login')
@pasajero_required
def reservar_asiento(request):
    vuelo_id = request.GET.get('vuelo')
    vuelo = None
    if vuelo_id:
        try:
            vuelo = Vuelo.objects.get(pk=vuelo_id)
        except Vuelo.DoesNotExist:
            messages.error(request, "Vuelo no válido.")
            return redirect('vuelos_disponibles')

    if request.method == 'POST':
        form = ReservaForm(request.POST, usuario=request.user)
        if form.is_valid():
            reserva = form.save()
            messages.success(request, "Reserva realizada con éxito.")
            return redirect('ver_boleto', reserva_id=reserva.id)
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = ReservaForm(usuario=request.user, initial={'vuelo': vuelo.id if vuelo else None})

    return render(request, 'gestion/reservar_asiento.html', {'form': form, 'vuelo': vuelo})

@login_required(login_url='login')
@pasajero_required
def ver_boleto(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, pasajero=request.user)
    boleto = getattr(reserva, 'boleto', None)
    return render(request, 'gestion/boleto.html', {'reserva': reserva, 'boleto': boleto})

@login_required(login_url='login')
@pasajero_required
def generar_pdf_boleto(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, pasajero=request.user)

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Reserva ID: {reserva.id}")
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img_qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    logo_path = os.path.join('gestion', 'static', 'gestion', 'img', 'logo.png')
    logo_base64 = None
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode('utf-8')

    template = get_template("gestion/boleto_pdf.html")
    html = template.render({"reserva": reserva, "qr_base64": qr_base64, "logo_base64": logo_base64})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="boleto_{reserva.id}.pdf"'

    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=response, encoding='UTF-8')
    if pisa_status.err:
        return HttpResponse("Hubo un error al generar el PDF.", status=500)
    return response

# -------------------------------
# VISTAS DE ADMIN
# -------------------------------
@login_required(login_url='login')
@admin_required
def panel_resumen(request):
    total_vuelos = Vuelo.objects.count()
    total_reservas = Reserva.objects.count()
    total_pasajeros = Usuario.objects.filter(rol=Usuario.Rol.PASAJERO).count()
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

@login_required(login_url='login')
@admin_required
def reporte_pasajeros(request, vuelo_id):
    vuelos = Vuelo.objects.all().order_by('fecha_salida')
    reservas = Reserva.objects.filter(vuelo_id=vuelo_id)
    return render(request, 'gestion/reporte_pasajeros.html', {
        'vuelos': vuelos,
        'reservas': reservas,
        'vuelo_seleccionado': vuelo_id
    })


@login_required(login_url='login')
@admin_required
def exportar_reporte_pdf(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    reservas = vuelo.reservas.all()  # o como tengas tu relación

    template_path = 'reporte_pasajeros.html'  # tu template corregido
    context = {'vuelo': vuelo, 'reservas': reservas}

    # Crear el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_vuelo_{vuelo.codigo_vuelo}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    # Generar PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF <pre>' + html + '</pre>')
    return response

@login_required(login_url='login')
@admin_required
def exportar_reporte_csv(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    reservas = Reserva.objects.filter(vuelo=vuelo)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_pasajeros_vuelo_{vuelo.id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Pasajero', 'Documento', 'Asiento', 'Precio', 'Código Reserva'])
    for reserva in reservas:
        writer.writerow([
            reserva.pasajero.get_full_name(),
            reserva.pasajero.documento,
            reserva.asiento.numero,
            reserva.precio_final,
            reserva.codigo_reserva
        ])
    return response

# -------------------------------
# CRUD DE VUELOS (ADMIN)
# -------------------------------
@login_required(login_url='login')
@admin_required
def vuelo_admin(request):
    vuelos = Vuelo.objects.all().order_by('fecha_salida')
    return render(request, 'gestion/vuelo_admin.html', {'vuelos': vuelos})

@login_required(login_url='login')
@admin_required
def editar_vuelo(request, vuelo_id=None):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id) if vuelo_id else None
    if request.method == 'POST':
        form = VueloForm(request.POST, instance=vuelo)
        if form.is_valid():
            form.save()
            messages.success(request, "Vuelo guardado correctamente.")
            return redirect('vuelo_admin')
    else:
        form = VueloForm(instance=vuelo)
    return render(request, 'gestion/editar_vuelo.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff)  # solo admin o staff
def cancelar_vuelo(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    vuelo.estado = Vuelo.Estado.CANCELADO
    vuelo.save()
    messages.success(request, f"El vuelo {vuelo.codigo_vuelo} ha sido cancelado.")
    return redirect('lista_vuelos')

# -------------------------------
# VISTA GENERAL DE VUELOS (PASAJERO Y ADMIN)
# -------------------------------
@login_required(login_url='login')
def vuelos_disponibles(request):
    vuelos = Vuelo.objects.all().order_by('fecha_salida')

    # --- SOLO ADMIN PUEDE EDITAR, AGREGAR O CANCELAR ---
    if request.method == 'POST' and getattr(request.user, 'rol', None) == Usuario.Rol.ADMIN:

        # --- ACTUALIZAR PRECIO ---
        if 'update_vuelo' in request.POST:
            vuelo_id = request.POST.get('update_vuelo')
            nuevo_precio = request.POST.get('nuevo_precio')
            try:
                vuelo = Vuelo.objects.get(id=vuelo_id)
                vuelo.precio_base = float(nuevo_precio)
                vuelo.save()
                messages.success(request, f"💰 Precio del vuelo {vuelo.codigo_vuelo} actualizado correctamente.")
            except (Vuelo.DoesNotExist, ValueError):
                messages.error(request, "❌ Error al actualizar precio.")
            return redirect('vuelos_disponibles')

        # --- CANCELAR VUELO ---
        if 'cancel_vuelo' in request.POST:
            vuelo_id = request.POST.get('cancel_vuelo')
            try:
                vuelo = Vuelo.objects.get(id=vuelo_id)
                vuelo.estado = Vuelo.Estado.CANCELADO  # ✅ asignamos el estado correcto
                vuelo.save()
                messages.success(request, f"✈️ Vuelo {vuelo.codigo_vuelo} cancelado correctamente.")
            except Vuelo.DoesNotExist:
                messages.error(request, "❌ El vuelo no existe.")
            return redirect('vuelos_disponibles')

        # --- AGREGAR NUEVO VUELO ---
        if all(field in request.POST for field in ['codigo_vuelo', 'origen', 'destino', 'fecha_salida', 'fecha_llegada', 'precio_base']):
            form = VueloForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "✈️ Vuelo agregado correctamente.")
            else:
                messages.error(request, "⚠️ Corrige los errores en el formulario de agregar vuelo.")
            return redirect('vuelos_disponibles')

    # Renderizar página
    return render(request, 'gestion/vuelos.html', {
        'vuelos': vuelos,
        'form': VueloForm(),  # Para que el admin pueda agregar desde la misma vista
    })


# -------------------------------
# PANEL DE ADMIN DE VUELOS
# -------------------------------
@login_required(login_url='login')
def vuelo_admin(request):
    vuelos = Vuelo.objects.all()
    return render(request, 'gestion/vuelo_admin.html', {'vuelos': vuelos})


@login_required(login_url='login')
def editar_vuelo(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    if request.method == "POST":
        form = VueloForm(request.POST, instance=vuelo)
        if form.is_valid():
            form.save()
            messages.success(request, "Vuelo actualizado correctamente")
            return redirect('vuelo_admin')
    else:
        form = VueloForm(instance=vuelo)
    return render(request, 'gestion/editar_vuelo.html', {'form': form, 'vuelo': vuelo})


@login_required(login_url='login')
def agregar_vuelo(request):
    if request.method == "POST":
        form = VueloForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vuelo agregado correctamente")
            return redirect('vuelo_admin')
    else:
        form = VueloForm()
    return render(request, 'gestion/agregar_vuelo.html', {'form': form})


@login_required(login_url='login')
def cancelar_vuelo(request, vuelo_id):
    vuelo = get_object_or_404(Vuelo, id=vuelo_id)
    vuelo.estado = Vuelo.Estado.CANCELADO  # ✅ usamos el campo correcto
    vuelo.save()
    messages.success(request, "Vuelo cancelado correctamente")
    return redirect('vuelo_admin')