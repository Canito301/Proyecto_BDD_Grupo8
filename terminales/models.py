from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    ROLES = [
        ('administrativo', 'Administrativo'),
        ('superadmin', 'Super Administrador'),
    ]
    rol = models.CharField(max_length=20, choices=ROLES, default='administrativo')
    rut = models.CharField(max_length=15, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"


class Terminal(models.Model):
    id_terminal = models.AutoField(primary_key=True)
    capacidad_buses = models.CharField(max_length=150)   #PARAMETROS QUE ESTEN EN LA BASE DE DATOS
    direccion = models.CharField(max_length=200)
    nombre = models.CharField(max_length=100)

    def cantidad_buses(self):
        return self.capacidad_buses                           #IMPORTANTE CAMBIAR LOS SELF

    def __str__(self):    
        return f"{self.nombre} — {self.direccion}"

    class Meta:
        db_table = 'terminal'                              #NOMBRE DATABASE TABLE
        verbose_name = "Terminal"
        verbose_name_plural = "Terminales"
        ordering = ['nombre']


class Bus(models.Model):
    # Definimos explícitamente la llave primaria real de la base de datos
    id_bus = models.AutoField(primary_key=True) 
    patente = models.CharField(max_length=8)  # max_length=8 en SQL 
    accesibilidad_universal = models.BooleanField()
    kilometraje = models.IntegerField(null=True, blank=True)
    
    # Llave foránea apuntando al ID real de la tabla terminal 
    id_terminal = models.ForeignKey(
        Terminal, 
        on_delete=models.SET_NULL, 
        db_column='id_terminal',  # Nombre exacto en PostgreSQL
        null=True, 
        blank=True,
        related_name='buses'
    )

    def __str__(self):
        return f"Bus {self.patente} (ID: {self.id_bus})"

    class Meta:
        # Si te sigue dando error de "relación no existe", cámbialo por: '"empresa_buses"."bus"'
        db_table = 'bus'  
        verbose_name = "Bus"
        verbose_name_plural = "Buses"
        ordering = ['patente']


class Viaje(models.Model):
    id_viaje = models.AutoField(primary_key=True)
    fecha_hora_inicio = models.DateTimeField()
    id_chofer = models.IntegerField()
    id_bus = models.ForeignKey(Bus, on_delete=models.CASCADE, db_column='id_bus')
    id_terminal_inicio = models.ForeignKey(Terminal, on_delete=models.CASCADE, db_column='id_terminal_inicio', related_name='viajes_inicio')
    id_terminal_final = models.ForeignKey(Terminal, on_delete=models.CASCADE, db_column='id_terminal_final', related_name='viajes_final')

    class Meta:
        db_table = 'viaje'
        managed = False


class Asiento(models.Model):
    num_asiento = models.IntegerField(primary_key=True)
    id_bus = models.ForeignKey(Bus, on_delete=models.CASCADE, db_column='id_bus')
    estado = models.BooleanField(default=True)  # True = disponible

    class Meta:
        db_table = 'asiento'
        managed = False
        unique_together = (('num_asiento', 'id_bus'),)

class Chofer(models.Model):
    id_chofer = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=150)
    fecha_inicio_contrato = models.DateField()

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    class Meta:
        db_table = 'chofer'
        managed = False


class Administrativo(models.Model):
    id_admin = models.AutoField(primary_key=True)
    id_terminal = models.ForeignKey(Terminal, on_delete=models.SET_NULL, null=True, db_column='id_terminal')
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=150)
    fecha_inicio_contrato = models.DateField()

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'administrativo'
        managed = False


class Reporte(models.Model):
    id_reporte = models.AutoField(primary_key=True)
    id_admin = models.ForeignKey(Administrativo, on_delete=models.CASCADE, db_column='id_admin')
    tipo = models.CharField(max_length=15, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    class Meta:
        db_table = 'reporte'
        managed = False


class BusReporte(models.Model):
    id_bus = models.ForeignKey(Bus, on_delete=models.CASCADE, db_column='id_bus', primary_key=True)
    id_reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, db_column='id_reporte')

    class Meta:
        db_table = 'bus_reporte'
        managed = False
        unique_together = (('id_bus', 'id_reporte'),)


class ChoferReporte(models.Model):
    id_reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, db_column='id_reporte', primary_key=True)
    id_chofer = models.ForeignKey(Chofer, on_delete=models.CASCADE, db_column='id_chofer')

    class Meta:
        db_table = 'chofer_reporte'
        managed = False
        unique_together = (('id_reporte', 'id_chofer'),)


class Boleto(models.Model):
    id_boleto = models.AutoField(primary_key=True)
    fecha_hora_compra = models.DateTimeField(auto_now_add=True)
    tipo_boleto = models.CharField(max_length=20)
    num_asiento = models.IntegerField()
    ciudad_inicial = models.CharField(max_length=100)
    ciudad_final = models.CharField(max_length=100)
    id_viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, db_column='id_viaje')

    def __str__(self):
        return f"Boleto #{self.id_boleto} — Asiento {self.num_asiento}"

    class Meta:
        db_table = 'boleto'
        managed = False
        ordering = ['-fecha_hora_compra']