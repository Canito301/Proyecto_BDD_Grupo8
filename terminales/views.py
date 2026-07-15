from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from functools import wraps
from .models import Usuario, Terminal, Bus, Viaje, Asiento, Chofer, Administrativo, Reporte, BusReporte, ChoferReporte, Boleto, Tramo
from .forms import LoginForm, TerminalForm, BusForm, ChoferForm, AdministrativoForm, ReporteForm, ViajeForm, BoletoForm, TramoForm

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

        'total_choferes': Chofer.objects.count(),
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
    return render(request, 'buses/form_buses.html', { 
        'form': form, 
        'titulo': f'Editar Bus — {bus.patente}'
    })


# ── Viajes y Asientos ──────────────────────────────────────────────────────────

@login_required
def lista_viajes(request):
    viajes = Viaje.objects.select_related('id_terminal_inicio', 'id_terminal_final', 'id_bus').all().order_by('-fecha_hora_inicio')
    return render(request, 'viajes/lista_viajes.html', {'viajes': viajes})


@login_required
def disponibilidad_asientos(request, viaje_id):
    viaje = get_object_or_404(Viaje.objects.select_related('id_terminal_inicio', 'id_terminal_final', 'id_bus'), pk=viaje_id)
    # Obtener asientos del bus asignado a este viaje
    asientos = Asiento.objects.filter(id_bus=viaje.id_bus_id).order_by('num_asiento')
    
    return render(request, 'asientos/disponibilidad.html', {
        'viaje': viaje,
        'asientos': asientos
    })


@login_required
def reservar_asiento(request, viaje_id, num_asiento):
    if request.method == 'POST':
        viaje = get_object_or_404(Viaje, pk=viaje_id)
        # Asiento específico del bus asignado al viaje
        asiento = get_object_or_404(Asiento, id_bus=viaje.id_bus_id, num_asiento=num_asiento)
        
        if asiento.estado: # Si está disponible
            # Usamos update() con ambos campos para la PK compuesta
            Asiento.objects.filter(id_bus=viaje.id_bus_id, num_asiento=num_asiento).update(estado=False)
            messages.success(request, f"¡Asiento {num_asiento} reservado exitosamente!")
        else:
            messages.error(request, f"El asiento {num_asiento} ya se encuentra ocupado.")
            
    return redirect('disponibilidad_asientos', viaje_id=viaje_id)


# ── Vinculación de Bus a Terminal ──────────────────────────────────────────────

@login_required
@rol_requerido('superadmin', 'administrativo')
def vincular_bus_terminal(request):
    """Lista buses en ruta (sin terminal) y permite vincularlos a un terminal."""
    buses_en_ruta = Bus.objects.filter(id_terminal__isnull=True).order_by('patente')
    buses_vinculados = Bus.objects.filter(id_terminal__isnull=False).select_related('id_terminal').order_by('patente')
    terminales = Terminal.objects.all().order_by('nombre')
    
    if request.method == 'POST':
        bus_id = request.POST.get('bus_id')
        terminal_id = request.POST.get('terminal_id')
        
        bus = get_object_or_404(Bus, pk=bus_id)
        terminal = get_object_or_404(Terminal, pk=terminal_id)
        
        # Validación: verificar que el bus no esté ya en otro terminal
        if bus.id_terminal_id is not None:
            messages.error(
                request,
                f"El bus {bus.patente} ya se encuentra vinculado al terminal "
                f"{bus.id_terminal.nombre}. Debe desvincularlo primero."
            )
            return redirect('vincular_bus_terminal')
        
        # Validación: verificar que el bus no tenga un viaje activo en curso
        ahora = timezone.now()
        viaje_activo = Viaje.objects.filter(
            id_bus=bus,
            fecha_hora_inicio__lte=ahora,  # Ya comenzó
        ).order_by('-fecha_hora_inicio').first()
        
        # Si tiene viaje activo, verificar que el terminal destino coincida
        if viaje_activo and viaje_activo.id_terminal_final_id != terminal.pk:
            messages.error(
                request,
                f"El bus {bus.patente} tiene un viaje activo con destino a "
                f"{viaje_activo.id_terminal_final.nombre}. "
                f"Solo puede vincularse a ese terminal."
            )
            return redirect('vincular_bus_terminal')
        
        # Todo OK: vincular el bus al terminal
        Bus.objects.filter(pk=bus.pk).update(id_terminal=terminal)
        messages.success(
            request,
            f"Bus {bus.patente} vinculado exitosamente al terminal {terminal.nombre}."
        )
        return redirect('vincular_bus_terminal')
    
    return render(request, 'buses/vincular_bus.html', {
        'buses_en_ruta': buses_en_ruta,
        'buses_vinculados': buses_vinculados,
        'terminales': terminales,
    })


@login_required
@rol_requerido('superadmin', 'administrativo')
def desvincular_bus(request, bus_id):
    """Desvincula un bus de su terminal actual (lo pone en ruta)."""
    if request.method == 'POST':
        bus = get_object_or_404(Bus, pk=bus_id)
        nombre_terminal = bus.id_terminal.nombre if bus.id_terminal else 'N/A'
        Bus.objects.filter(pk=bus.pk).update(id_terminal=None)
        messages.success(request, f"Bus {bus.patente} desvinculado del terminal {nombre_terminal}.")
    return redirect('vincular_bus_terminal')




@login_required
def crear_reporte(request):
    if request.method == 'POST':
        form = ReporteForm(request.POST)
        if form.is_valid():
            try:
                # 1. Buscar al administrativo
                admin_bd = Administrativo.objects.filter(rut=request.user.rut).first()

                # Malla de seguridad para superusuarios sin RUT en la tabla administrativo
                if not admin_bd:
                    admin_bd = Administrativo.objects.first()
                    if not admin_bd:
                        messages.error(request,
                                       "Error: No hay administrativos en la Base de Datos para crear reportes.")
                        return redirect('dashboard')

                # 2. Crear el Reporte
                nuevo_reporte = Reporte.objects.create(
                    id_admin=admin_bd,
                    tipo=form.cleaned_data['tipo'],
                    descripcion=form.cleaned_data['descripcion']
                )

                # 3. Vincular Bus
                bus = form.cleaned_data.get('id_bus')
                if bus:
                    BusReporte.objects.create(id_bus=bus, id_reporte=nuevo_reporte)

                # 4. Vincular Chofer
                chofer = form.cleaned_data.get('id_chofer')
                if chofer:
                    ChoferReporte.objects.create(id_reporte=nuevo_reporte, id_chofer=chofer)

                messages.success(request, f"El reporte #{nuevo_reporte.id_reporte} ha sido registrado exitosamente.")
                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f"Hubo un error al guardar en la base de datos: {str(e)}")
    else:
        form = ReporteForm()

    return render(request, 'crear_reporte.html', {'form': form})


# ── Chofer ──────────────────────────────────────────────────────────


@login_required
@rol_requerido('superadmin', 'administrativo')
def crear_chofer(request):
    form = ChoferForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        chofer = form.save()
        messages.success(request, f"Chofer {chofer.nombre} inscrito exitosamente.")
        return redirect('lista_choferes')
    return render(request, 'chofer/form_chofer.html', {'form': form, 'titulo': 'Inscribir Chofer'})

@login_required
def lista_choferes(request):
    q = request.GET.get('q', '')
    choferes = Chofer.objects.all()

    # Si el usuario escribió algo en el buscador, filtramos por RUT o Nombre
    if q:
        choferes = choferes.filter(
            Q(rut__icontains=q) | Q(nombre__icontains=q)
        )

    return render(request, 'chofer/lista_choferes.html', {
        'choferes': choferes,
        'q': q
    })

@login_required
@rol_requerido('superadmin', 'administrativo')
def editar_chofer(request, chofer_id):
    # 1. Buscamos al chofer en la base de datos por su ID (la PK autoincremental)
    chofer = get_object_or_404(Chofer, pk=chofer_id)

    # 2. Cargamos el formulario.
    # El 'instance=chofer' es vital: le dice a Django que pre-llene los campos con los datos actuales
    form = ChoferForm(request.POST or None, instance=chofer)

    # 3. Si el usuario modificó algo y apretó "Guardar"
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Chofer {chofer.nombre} actualizado exitosamente.")
        return redirect('lista_choferes')

    # 4. Si solo está entrando a la página, le mostramos el HTML (podemos reciclar el mismo que usamos para crear)
    return render(request, 'chofer/form_chofer.html', {
        'form': form,
        'titulo': f'Editar Chofer — {chofer.rut}'
    })


# ── Administrativos ──────────────────────────────────────────────────────────

@login_required
def lista_administrativos(request):
    q = request.GET.get('q', '')
    # select_related optimiza la consulta JOIN con la tabla terminal
    administrativos = Administrativo.objects.select_related('id_terminal').all()

    if q:
        administrativos = administrativos.filter(
            Q(rut__icontains=q) | Q(nombre__icontains=q)
        )

    return render(request, 'administrativo/lista_administrativos.html', {
        'administrativos': administrativos,
        'q': q
    })


@login_required
@rol_requerido('superadmin', 'administrativo')
def crear_administrativo(request):
    form = AdministrativoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Administrativo registrado exitosamente.")
        return redirect('lista_administrativos')

    return render(request, 'administrativo/form_administrativo.html', {
        'form': form,
        'titulo': 'Registrar Administrativo'
    })


@login_required
@rol_requerido('superadmin', 'administrativo')
def editar_administrativo(request, admin_id):
    admin = get_object_or_404(Administrativo, pk=admin_id)
    form = AdministrativoForm(request.POST or None, instance=admin)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Administrativo {admin.nombre} actualizado exitosamente.")
        return redirect('lista_administrativos')

    return render(request, 'administrativo/form_administrativo.html', {
        'form': form,
        'titulo': f'Editar Administrativo — {admin.rut}'
    })
@login_required
def lista_viajes(request):
    if request.method == 'POST':
        form = ViajeForm(request.POST)
        if form.is_valid():
            viaje = form.save(commit=False)
            # id_chofer en el modelo es IntegerField, asi que guardamos el numero real
            viaje.id_chofer = form.cleaned_data['id_chofer'].id_chofer
            viaje.save()
            messages.success(request, "Viaje creado exitosamente.")
            return redirect('lista_viajes')
        else:
            messages.error(request, "No se registró el viaje.") #BORRAR DESPUES QUIZA
    else:
        form = ViajeForm()

    viajes = Viaje.objects.select_related('id_terminal_inicio', 'id_terminal_final', 'id_bus').all().order_by('-fecha_hora_inicio')

    return render(request, 'viajes/lista_viajes.html', {
        'viajes': viajes,
        'form': form,
    })
@login_required
def lista_boletos(request):
    q = request.GET.get('q', '')
    boletos = Boleto.objects.select_related('id_viaje').all()

    if q:
        boletos = boletos.filter(
            Q(ciudad_inicial__icontains=q) | Q(ciudad_final__icontains=q)
        )

    return render(request, 'boletos/lista_boletos.html', {
        'boletos': boletos,
        'q': q
    })


@login_required
@rol_requerido('superadmin', 'administrativo')
def crear_boleto(request):
    form = BoletoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        boleto = form.save()
        messages.success(request, f"Boleto #{boleto.id_boleto} generado exitosamente.")
        return redirect('lista_boletos')
    return render(request, 'boletos/form_boleto.html', {'form': form, 'titulo': 'Generar Boleto'})


# ── Tramos ────────────────────────────────────────────────────────────────────

@login_required
def lista_tramos(request):
    origen = request.GET.get('origen', '')
    destino = request.GET.get('destino', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')

    tramos = Tramo.objects.all().order_by('ciudad_inicial', 'ciudad_final')

    if origen:
        tramos = tramos.filter(ciudad_inicial__icontains=origen)
    if destino:
        tramos = tramos.filter(ciudad_final__icontains=destino)
    if precio_min:
        tramos = tramos.filter(precio__gte=precio_min) # gte = Greater Than or Equal (Mayor o igual)
    if precio_max:
        tramos = tramos.filter(precio__lte=precio_max) # lte = Less Than or Equal (Menor o igual)

    return render(request, 'tramo/lista_tramos.html', {
        'tramos': tramos,
        'origen': origen,
        'destino': destino,
        'precio_min': precio_min,
        'precio_max': precio_max,
    })

@login_required
@rol_requerido('superadmin', 'administrativo')
def crear_tramo(request):
    form = TramoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Tramo registrado exitosamente.")
        return redirect('lista_tramos')
        
    return render(request, 'tramo/form_tramo.html', {
        'form': form,
        'titulo': 'Nuevo Tramo'
    })

@login_required
@rol_requerido('superadmin', 'administrativo')
def editar_tramo(request, origen, destino):
    # Buscamos usando ambos componentes de la llave primaria compuesta
    tramo = get_object_or_404(Tramo, ciudad_inicial=origen, ciudad_final=destino)
    
    form = TramoForm(request.POST or None, instance=tramo)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Precios y descuentos para {origen} - {destino} actualizados.")
        return redirect('lista_tramos')
        
    return render(request, 'tramo/form_tramo.html', {
        'form': form,
        'titulo': f'Editar Tramo — {origen} a {destino}'
    })