from django import forms
from .models import Pasajero, Reserva
from django.utils import timezone
class PasajeroForm(forms.ModelForm):
    class Meta:
        model = Pasajero
        fields = '__all__'

class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['vuelo', 'pasajero', 'asiento', 'precio']

    def clean(self):
        cleaned_data = super().clean()
        vuelo = cleaned_data.get('vuelo')
        pasajero = cleaned_data.get('pasajero')
        asiento = cleaned_data.get('asiento')

        # Verificar que el vuelo no sea anterior a hoy
        if vuelo and vuelo.fecha_salida < timezone.now():
            raise forms.ValidationError({
                'vuelo': '⚠️ No se puede reservar un vuelo cuya fecha ya pasó.'
            })

        # Verificar reserva duplicada por pasajero
        if vuelo and pasajero:
            if Reserva.objects.filter(vuelo=vuelo, pasajero=pasajero).exists():
                raise forms.ValidationError({
                    '__all__': '⚠️ Este pasajero ya tiene una reserva para este vuelo.'
                })

        # Verificar si el asiento ya está reservado
        if asiento and Reserva.objects.filter(asiento=asiento).exists():
            raise forms.ValidationError({
                'asiento': '⚠️ Este asiento ya fue reservado por otro pasajero.'
            })

        return cleaned_data