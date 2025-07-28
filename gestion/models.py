from django.db import models
from django.contrib.auth.models import User
import random
import string

# ------------------------------
# MODELO: AVIÓN
# ------------------------------
class Avion(models.Model):
    modelo = models.CharField(max_length=100)
    capacidad = models.IntegerField()
    filas = models.IntegerField()
    columnas = models.IntegerField()

    def __str__(self):
        return self.modelo

# ------------------------------
# MODELO: VUELO
# ------------------------------
class Vuelo(models.Model):
    ESTADOS = [
        ('programado', 'Programado'),
        ('cancelado', 'Cancelado'),
        ('finalizado', 'Finalizado')
    ]
    avion = models.ForeignKey(Avion, on_delete=models.CASCADE)
    origen = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    fecha_salida = models.DateTimeField()
    fecha_llegada = models.DateTimeField()
    duracion = models.DurationField()
    estado = models.CharField(max_length=20, choices=ESTADOS)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    usuarios = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return f"{self.origen} → {self.destino} ({self.fecha_salida.date()})"

# ------------------------------
# MODELO: PASAJERO
# ------------------------------
class Pasajero(models.Model):
    TIPO_DOC = [('DNI', 'DNI'), ('Pasaporte', 'Pasaporte')]
    nombre = models.CharField(max_length=100)
    documento = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField()
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOC)

    def __str__(self):
        return f"{self.nombre} ({self.documento})"

# ------------------------------
# MODELO: ASIENTO
# ------------------------------
class Asiento(models.Model):
    TIPOS = [('economy', 'Economy'), ('premium', 'Premium')]
    ESTADO = [('disponible', 'Disponible'), ('reservado', 'Reservado'), ('ocupado', 'Ocupado')]
    avion = models.ForeignKey(Avion, on_delete=models.CASCADE)
    numero = models.CharField(max_length=10)
    fila = models.IntegerField()
    columna = models.CharField(max_length=5)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    estado = models.CharField(max_length=20, choices=ESTADO)

    def __str__(self):
        return f"Asiento {self.numero} ({self.estado})"

# ------------------------------
# MODELO: RESERVA
# ------------------------------
class Reserva(models.Model):
    ESTADO = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada')
    ]
    vuelo = models.ForeignKey(Vuelo, on_delete=models.CASCADE)
    pasajero = models.ForeignKey(Pasajero, on_delete=models.CASCADE)
    asiento = models.OneToOneField(Asiento, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADO, default='pendiente')
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    codigo_reserva = models.CharField(max_length=12, unique=True, blank=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['pasajero', 'vuelo'], name='reserva_unica_por_pasajero_y_vuelo')
        ]

    def __str__(self):
        return f"Reserva {self.codigo_reserva}"

    def generar_codigo(self):
        # Intenta generar un código único hasta 10 veces
        for _ in range(10):
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Reserva.objects.filter(codigo_reserva=codigo).exists():
                return codigo
        raise ValueError("No se pudo generar un código único de reserva.")

    def save(self, *args, **kwargs):
        if not self.codigo_reserva:
            self.codigo_reserva = self.generar_codigo()
        super().save(*args, **kwargs)

# ------------------------------
# MODELO: BOLETO
# ------------------------------

class Boleto(models.Model):
    ESTADO = [
        ('activo', 'Activo'),
        ('usado', 'Usado'),
        ('anulado', 'Anulado')
    ]

    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE)
    codigo_barra = models.CharField(max_length=30)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO, default='activo')

    def __str__(self):
        return f"Boleto {self.codigo_barra}"

    def anular(self):
        self.estado = 'anulado'
        self.save()
