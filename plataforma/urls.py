from django.urls import path

from plataforma import views

urlpatterns = [

    path('', views.landing_or_dashboard, name='dashboard'),

    path('login/', views.login_view, name='login'),

    path('registro/', views.registro_view, name='registro'),

    path('verificacion-telefono/', views.verificacion_telefono, name='verificacion_telefono'),

    path('logout/', views.logout_view, name='logout'),

    path('suscripcion/', views.procesar_suscripcion, name='suscripcion'),
    path('suscripcion/cancelar/', views.cancelar_suscripcion_propia, name='cancelar_suscripcion_propia'),

    path('catalogo/', views.catalogo_artistas, name='catalogo'),

    path('catalogo/reproducir/<int:id_cancion>/', views.reproducir_cancion, name='reproducir_cancion'),

    path('historial/', views.historial_reproduccion, name='historial'),

    path('historial/pdf/', views.exportar_historial_pdf, name='exportar_historial_pdf'),

    path('eliminar-usuario/', views.eliminar_usuario, name='eliminar_usuario'),

    path('administracion/', views.administracion, name='administracion'),

    path('administracion/crear/', views.crear_oyente, name='crear_oyente'),

    path('administracion/editar/<int:id_usuario>/', views.editar_oyente, name='editar_oyente'),

    path('administracion/eliminar/<int:id_usuario>/', views.eliminar_oyente, name='eliminar_oyente'),

    path('administracion/artista/crear/', views.crear_artista, name='crear_artista'),

    path('administracion/artista/editar/<int:id_artista>/', views.editar_artista, name='editar_artista'),

    path('administracion/artista/eliminar/<int:id_artista>/', views.eliminar_artista, name='eliminar_artista'),

    path('administracion/album/crear/', views.crear_album, name='crear_album'),

    path('administracion/album/editar/<int:id_album>/', views.editar_album, name='editar_album'),

    path('administracion/album/eliminar/<int:id_album>/', views.eliminar_album, name='eliminar_album'),

    path('administracion/cancion/crear/', views.crear_cancion, name='crear_cancion'),

    path('administracion/cancion/editar/<int:id_cancion>/', views.editar_cancion, name='editar_cancion'),

    path('administracion/cancion/eliminar/<int:id_cancion>/', views.eliminar_cancion, name='eliminar_cancion'),

    path('artista/<int:id_artista>/', views.detalle_artista, name='detalle_artista'),

    path('album/<int:id_album>/', views.detalle_album, name='detalle_album'),
    path('album/<int:id_album>/guardar/', views.agregar_album_view, name='agregar_album_guardado'),
    path('album/<int:id_album>/quitar/', views.quitar_album_view, name='quitar_album_guardado'),

    path('playlist/<int:id_playlist>/', views.detalle_playlist, name='detalle_playlist'),

    path('reportes/', views.reportes, name='reportes'),

    path('soporte/', views.soporte, name='soporte'),

    path('planes/', views.planes, name='planes'),

    path('verificacion-estudiantil/', views.verificacion_estudiantil, name='verificacion_estudiantil'),

    path('verificar-admin/', views.verificar_admin, name='verificar_admin'),

    path('ajustes/', views.ajustes, name='ajustes'),

    path('informacion/', views.informacion, name='informacion'),
    path('terminos-y-condiciones/', views.terminos_condiciones, name='terminos_condiciones'),
]