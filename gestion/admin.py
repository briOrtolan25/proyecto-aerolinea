from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils import timezone
from .models import Avion, Vuelo, Asiento, Pasajero, Reserva, Boleto

# 🔒 Validaciones en el admin para RESERVAS
class ReservaAdminForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        vuelo = cleaned_data.get('vuelo')
        pasajero = cleaned_data.get('pasajero')
        asiento = cleaned_data.get('asiento')

        if vuelo and pasajero:
            if Reserva.objects.filter(vuelo=vuelo, pasajero=pasajero).exclude(pk=self.instance.pk).exists():
                raise ValidationError("Este pasajero ya tiene una reserva para este vuelo.")

        if asiento and Reserva.objects.filter(asiento=asiento).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este asiento ya fue reservado.")

        if vuelo and vuelo.fecha_salida < timezone.now():
            raise ValidationError("No se puede reservar un vuelo cuya fecha ya pasó.")

        return cleaned_data

# 🔧 Admin personalizado para Reserva
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    form = ReservaAdminForm
    list_display = ('codigo_reserva', 'pasajero', 'vuelo', 'asiento', 'precio', 'estado')
    list_filter = ('estado',)
    search_fields = ('codigo_reserva', 'pasajero__nombre')

# ✅ Admin para Boleto con acción para anular
@admin.register(Boleto)
class BoletoAdmin(admin.ModelAdmin):
    list_display = ('codigo_barra', 'reserva', 'estado', 'fecha_emision')
    list_filter = ('estado',)
    actions = ['anular_boleto']

    @admin.action(description="❌ Anular boletos seleccionados")
    def anular_boleto(self, request, queryset):
        actualizados = 0
        for boleto in queryset:
            boleto.anular()
            actualizados += 1
        self.message_user(request, f"{actualizados} boleto(s) anulados correctamente.")

# Admins para los demás modelos
@admin.register(Avion)
class AvionAdmin(admin.ModelAdmin):
    list_display = ('modelo', 'capacidad', 'filas', 'columnas')

@admin.register(Vuelo)
class VueloAdmin(admin.ModelAdmin):
    list_display = ('origen', 'destino', 'fecha_salida', 'estado', 'precio_base')
    list_filter = ('estado',)

@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'documento', 'email')
    search_fields = ('nombre', 'documento')

@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'avion', 'fila', 'columna', 'tipo', 'estado')
    list_filter = ('estado', 'tipo')
