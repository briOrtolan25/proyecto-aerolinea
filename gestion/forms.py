from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import Pasajero, Reserva, Vuelo, Asiento, Usuario


class PasajeroForm(forms.ModelForm):
    class Meta:
        model = Pasajero
        fields = ['nombre', 'apellido', 'tipo_documento', 'documento', 'fecha_nacimiento']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'documento': 'Número de documento',
            'tipo_documento': 'Tipo de documento',
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
    vuelo = forms.ModelChoiceField(
        queryset=Vuelo.objects.filter(fecha_salida__gte=timezone.now()),
        empty_label="Seleccione un vuelo",
        widget=forms.Select(attrs={'class': 'form-control', 'required': True, 'onchange': 'this.form.submit();'})
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

        vuelo_id = None
        if 'vuelo' in self.data:
            try:
                vuelo_id = int(self.data.get('vuelo'))
                vuelo = Vuelo.objects.get(pk=vuelo_id)
                # Filtrar asientos disponibles sólo del avión del vuelo seleccionado
                self.fields['asiento'].queryset = Asiento.objects.filter(
                    avion=vuelo.avion,
                    estado=Asiento.Estado.DISPONIBLE
                )
            except (ValueError, TypeError, Vuelo.DoesNotExist):
                self.fields['asiento'].queryset = Asiento.objects.none()
        elif self.instance.pk and self.instance.vuelo:
            vuelo = self.instance.vuelo
            self.fields['asiento'].queryset = Asiento.objects.filter(
                avion=vuelo.avion,
                estado=Asiento.Estado.DISPONIBLE
            ) | Asiento.objects.filter(pk=self.instance.asiento.pk)
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

            # Evitar reservas duplicadas para el mismo pasajero y vuelo
            if Reserva.objects.filter(
                vuelo=vuelo, pasajero=self.usuario
            ).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise forms.ValidationError("⚠️ Ya tienes una reserva para este vuelo.")

        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        reserva.pasajero = self.usuario
        reserva.precio_final = reserva.vuelo.precio_base + reserva.asiento.precio_extra
        reserva.estado = Reserva.Estado.PENDIENTE
        if commit:
            reserva.save()
            # Marcar asiento como reservado
            reserva.asiento.estado = Asiento.Estado.RESERVADO
            reserva.asiento.save()
        return reserva
    vuelo = forms.ModelChoiceField(
        queryset=Vuelo.objects.filter(fecha_salida__gte=timezone.now()),
        empty_label="Seleccione un vuelo",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
            'onchange': 'this.form.submit();'  # Auto submit al cambiar vuelo
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

        vuelo_id = None
        # Intentamos obtener el vuelo seleccionado para filtrar los asientos disponibles
        if 'vuelo' in self.data:
            try:
                vuelo_id = int(self.data.get('vuelo'))
            except (ValueError, TypeError):
                vuelo_id = None

        # Si se encontró un vuelo válido, filtramos los asientos disponibles para ese avión
        if vuelo_id:
            try:
                vuelo = Vuelo.objects.get(pk=vuelo_id)
                self.fields['asiento'].queryset = Asiento.objects.filter(
                    avion=vuelo.avion,
                    estado=Asiento.Estado.DISPONIBLE
                )
            except Vuelo.DoesNotExist:
                self.fields['asiento'].queryset = Asiento.objects.none()
        # En caso de edición, permitir mantener el asiento seleccionado aunque no esté disponible ahora
        elif self.instance.pk and self.instance.vuelo:
            vuelo = self.instance.vuelo
            self.fields['asiento'].queryset = Asiento.objects.filter(
                avion=vuelo.avion,
                estado=Asiento.Estado.DISPONIBLE
            ) | Asiento.objects.filter(pk=self.instance.asiento.pk)
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

            # Evitar reservas duplicadas para el mismo pasajero y vuelo
            if Reserva.objects.filter(vuelo=vuelo, pasajero=self.usuario).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise forms.ValidationError("⚠️ Ya tienes una reserva para este vuelo.")

        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        reserva.pasajero = self.usuario
        reserva.precio_final = reserva.vuelo.precio_base + reserva.asiento.precio_extra
        reserva.estado = Reserva.Estado.PENDIENTE

        if commit:
            reserva.save()
            # Marcar asiento como reservado
            reserva.asiento.estado = Asiento.Estado.RESERVADO
            reserva.asiento.save()

        return reserva

class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    first_name = forms.CharField(required=True, label='Nombre')
    last_name = forms.CharField(required=True, label='Apellido')
    documento = forms.CharField(required=True, label='Documento', validators=[RegexValidator(r'^[0-9]+$', 'Solo se permiten números')])
    telefono = forms.CharField(required=True, validators=[RegexValidator(r'^\+?[0-9]+$', 'Formato de teléfono inválido')])
    fecha_nacimiento = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}), label='Fecha de nacimiento')

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


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Nombre de usuario o email", widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))


class VueloSearchForm(forms.Form):
    origen = forms.CharField(required=False, label='Origen', widget=forms.TextInput(attrs={'placeholder': 'Ciudad origen'}))
    destino = forms.CharField(required=False, label='Destino', widget=forms.TextInput(attrs={'placeholder': 'Ciudad destino'}))
    fecha = forms.DateField(required=False, label='Fecha', widget=forms.DateInput(attrs={'type': 'date'}), input_formats=['%Y-%m-%d', '%d/%m/%Y'])

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError('⚠️ No puedes buscar vuelos en fechas pasadas.')
        return fecha


class AsientoSelectForm(forms.Form):
    asiento_id = forms.IntegerField(required=True, widget=forms.HiddenInput())

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
