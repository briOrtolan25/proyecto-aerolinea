from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from .models import Vuelo, Reserva, Pasajero, Asiento, Boleto
from .forms import (
    RegistroUsuarioForm, 
    LoginForm,
    PasajeroForm,
    ReservaForm,
    VueloSearchForm,
    AsientoSelectForm
)

## Vistas de Autenticación ##
def registro_view(request):
    if request.user.is_authenticated:
        return redirect('inicio')
    
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Crear perfil de pasajero asociado
            Pasajero.objects.create(
                usuario=user,
                nombre=f"{user.first_name} {user.last_name}",
                documento=form.cleaned_data['documento'],
                email=user.email,
                telefono=form.cleaned_data['telefono'],
                fecha_nacimiento=form.cleaned_data['fecha_nacimiento']
            )
            
            login(request, user)
            messages.success(request, '¡Registro exitoso! Bienvenido/a a nuestra aerolínea.')
            return redirect('inicio')
    else:
        form = RegistroUsuarioForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('inicio')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido/a de vuelta, {user.first_name}!')
                return redirect('inicio')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('login')

## Vistas Públicas ##
class InicioView(TemplateView):
    template_name = 'gestion/inicio.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vuelos_destacados'] = Vuelo.objects.filter(
            fecha_salida__gte=timezone.now()
        ).order_by('fecha_salida')[:3]
        return context

## Vistas de Vuelos ##
class ListaVuelosView(ListView):
    model = Vuelo
    template_name = 'gestion/lista_vuelos.html'
    context_object_name = 'vuelos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            fecha_salida__gte=timezone.now()
        )
        
        form = VueloSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data['origen']:
                queryset = queryset.filter(origen__icontains=form.cleaned_data['origen'])
            if form.cleaned_data['destino']:
                queryset = queryset.filter(destino__icontains=form.cleaned_data['destino'])
            if form.cleaned_data['fecha']:
                queryset = queryset.filter(fecha_salida__date=form.cleaned_data['fecha'])
        
        return queryset.order_by('fecha_salida')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = VueloSearchForm(self.request.GET)
        return context

class DetalleVueloView(DetailView):
    model = Vuelo
    template_name = 'gestion/detalle_vuelo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['asientos_disponibles'] = self.object.avion.asientos.filter(
            estado='disponible'
        )
        context['form_seleccion_asiento'] = AsientoSelectForm(vuelo=self.object)
        return context

## Vistas de Reservas (requieren autenticación) ##
class CrearReservaView(LoginRequiredMixin, CreateView):
    model = Reserva
    form_class = ReservaForm
    template_name = 'gestion/crear_reserva.html'
    
    def get_initial(self):
        initial = super().get_initial()
        vuelo = get_object_or_404(Vuelo, pk=self.kwargs['vuelo_id'])
        asiento = get_object_or_404(Asiento, pk=self.request.POST.get('asiento_id'))
        
        initial.update({
            'vuelo': vuelo,
            'pasajero': self.request.user.pasajero,
            'asiento': asiento,
            'precio': vuelo.precio_base + asiento.precio_extra
        })
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vuelo'] = get_object_or_404(Vuelo, pk=self.kwargs['vuelo_id'])
        return context
    
    def form_valid(self, form):
        vuelo = get_object_or_404(Vuelo, pk=self.kwargs['vuelo_id'])
        form.instance.vuelo = vuelo
        form.instance.pasajero = self.request.user.pasajero
        
        # Actualizar estado del asiento
        asiento = form.instance.asiento
        asiento.estado = 'reservado'
        asiento.save()
        
        # Crear boleto asociado
        Boleto.objects.create(
            reserva=form.instance,
            codigo_barra=form.instance.generar_codigo_barra()
        )
        
        messages.success(self.request, '¡Reserva creada exitosamente!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('detalle_reserva', kwargs={'pk': self.object.pk})

class ListaReservasView(LoginRequiredMixin, ListView):
    model = Reserva
    template_name = 'gestion/lista_reservas.html'
    context_object_name = 'reservas'
    
    def get_queryset(self):
        return Reserva.objects.filter(
            pasajero=self.request.user.pasajero
        ).order_by('-fecha_reserva')

class DetalleReservaView(LoginRequiredMixin, DetailView):
    model = Reserva
    template_name = 'gestion/detalle_reserva.html'
    
    def get_queryset(self):
        return super().get_queryset().filter(pasajero=self.request.user.pasajero)

## Vistas de Perfil ##
@login_required
def perfil_view(request):
    pasajero = get_object_or_404(Pasajero, usuario=request.user)
    
    if request.method == 'POST':
        form = PasajeroForm(request.POST, instance=pasajero)
        user_form = RegistroUsuarioForm(request.POST, instance=request.user)
        
        if form.is_valid() and user_form.is_valid():
            form.save()
            user_form.save()
            messages.success(request, 'Perfil actualizado correctamente')
            return redirect('perfil')
    else:
        form = PasajeroForm(instance=pasajero)
        user_form = RegistroUsuarioForm(instance=request.user)
    
    return render(request, 'gestion/perfil.html', {
        'form': form,
        'user_form': user_form
    })

## Vistas para Personal (requieren ser staff) ##
class GestionReservasView(LoginRequiredMixin, ListView):
    template_name = 'gestion/gestion_reservas.html'
    context_object_name = 'reservas'
    
    def get_queryset(self):
        return Reserva.objects.filter(
            vuelo__fecha_salida__gte=timezone.now()
        ).order_by('vuelo__fecha_salida')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'No tienes permiso para acceder a esta página')
            return redirect('inicio')
        return super().dispatch(request, *args, **kwargs)