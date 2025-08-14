from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import Reserva, Vuelo, Asiento, Usuario

# ---------------------------
# FORMULARIO DE RESERVA DE ASIENTOS
# ---------------------------
class ReservaForm(forms.ModelForm):
    vuelo = forms.ModelChoiceField(
        queryset=Vuelo.objects.filter(fecha_salida__gte=timezone.now()),
        empty_label="Seleccione un vuelo",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
            'onchange': 'this.form.submit();'  # Para recargar asientos al cambiar vuelo
        })
    )
    asiento = forms.ModelChoiceField(
        queryset=Asiento.objects.none(),
        empty_label="Seleccione un asiento",
        widget=forms.Select(attrs={'class': 'form-control', 'required': True})
    )
    equipaje_bodega = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    equipaje_mano = forms.BooleanField(required=False, initial=True)
    requerimientos_especiales = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )

    class Meta:
        model = Reserva
        fields = ['vuelo', 'asiento', 'equipaje_mano', 'equipaje_bodega', 'requerimientos_especiales']

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

        # Obtener el vuelo desde POST, initial o reserva existente
        vuelo_id = (
            self.data.get('vuelo') or
            (self.initial.get('vuelo') if self.initial.get('vuelo') else None) or
            (self.instance.vuelo.pk if self.instance.pk and self.instance.vuelo else None)
        )

        if vuelo_id:
            try:
                vuelo = Vuelo.objects.get(pk=int(vuelo_id))
                # Solo los asientos disponibles del avión del vuelo
                queryset_asientos = Asiento.objects.filter(
                    avion=vuelo.avion,
                    estado=Asiento.Estado.DISPONIBLE
                )
                # Si editamos una reserva existente, agregamos su asiento
                if self.instance.pk and self.instance.asiento:
                    queryset_asientos |= Asiento.objects.filter(pk=self.instance.asiento.pk)
                self.fields['asiento'].queryset = queryset_asientos
            except (ValueError, TypeError, Vuelo.DoesNotExist):
                self.fields['asiento'].queryset = Asiento.objects.none()
        else:
            self.fields['asiento'].queryset = Asiento.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        vuelo = cleaned_data.get('vuelo')
        asiento = cleaned_data.get('asiento')

        if vuelo and asiento:
            if asiento.avion != vuelo.avion:
                raise forms.ValidationError("⚠️ Este asiento no pertenece al avión del vuelo seleccionado.")
            if asiento.estado != Asiento.Estado.DISPONIBLE:
                raise forms.ValidationError("⚠️ Este asiento no está disponible.")
            if Reserva.objects.filter(
                vuelo=vuelo,
                pasajero=self.usuario
            ).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise forms.ValidationError("⚠️ Ya tienes una reserva para este vuelo.")

        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        reserva.pasajero = self.usuario
        reserva.precio_final = reserva.vuelo.precio_base + (reserva.asiento.precio_extra if reserva.asiento else 0)
        reserva.estado = Reserva.Estado.PENDIENTE

        if commit:
            reserva.save()
            # Marcar asiento como reservado
            if reserva.asiento:
                reserva.asiento.estado = Asiento.Estado.RESERVADO
                reserva.asiento.save()
        return reserva

# ---------------------------
# REGISTRO DE USUARIO
# ---------------------------
class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, label='Nombre')
    last_name = forms.CharField(required=True, label='Apellido')
    documento = forms.CharField(required=True, validators=[RegexValidator(r'^[0-9]+$', 'Solo números')])
    telefono = forms.CharField(required=True, validators=[RegexValidator(r'^\+?[0-9]+$', 'Formato inválido')])
    fecha_nacimiento = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'documento', 'telefono', 'fecha_nacimiento', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = Usuario.Rol.PASAJERO
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('⚠️ Este email ya está registrado.')
        return email

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha and fecha > timezone.now().date():
            raise forms.ValidationError('⚠️ La fecha de nacimiento no puede ser futura.')
        return fecha

# ---------------------------
# LOGIN
# ---------------------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario o email", widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

# ---------------------------
# BÚSQUEDA DE VUELOS
# ---------------------------
class VueloSearchForm(forms.Form):
    origen = forms.CharField(required=False, label='Origen', widget=forms.TextInput(attrs={'placeholder': 'Ciudad origen'}))
    destino = forms.CharField(required=False, label='Destino', widget=forms.TextInput(attrs={'placeholder': 'Ciudad destino'}))
    fecha = forms.DateField(required=False, label='Fecha', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError('⚠️ No puedes buscar vuelos en fechas pasadas.')
        return fecha

# ---------------------------
# SELECCIÓN DE ASIENTO
# ---------------------------
class AsientoSelectForm(forms.Form):
    asiento_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, vuelo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vuelo = vuelo

    def clean_asiento_id(self):
        asiento_id = self.cleaned_data.get('asiento_id')
        try:
            asiento = Asiento.objects.get(pk=asiento_id)
            if self.vuelo and asiento.avion != self.vuelo.avion:
                raise forms.ValidationError('⚠️ Este asiento no pertenece al avión del vuelo seleccionado.')
            if asiento.estado != Asiento.Estado.DISPONIBLE:
                raise forms.ValidationError('⚠️ Este asiento no está disponible.')
            return asiento
        except Asiento.DoesNotExist:
            raise forms.ValidationError('⚠️ Asiento no válido.')

# ---------------------------
# FORMULARIO DE VUELOS (ADMIN)
# ---------------------------
class VueloForm(forms.ModelForm):
    class Meta:
        model = Vuelo
        fields = [
            'avion', 'codigo_vuelo', 'origen', 'destino', 'fecha_salida',
            'fecha_llegada', 'duracion', 'precio_base', 'tripulacion'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.rol == 'AD':  # Si es administrador
            self.fields['estado'] = forms.ChoiceField(choices=Vuelo.Estado.choices)
