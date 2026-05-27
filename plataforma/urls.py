from django.urls import path
from plataforma import views

urlpatterns = [
    path('', views.dashboard_usuario, name='dashboard'),
    path('suscripcion/', views.procesar_suscripcion, name='suscripcion'),
    path('catalogo/', views.catalogo_artistas, name='catalogo'),
    path('historial/', views.historial_reproduccion, name='historial'),
]
