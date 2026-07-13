from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from .models import Usuario, Terminal, Bus
from .forms import LoginForm, TerminalForm, BusForm
from functools import wraps


# ── Seguridad ─────────────────────────────────────────────────────────────────

def rol_requerido(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.rol not in roles and not request.user.is_superuser:
                messages.error(request, "No tienes permiso para acceder a esta seccion.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user and user.is_active:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, "Credenciales incorrectas o cuenta inactiva.")
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    # Es para ver cuantos buses estan en un terminal
    buses_en_terminal = Bus.objects.filter(id_terminal__isnull=False).count()
    
    context = {
        'total_terminales': Terminal.objects.count(),
        'total_buses': Bus.objects.count(),
        # Si es null es porque no esta en ningun terminal
        'buses_en_ruta': Bus.objects.filter(id_terminal__isnull=True).count(),
        
        # Agregamos esta variable para reemplazar la de mantenimiento usando lógica real
        'buses_en_terminal': buses_en_terminal,
        
        # Traemos los primeros 5 terminales ordenados por su nombre o id_terminal
        'terminales_recientes': Terminal.objects.all().order_by('nombre')[:5],
    }
    return render(request, 'dashboard.html', context)


# ── Terminales ────────────────────────────────────────────────────────────────

@login_required
def lista_terminales(request):
    q = request.GET.get('q', '')
    # Quitamos .filter(activo=True) y .select_related('administrador') porque no existen así en la BD
    terminales = Terminal.objects.all()
    if q:
        # Nota: Como capacidad_buses es un número (Integer), usar __icontains puede dar error en PostgreSQL.
        # Si te falla la búsqueda, quita la parte de capacidad_buses y deja solo dirección y nombre.
        terminales = terminales.filter(
            Q(direccion__icontains=q) | Q(nombre__icontains=q)
        )
    terminales = terminales.annotate(
        total_buses=Count('buses')
    )
    return render(request, 'lista.html', {
        'terminales': terminales,
        'q': q
    })


@login_required
def detalle_terminal(request, terminal_id):
    # Quitamos activo=True ya que la llave primaria (pk) basta para buscarlo
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    
    # Cambiamos 'terminal_actual' por 'id_terminal'
    buses = Bus.objects.filter(id_terminal=terminal)
    
    # Como el bus ya no tiene una columna 'estado', calculamos cuántos hay en total
    # asignados a este terminal en específico.
    total_buses_en_este_terminal = buses.count()
    
    buses_por_estado = {
        'en_terminal': total_buses_en_este_terminal,
        'en_ruta': 0,          # Forzado a 0 ya que si están en esta lista, están en el terminal
        'mantenimiento': 0,    # Eliminados al no estar en la BD
        'fuera_servicio': 0,   # Eliminados al no estar en la BD
    }
    
    return render(request, 'detalle.html', {
        'terminal': terminal,
        'buses': buses,
        'buses_por_estado': buses_por_estado,
    })


@login_required
@rol_requerido('superadmin', 'administrativo')
def crear_terminal(request):
    form = TerminalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        terminal = form.save()
        messages.success(request, f"Terminal '{terminal.nombre}' creado exitosamente.")
        return redirect('lista_terminales')
    
    # OJO: Aquí tenías render(request, '.html'), asegúrate de poner el nombre correcto de tu plantilla, ej: 'crear.html'
    return render(request, 'crear_terminal.html', {'form': form, 'titulo': 'Nuevo Terminal'})


@login_required
@rol_requerido('superadmin', 'administrativo')
def editar_terminal(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    form = TerminalForm(request.POST or None, instance=terminal)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Terminal '{terminal.nombre}' actualizado.")
        return redirect('detalle_terminal', terminal_id=terminal.pk)
    return render(request, 'form.html', {'form': form, 'titulo': f'Editar — {terminal.nombre}'})


@login_required
@rol_requerido('superadmin')
def eliminar_terminal(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    terminal.activo = False
    terminal.save()
    messages.success(request, f"Terminal '{terminal.nombre}' desactivado.")
    return redirect('lista_terminales')


# ── Buses ─────────────────────────────────────────────────────────────────────

@login_required
def lista_buses(request):
    q = request.GET.get('q', '')
    accesibilidad = request.GET.get('accesibilidad', '')  # Filtro real de la BD
    
    # Traemos los buses con su terminal real asignado de la BD
    buses = Bus.objects.select_related('id_terminal')
    
    # 1. Filtrado por texto (Búsqueda por patente)
    if q:
        buses = buses.filter(Q(patente__icontains=q))
        
    # 2. Filtrado por Accesibilidad Universal (Elemento real de la BD)
    if accesibilidad:
        if accesibilidad == 'si':
            buses = buses.filter(accesibilidad_universal=True)
        elif accesibilidad == 'no':
            buses = buses.filter(accesibilidad_universal=False)
            
    return render(request, 'buses/lista_buses.html', {
        'buses': buses,
        'q': q,
        'accesibilidad': accesibilidad,  # Pasamos el filtro aplicado al HTML
    })


@login_required
@rol_requerido('superadmin', 'administrativo')
def crear_bus(request):
    form = BusForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        bus = form.save()
        messages.success(request, f"Bus {bus.patente} registrado exitosamente.")
        return redirect('lista_buses')
    return render(request, 'buses/form_buses.html', {'form': form, 'titulo': 'Registrar Bus'})


@login_required
@rol_requerido('superadmin', 'administrativo')
def editar_bus(request, bus_id):
    bus = get_object_or_404(Bus, pk=bus_id)
    form = BusForm(request.POST or None, instance=bus)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Bus {bus.patente} actualizado.")
        return redirect('lista_buses')
    return render(request, 'form.html', {'form': form, 'titulo': f'Editar Bus — {bus.patente}'})