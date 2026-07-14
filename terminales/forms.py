from django import forms
from .models import Terminal, Bus, Usuario
from .models import Terminal, Bus, Usuario, Chofer


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