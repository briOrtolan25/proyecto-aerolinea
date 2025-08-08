from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator
from .models import Pasajero, Reserva, Vuelo, Asiento

class PasajeroForm(forms.ModelForm):
    class Meta:
        model = Pasajero
        # Quitar email y telefono que no existen en el modelo Pasajero
        fields = ['nombre', 'documento', 'fecha_nacimiento', 'tipo_documento']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'nombre': 'Nombre completo',
            'documento': 'Número de documento',
            'tipo_documento': 'Tipo de documento'
        }

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        if Pasajero.objects.filter(documento=documento).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('⚠️ Este documento ya está registrado en el sistema.')
        return documento

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
        if fecha_nacimiento and fecha_nacimiento > timezone.now().date():
            raise forms.ValidationError('⚠️ La fecha de nacimiento no puede ser futura.')
        return fecha_nacimiento
class ReservaForm(forms.ModelForm):
    # Campos extras que no están en el modelo Reserva
    equipaje_bodega = forms.IntegerField(required=False, min_value=0)
    equipaje_mano = forms.IntegerField(required=False, min_value=0)
    precio_final = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    requerimientos_especiales = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3})
    )

    class Meta:
        model = Reserva
        fields = ['vuelo', 'pasajero', 'asiento']
        widgets = {
            'vuelo': forms.HiddenInput(),
            'pasajero': forms.HiddenInput(),
            'asiento': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        vuelo = cleaned_data.get('vuelo')
        pasajero = cleaned_data.get('pasajero')
        asiento = cleaned_data.get('asiento')
        precio = cleaned_data.get('precio_final')

        if vuelo and vuelo.fecha_salida < timezone.now():
            raise forms.ValidationError({
                'vuelo': '⚠️ No se puede reservar un vuelo cuya fecha ya pasó.'
            })

        if vuelo and pasajero:
            if Reserva.objects.filter(vuelo=vuelo, pasajero=pasajero).exclude(
                pk=self.instance.pk if self.instance else None
            ).exists():
                raise forms.ValidationError({
                    '__all__': '⚠️ Este pasajero ya tiene una reserva para este vuelo.'
                })

        if asiento:
            if asiento.avion != vuelo.avion:
                raise forms.ValidationError({
                    'asiento': '⚠️ Este asiento no pertenece al avión asignado para este vuelo.'
                })
            if asiento.estado != 'disponible':
                raise forms.ValidationError({
                    'asiento': '⚠️ Este asiento no está disponible para reserva.'
                })

        if precio and precio < (vuelo.precio_base if vuelo else 0):
            raise forms.ValidationError({
                'precio_final': f'⚠️ El precio no puede ser menor al base (${vuelo.precio_base if vuelo else 0}).'
            })

        return cleaned_data

    class Meta:
        model = Reserva
        fields = ['vuelo', 'asiento', 'pasajero']
    class Meta:
        model = Reserva
        # Usar los campos reales del modelo Reserva
        # Si en tu modelo se llama "precio_final" en lugar de "precio", cambiar acá
        fields = ['vuelo', 'pasajero', 'asiento', 'precio_final', 'equipaje_mano', 'equipaje_bodega', 'requerimientos_especiales']
        widgets = {
            'vuelo': forms.HiddenInput(),
            'pasajero': forms.HiddenInput(),
            'asiento': forms.HiddenInput(),
            'requerimientos_especiales': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipaje_bodega'].validators.append(MinValueValidator(0))

    def clean(self):
        cleaned_data = super().clean()
        vuelo = cleaned_data.get('vuelo')
        pasajero = cleaned_data.get('pasajero')
        asiento = cleaned_data.get('asiento')
        precio = cleaned_data.get('precio_final')  # acorde al campo corregido

        if vuelo and vuelo.fecha_salida < timezone.now():
            raise forms.ValidationError({
                'vuelo': '⚠️ No se puede reservar un vuelo cuya fecha ya pasó.'
            })

        if vuelo and pasajero:
            if Reserva.objects.filter(vuelo=vuelo, pasajero=pasajero).exclude(
                pk=self.instance.pk if self.instance else None
            ).exists():
                raise forms.ValidationError({
                    '__all__': '⚠️ Este pasajero ya tiene una reserva para este vuelo.'
                })

        if asiento:
            if asiento.avion != vuelo.avion:
                raise forms.ValidationError({
                    'asiento': '⚠️ Este asiento no pertenece al avión asignado para este vuelo.'
                })
            if asiento.estado != 'disponible':
                raise forms.ValidationError({
                    'asiento': '⚠️ Este asiento no está disponible para reserva.'
                })

        if precio and precio < (vuelo.precio_base if vuelo else 0):
            raise forms.ValidationError({
                'precio_final': f'⚠️ El precio no puede ser menor al base (${vuelo.precio_base if vuelo else 0}).'
            })

        return cleaned_data

class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    first_name = forms.CharField(
        required=True,
        label='Nombre'
    )
    last_name = forms.CharField(
        required=True,
        label='Apellido'
    )
    documento = forms.CharField(
        required=True,
        label='Documento',
        validators=[RegexValidator(r'^[0-9]+$', 'Solo se permiten números')]
    )
    telefono = forms.CharField(
        required=True,
        validators=[RegexValidator(r'^\+?[0-9]+$', 'Formato de teléfono inválido')]
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha de nacimiento'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 
                 'documento', 'telefono', 'fecha_nacimiento',
                 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('⚠️ Este email ya está registrado.')
        return email

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha and fecha > timezone.now().date():
            raise forms.ValidationError('⚠️ La fecha de nacimiento no puede ser futura.')
        return fecha

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Nombre de usuario o email",
        widget=forms.TextInput(attrs={'autofocus': True})
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'})
    )

class VueloSearchForm(forms.Form):
    origen = forms.CharField(
        required=False,
        label='Origen',
        widget=forms.TextInput(attrs={'placeholder': 'Ciudad origen'})
    )
    destino = forms.CharField(
        required=False,
        label='Destino',
        widget=forms.TextInput(attrs={'placeholder': 'Ciudad destino'})
    )
    fecha = forms.DateField(
        required=False,
        label='Fecha',
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError('⚠️ No puedes buscar vuelos en fechas pasadas.')
        return fecha

class AsientoSelectForm(forms.Form):
    asiento_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, vuelo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vuelo = vuelo

    def clean_asiento_id(self):
        asiento_id = self.cleaned_data.get('asiento_id')
        try:
            asiento = Asiento.objects.get(pk=asiento_id)
            if asiento.avion != self.vuelo.avion:
                raise forms.ValidationError('⚠️ Este asiento no pertenece al avión del vuelo seleccionado.')
            if asiento.estado != 'disponible':
                raise forms.ValidationError('⚠️ Este asiento no está disponible.')
            return asiento
        except Asiento.DoesNotExist:
            raise forms.ValidationError('⚠️ Asiento no válido.')
