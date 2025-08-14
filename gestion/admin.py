from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils import timezone
from .models import Avion, Vuelo, Asiento, Usuario, Reserva, Boleto

# 🔒 Formulario de validación para Reservas
class ReservaAdminForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        vuelo = cleaned_data.get('vuelo')
        pasajero = cleaned_data.get('pasajero')
        asiento = cleaned_data.get('asiento')

        # Validación: un pasajero no puede reservar el mismo vuelo dos veces
        if vuelo and pasajero:
            if Reserva.objects.filter(vuelo=vuelo, pasajero=pasajero).exclude(pk=self.instance.pk).exists():
                raise ValidationError("Este pasajero ya tiene una reserva para este vuelo.")

        # Validación: un asiento no puede estar reservado dos veces
        if asiento and Reserva.objects.filter(asiento=asiento).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este asiento ya fue reservado.")

        # Validación: no reservar vuelos pasados
        if vuelo and vuelo.fecha_salida < timezone.now():
            raise ValidationError("No se puede reservar un vuelo cuya fecha ya pasó.")

        return cleaned_data

# 🔧 Admin personalizado para Reservas
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    form = ReservaAdminForm
    list_display = ('vuelo', 'pasajero', 'asiento', 'precio_final', 'estado')
    search_fields = ('pasajero__first_name', 'pasajero__last_name', 'vuelo__origen', 'vuelo__destino')
    list_filter = ('estado', 'vuelo__estado')

# ✅ Admin para Boleto con acción de anulación
@admin.register(Boleto)
class BoletoAdmin(admin.ModelAdmin):
    list_display = ('codigo_barra', 'reserva', 'estado', 'fecha_emision')
    list_filter = ('estado',)
    actions = ['anular_boletos']

    @admin.action(description="❌ Anular boletos seleccionados")
    def anular_boletos(self, request, queryset):
        actualizados = 0
        for boleto in queryset:
            boleto.anular()
            actualizados += 1
        self.message_user(request, f"{actualizados} boleto(s) anulados correctamente.")

# Admins para modelos básicos
@admin.register(Avion)
class AvionAdmin(admin.ModelAdmin):
    list_display = ('modelo', 'capacidad', 'filas', 'columnas', 'matricula')
    search_fields = ('modelo', 'matricula')

@admin.register(Vuelo)
class VueloAdmin(admin.ModelAdmin):
    list_display = ('codigo_vuelo', 'origen', 'destino', 'fecha_salida', 'estado', 'precio_base')
    list_filter = ('estado',)
    search_fields = ('codigo_vuelo', 'origen', 'destino')

@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'avion', 'vuelo', 'fila', 'columna', 'tipo', 'estado')
    list_filter = ('estado', 'tipo')
    search_fields = ('numero',)

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'get_full_name', 'documento', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'documento')
