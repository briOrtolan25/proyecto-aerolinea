from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
import random
import string
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


# --------------------
# PASAJERO
# --------------------
class Pasajero(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    tipo_documento = models.CharField(max_length=10)
    documento = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField()

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


# --------------------
# USUARIO
# --------------------
class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = 'AD', _('Administrador')
        EMPLEADO = 'EM', _('Empleado')
        PASAJERO = 'PA', _('Pasajero')
    
    documento = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[0-9]+$', 'Solo se permiten números')]
    )
    telefono = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?[0-9]+$', 'Formato de teléfono inválido')]
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    rol = models.CharField(max_length=2, choices=Rol.choices, default=Rol.PASAJERO)

    groups = models.ManyToManyField(
        Group,
        related_name='gestion_usuarios',
        blank=True,
        verbose_name=_('groups'),
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='gestion_usuarios_permissions',
        blank=True,
        verbose_name=_('user permissions'),
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.documento})"


# --------------------
# AVIÓN
# --------------------
class Avion(models.Model):
    modelo = models.CharField(max_length=100)
    capacidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    filas = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    columnas = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    matricula = models.CharField(max_length=10, unique=True)
    fecha_fabricacion = models.DateField(default=timezone.now)
    ultimo_mantenimiento = models.DateField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Aviones"
        ordering = ['modelo']

    def __str__(self):
        return f"{self.modelo} ({self.matricula})"


# --------------------
# VUELO
# --------------------
class Vuelo(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADO = 'programado', _('Programado')
        DEMORADO = 'demorado', _('Demorado')
        CANCELADO = 'cancelado', _('Cancelado')
        COMPLETADO = 'completado', _('Completado')
        EN_CURSO = 'en_curso', _('En Curso')

    avion = models.ForeignKey(Avion, on_delete=models.PROTECT, related_name='vuelos')
    codigo_vuelo = models.CharField(max_length=10, unique=True)
    origen = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    fecha_salida = models.DateTimeField()
    fecha_llegada = models.DateTimeField()
    duracion = models.DurationField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PROGRAMADO)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tripulacion = models.ManyToManyField(Usuario, limit_choices_to={'rol__in': ['AD', 'EM']}, blank=True)

    class Meta:
        ordering = ['fecha_salida']
        indexes = [
            models.Index(fields=['origen', 'destino']),
            models.Index(fields=['fecha_salida']),
        ]

    def __str__(self):
        return f"{self.codigo_vuelo}: {self.origen} → {self.destino}"

    def clean(self):
        if self.fecha_llegada <= self.fecha_salida:
            raise ValidationError("La fecha de llegada debe ser posterior a la de salida")


# --------------------
# ASIENTO
# --------------------
class Asiento(models.Model):
    class Tipo(models.TextChoices):
        ECONOMY = 'economy', _('Economy')
        PREMIUM = 'premium', _('Premium')
        BUSINESS = 'business', _('Business')
        FIRST = 'first', _('First Class')

    class Estado(models.TextChoices):
        DISPONIBLE = 'disponible', _('Disponible')
        RESERVADO = 'reservado', _('Reservado')
        OCUPADO = 'ocupado', _('Ocupado')
        MANTENIMIENTO = 'mantenimiento', _('En Mantenimiento')

    avion = models.ForeignKey(Avion, on_delete=models.CASCADE, related_name='asientos')
    vuelo = models.ForeignKey(Vuelo, on_delete=models.CASCADE, related_name='asientos')
    numero = models.CharField(max_length=10)
    fila = models.PositiveIntegerField()
    columna = models.CharField(max_length=5)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.ECONOMY)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)
    clase = models.CharField(max_length=20, choices=[("Turista", "Turista"), ("Ejecutiva", "Ejecutiva")], default="Turista")
    precio_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['avion', 'numero']
        ordering = ['fila', 'columna']

    def __str__(self):
        return f"Asiento {self.numero} ({self.get_tipo_display()})"


# --------------------
# RESERVA
# --------------------
class Reserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', _('Pendiente')
        CONFIRMADA = 'confirmada', _('Confirmada')
        CANCELADA = 'cancelada', _('Cancelada')
        CHECKIN = 'checkin', _('Check-In Realizado')

    vuelo = models.ForeignKey(Vuelo, on_delete=models.PROTECT, related_name='reservas')
    pasajero = models.ForeignKey(Usuario, on_delete=models.PROTECT, limit_choices_to={'rol': 'PA'}, related_name='reservas')
    asiento = models.OneToOneField(Asiento, on_delete=models.PROTECT, related_name='reserva')
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    codigo_reserva = models.CharField(max_length=12, unique=True, editable=False)
    precio_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    equipaje_mano = models.BooleanField(default=True)
    equipaje_bodega = models.PositiveIntegerField(default=0)
    requerimientos_especiales = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['pasajero', 'vuelo'], name='reserva_unica_por_pasajero_y_vuelo'),
            models.CheckConstraint(check=models.Q(precio_final__gte=0), name='precio_final_positivo')
        ]
        ordering = ['-fecha_reserva']

    def __str__(self):
        return f"Reserva {self.codigo_reserva} - {self.pasajero}"

    def save(self, *args, **kwargs):
        if not self.codigo_reserva:
            self.codigo_reserva = self.generar_codigo_unico()
        if not self.pk:
            self.precio_final = self.calcular_precio_final()
        super().save(*args, **kwargs)

    def generar_codigo_unico(self):
        for _ in range(10):
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Reserva.objects.filter(codigo_reserva=codigo).exists():
                return codigo
        raise ValueError("No se pudo generar un código único de reserva")

    def calcular_precio_final(self):
        return self.vuelo.precio_base + self.asiento.precio_extra

    def cancelar(self):
        self.estado = self.Estado.CANCELADA
        self.asiento.estado = Asiento.Estado.DISPONIBLE
        self.asiento.save()
        self.save()


# --------------------
# BOLETO
# --------------------
class Boleto(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = 'activo', _('Activo')
        USADO = 'usado', _('Usado')
        ANULADO = 'anulado', _('Anulado')

    reserva = models.OneToOneField(Reserva, on_delete=models.PROTECT, related_name='boleto')
    codigo_barra = models.CharField(max_length=30, unique=True, editable=False)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_checkin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    puerta_embarque = models.CharField(max_length=5, blank=True)

    class Meta:
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Boleto {self.codigo_barra} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        if not self.codigo_barra:
            self.codigo_barra = self.generar_codigo_barra()
        super().save(*args, **kwargs)

    def generar_codigo_barra(self):
        return f"B{self.reserva.codigo_reserva}{random.randint(1000, 9999)}"

    def marcar_como_usado(self):
        self.estado = self.Estado.USADO
        self.fecha_checkin = timezone.now()
        self.save()

    def anular(self):
        self.estado = self.Estado.ANULADO
        self.save()
        self.reserva.cancelar()
