from django.urls import path
from terminales import views
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    #ADMIN
    path('admin/', admin.site.urls),
    #path('', include('terminales.urls')), GENERA ERRORES

    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Terminales
    path('terminales/', views.lista_terminales, name='lista_terminales'),
    path('terminales/nuevo/', views.crear_terminal, name='crear_terminal'),
    path('terminales/<int:terminal_id>/', views.detalle_terminal, name='detalle_terminal'),
    path('terminales/<int:terminal_id>/editar/', views.editar_terminal, name='editar_terminal'),
    path('terminales/<int:terminal_id>/eliminar/', views.eliminar_terminal, name='eliminar_terminal'),

    # Buses
    path('buses/', views.lista_buses, name='lista_buses'),
    path('buses/nuevo/', views.crear_bus, name='crear_bus'),
    path('buses/<int:bus_id>/editar/', views.editar_bus, name='editar_bus'),

    # Viajes y Asientos
    path('viajes/', views.lista_viajes, name='lista_viajes'),
    path('viajes/<int:viaje_id>/asientos/', views.disponibilidad_asientos, name='disponibilidad_asientos'),
    path('viajes/<int:viaje_id>/asientos/<int:num_asiento>/reservar/', views.reservar_asiento, name='reservar_asiento'),

    # Vinculación Bus-Terminal
    path('buses/vincular/', views.vincular_bus_terminal, name='vincular_bus_terminal'),
    path('buses/<int:bus_id>/desvincular/', views.desvincular_bus, name='desvincular_bus'),

    # Reportes (Requerimiento 3)
    path('reportes/nuevo/', views.crear_reporte, name='crear_reporte'),
]