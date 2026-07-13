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

]