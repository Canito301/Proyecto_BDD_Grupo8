from django import forms
from .models import Terminal, Bus, Usuario, Chofer, Administrativo
from .models import Terminal, Bus, Usuario, Chofer, Administrativo, Viaje #AGREGUE ESTO
from .models import Terminal, Bus, Usuario, Chofer, Administrativo, Viaje, Boleto

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={'placeholder': 'Nombre de usuario'})
    )
    password = forms.CharField(
        label="Contrasena",
        widget=forms.PasswordInput(attrs={'placeholder': 'Contrasena'})
    )


class TerminalForm(forms.ModelForm):
    class Meta:
        model = Terminal
        fields = ['capacidad_buses', 'direccion', 'nombre']
        labels = {
            'capacidad_buses': 'Capacidad',
            'direccion': 'Direccion',
            'nombre': 'Nombre',
        }
        widgets = {
            'capacidad_buses': forms.TextInput(attrs={'placeholder': 'Ej: 9'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Terminal Alameda'}),
            'direccion': forms.TextInput(attrs={'placeholder': 'Ej: Av. Libertador 123'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['administrador'].queryset = Usuario.objects.filter(is_active=True)
        self.fields['administrador'].empty_label = "Sin administrador asignado"


class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        # Solo dejamos los campos reales que mapean a la tabla de la BD
        fields = ['patente', 'accesibilidad_universal', 'kilometraje', 'id_terminal']
        
        labels = {
            'patente': 'Patente',
            'accesibilidad_universal': 'Accesibilidad Universal',
            'kilometraje': 'Kilometraje Actual',
            'id_terminal': 'Terminal Actual',
        }
        
        widgets = {
            'patente': forms.TextInput(attrs={'placeholder': 'Ej: ABCD12'}),
            'kilometraje': forms.NumberInput(attrs={'placeholder': 'Ej: 15000'}),
            # Accesibilidad usa un Checkbox automático por ser BooleanField en el modelo
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Cambiamos 'terminal_actual' por 'id_terminal' que es la llave foránea real
        if 'id_terminal' in self.fields:
            # NOTA: Removí el .filter(activo=True) porque tu tabla terminal original en SQL
            # no tiene una columna llamada "activo". Si la agregas después, puedes descomentar el filtro.
            self.fields['id_terminal'].queryset = Terminal.objects.all()
            self.fields['id_terminal'].empty_label = "Sin terminal asignado (en ruta)"


class ReporteForm(forms.Form):
    TIPOS_REPORTE = [
        ('Mecanico', 'Falla Mecánica'),
        ('Incidente', 'Incidente / Accidente'),
        ('Retraso', 'Retraso de Ruta'),
        ('Personal', 'Problema de Personal'),
        ('Otro', 'Otro'),
    ]

    tipo = forms.ChoiceField(
        choices=TIPOS_REPORTE,
        label='Tipo de Reporte'
    )

    descripcion = forms.CharField(
        label='Descripción detallada',
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Describa lo sucedido...',
            'oninvalid': "this.setCustomValidity('Por favor, complete este campo.')",
            'oninput': "this.setCustomValidity('')"
        }),
        required=True
    )

    # Campos Opcionales (Requerimiento 3)
    id_bus = forms.ModelChoiceField(
        queryset=Bus.objects.all(),
        label='Bus Involucrado (Opcional)',
        required=False,
        empty_label="Ninguno"
    )

    id_chofer = forms.ModelChoiceField(
        queryset=Chofer.objects.all(),
        label='Chofer Involucrado (Opcional)',
        required=False,
        empty_label="Ninguno"
    )

class ChoferForm(forms.ModelForm):
    class Meta:
        model = Chofer
        fields = ['rut', 'nombre', 'fecha_inicio_contrato']

        widgets = {
            'fecha_inicio_contrato': forms.DateInput(
                attrs={
                    'type': 'date', # Esto invoca el calendario del navegador
                }
            )
        }


    def clean_rut(self):
        rut = self.cleaned_data.get('rut')

        if not rut:
            return rut

        # Verificamos cómo fue ingresado (Puntos y guion, igual que tu Dart)
        if "-" not in rut:
            raise forms.ValidationError("El RUT debe contener un guion (-).")

        if "." in rut:
            if len(rut) < 11:
                raise forms.ValidationError("El RUT con puntos está incompleto.")
            if rut.count('.') != 2:
                raise forms.ValidationError("Formato inválido. Debe tener dos puntos o ninguno.")
        else:
            if len(rut) < 9:
                raise forms.ValidationError("El RUT está incompleto.")

        # Dejamos el RUT limpio y separamos el cuerpo del DV
        rut_limpio = rut.replace('.', '').replace('-', '').upper()

        if len(rut_limpio) < 2:
            raise forms.ValidationError("El RUT ingresado es inválido.")

        cuerpo = rut_limpio[:-1]
        dv_ingresado = rut_limpio[-1]

        # Evitamos caídas si ingresan letras en el cuerpo
        if not cuerpo.isdigit():
            raise forms.ValidationError("El cuerpo del RUT solo debe contener números.")

        nums = int(cuerpo)
        if nums > 40000000 or nums < 500000:
            raise forms.ValidationError("El RUT está fuera del rango permitido para choferes.")

        # Verificar Módulo 11 matemático
        suma = 0
        multiplicador = 2

        # Recorremos el cuerpo de atrás hacia adelante en Python
        for digito in reversed(cuerpo):
            suma += int(digito) * multiplicador
            multiplicador += 1
            if multiplicador > 7:
                multiplicador = 2

        resto = suma % 11
        resultado = 11 - resto

        # Transformamos el resultado matemático al dígito esperado
        if resultado == 11:
            dv_esperado = "0"
        elif resultado == 10:
            dv_esperado = "K"
        else:
            dv_esperado = str(resultado)

        if dv_ingresado != dv_esperado:
            raise forms.ValidationError("El dígito verificador es incorrecto.")

        if Chofer.objects.filter(rut=rut).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este RUT ya se encuentra registrado en el sistema.")

        # Si supera todas las barreras sin lanzar un ValidationError, el RUT es válido
        return rut

class AdministrativoForm(forms.ModelForm):
    class Meta:
        model = Administrativo
        # Usamos los campos exactos de tu modelo
        fields = ['rut', 'nombre', 'id_terminal', 'fecha_inicio_contrato']

        widgets = {
            # Calendario automático para la fecha
            'fecha_inicio_contrato': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            return rut

        # 1. Verificaciones de formato
        if "-" not in rut:
            raise forms.ValidationError("El RUT debe contener un guion (-).")

        if "." in rut:
            if len(rut) < 11:
                raise forms.ValidationError("El RUT con puntos está incompleto.")
            if rut.count('.') != 2:
                raise forms.ValidationError("Formato inválido. Debe tener dos puntos o ninguno.")
        else:
            if len(rut) < 9:
                raise forms.ValidationError("El RUT está incompleto.")

        # 2. Limpieza del string
        rut_limpio = rut.replace('.', '').replace('-', '').upper()
        if len(rut_limpio) < 2:
            raise forms.ValidationError("El RUT ingresado es inválido.")

        cuerpo = rut_limpio[:-1]
        dv_ingresado = rut_limpio[-1]

        if not cuerpo.isdigit():
            raise forms.ValidationError("El cuerpo del RUT solo debe contener números.")

        # 3. Rango numérico permitido
        nums = int(cuerpo)
        if nums > 40000000 or nums < 500000:
            raise forms.ValidationError("El RUT está fuera del rango permitido.")

        # 4. Verificación matemática Módulo 11
        suma = 0
        multiplicador = 2
        for digito in reversed(cuerpo):
            suma += int(digito) * multiplicador
            multiplicador += 1
            if multiplicador > 7:
                multiplicador = 2

        resto = suma % 11
        resultado = 11 - resto

        if resultado == 11:
            dv_esperado = "0"
        elif resultado == 10:
            dv_esperado = "K"
        else:
            dv_esperado = str(resultado)

        if dv_ingresado != dv_esperado:
            raise forms.ValidationError("El dígito verificador es incorrecto.")

        # 5. Evitamos duplicados en la tabla de ADMINISTRATIVOS
        if Administrativo.objects.filter(rut=rut).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este RUT ya está registrado para otro administrativo.")

        return rut

class ViajeForm(forms.ModelForm):
    # Se mantiene declarado manualmente para mostrar el select con los choferes reales,
    # pero OJO: ya NO va en Meta.fields, porque en el modelo id_chofer es IntegerField
    # y Django intentaria asignar el objeto Chofer completo al instance durante la validacion,
    # rompiendo el full_clean() del modelo.
    id_chofer = forms.ModelChoiceField(
        queryset=Chofer.objects.all(),
        label='Chofer',
        empty_label="Seleccione un chofer"
    )

    class Meta:
        model = Viaje
        # id_chofer NO va aqui
        fields = ['fecha_hora_inicio', 'id_bus', 'id_terminal_inicio', 'id_terminal_final']
        labels = {
            'fecha_hora_inicio': 'Fecha y Hora',
            'id_bus': 'Bus',
            'id_terminal_inicio': 'Terminal de Origen',
            'id_terminal_final': 'Terminal de Destino',
        }
        widgets = {
            'fecha_hora_inicio': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_bus'].queryset = Bus.objects.all().order_by('patente')
        self.fields['id_bus'].empty_label = "Seleccione un bus"
        self.fields['id_terminal_inicio'].queryset = Terminal.objects.all().order_by('nombre')
        self.fields['id_terminal_inicio'].empty_label = "Seleccione terminal de origen"
        self.fields['id_terminal_final'].queryset = Terminal.objects.all().order_by('nombre')
        self.fields['id_terminal_final'].empty_label = "Seleccione terminal de destino"

        # Como id_chofer ya no esta en Meta.fields, hay que reordenarlo manualmente
        # para que aparezca en el lugar correcto del formulario (despues de fecha_hora_inicio)
        self.order_fields(['fecha_hora_inicio', 'id_chofer', 'id_bus', 'id_terminal_inicio', 'id_terminal_final'])

    def clean(self):
        cleaned_data = super().clean()
        terminal_inicio = cleaned_data.get('id_terminal_inicio')
        terminal_final = cleaned_data.get('id_terminal_final')
        if terminal_inicio and terminal_final and terminal_inicio == terminal_final:
            raise forms.ValidationError("El terminal de origen y destino no pueden ser el mismo.")
        return cleaned_data
    
class BoletoForm(forms.ModelForm):
    TIPOS_BOLETO = [
        ('Normal', 'Normal'),
        ('Estudiante', 'Estudiante'),
        ('Adulto Mayor', 'Adulto Mayor'),
        ('Discapacidad', 'Discapacidad'),
    ]

    tipo_boleto = forms.ChoiceField(choices=TIPOS_BOLETO, label='Tipo de Boleto')

    class Meta:
        model = Boleto
        fields = ['tipo_boleto', 'num_asiento', 'ciudad_inicial', 'ciudad_final', 'id_viaje']
        labels = {
            'num_asiento': 'Número de Asiento',
            'ciudad_inicial': 'Ciudad de Origen',
            'ciudad_final': 'Ciudad de Destino',
            'id_viaje': 'Viaje',
        }
        widgets = {
            'ciudad_inicial': forms.TextInput(attrs={'placeholder': 'Ej: Concepcion'}),
            'ciudad_final': forms.TextInput(attrs={'placeholder': 'Ej: Santiago'}),
            'num_asiento': forms.NumberInput(attrs={'placeholder': 'Ej: 14'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_viaje'].queryset = Viaje.objects.select_related(
            'id_terminal_inicio', 'id_terminal_final'
        ).order_by('-fecha_hora_inicio')
        self.fields['id_viaje'].empty_label = "Seleccione un viaje"

    def clean_num_asiento(self):
        num_asiento = self.cleaned_data.get('num_asiento')
        if num_asiento is not None and num_asiento <= 0:
            raise forms.ValidationError("El número de asiento debe ser mayor a 0.")
        return num_asiento