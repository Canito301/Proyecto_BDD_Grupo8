from django import forms
from .models import Terminal, Bus, Usuario, Chofer, Administrativo


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