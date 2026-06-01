from django.urls import path
from plataforma import views

urlpatterns = [
    path('', views.dashboard_usuario, name='dashboard'),
    path('suscripcion/', views.procesar_suscripcion, name='suscripcion'),
    path('catalogo/', views.catalogo_artistas, name='catalogo'),
    path('catalogo/reproducir/<int:id_cancion>/', views.reproducir_cancion, name='reproducir_cancion'),
    path('historial/', views.historial_reproduccion, name='historial'),
    path('historial/pdf/', views.exportar_historial_pdf, name='exportar_historial_pdf'),
    path('eliminar-usuario/', views.eliminar_usuario, name='eliminar_usuario'),
    path('administracion/', views.administracion, name='administracion'),
    path('administracion/crear/', views.crear_oyente, name='crear_oyente'),
    path('administracion/editar/<int:id_usuario>/', views.editar_oyente, name='editar_oyente'),
    path('administracion/eliminar/<int:id_usuario>/', views.eliminar_oyente, name='eliminar_oyente'),
]
