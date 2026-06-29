# Matriz de Trazabilidad — SoundWave
## Caso de Uso / Requerimiento → Implementación Técnica NoSQL (MongoDB)

Esta matriz conecta cada uno de los requerimientos y casos de uso del sistema con sus correspondientes artefactos de datos en MongoDB Atlas, lógica en la capa de acceso a datos (`fase7_mongo_db_utils.py`) y las vistas en el framework Django (`views.py`).

| # | Caso de Uso / Requerimiento | Colección(es) MongoDB | Función Python (fase7_mongo_db_utils.py) | Vista Django (views.py) |
|---|---|---|---|---|
| 1 | Registro de usuario | `usuarios`, `suscripciones` (si es Premium) | `crear_usuario_sp` | `crear_oyente` / `registro_view` |
| 2 | Login y validación de perfil | `usuarios` | `validar_credenciales_mongo`, `obtener_perfil_usuario_mongo` | `login_view` |
| 3 | Catálogo musical completo | `canciones`, `artistas` | `get_catalogo_completo` | `catalogo_artistas` |
| 4 | Reproducción de canción | `canciones`, `reproducciones` | `registrar_reproduccion_mongo` | `reproducir_cancion` |
| 5 | Historial de escucha | `reproducciones`, `canciones` | `get_historial_completo` | `historial_reproduccion` / `exportar_historial_pdf` |
| 6 | Gestión de playlists | `playlists` | `get_detalle_playlist_mongo` | `detalle_playlist` |
| 7 | Likes de canciones | `usuarios` (arreglo embebido `likes_canciones`) | **No implementada** (Inicialización de array vacío pasivo; no existe lógica de escritura/endpoints) | **No implementada** (Manejo pasivo de datos) |
| 8 | Artistas seguidos | `usuarios` (arreglo embebido `artistas_seguidos`) | **No implementada** (Inicialización de array vacío pasivo; no existe lógica de escritura/endpoints) | **No implementada** (Manejo pasivo de datos) |
| 9 | Álbumes guardados por usuario | `usuarios` (arreglo embebido `albumes_guardados`) | `agregar_album_guardado`, `quitar_album_guardado` | `agregar_album_view`, `quitar_album_view`, `detalle_album` |
| 10 | Suscripción y plan activo | `usuarios`, `suscripciones` | `get_suscripcion_data`, `obtener_perfil_usuario_mongo` | `procesar_suscripcion` |
| 11 | Procesamiento de pagos | `suscripciones`, `usuarios` | `procesar_renovacion_mongo` | `procesar_suscripcion` |
| 12 | Pagos fallidos y vencimientos | `suscripciones`, `usuarios` | `procesar_renovacion_mongo` | `procesar_suscripcion` |
| 13 | Notificaciones al usuario | `usuarios` (arreglo embebido `notificaciones`) | **No implementada** (Inicialización de array vacío pasivo; no existe lógica de alertas) | **No implementada** (Manejo pasivo de datos) |
| 14 | Reportes musicales (top canciones, artistas) | `canciones`, `artistas`, `usuarios`, `suscripciones` | `generar_reporte_mongo` | `reportes` |
| 15 | Cálculo de regalías por artista | `canciones` (stream counts), `artistas` | **No dedicada** (Cálculo inline multiplicando reproducciones * tarifa `0.004` USD) | `reportes` / `administracion` |
| 16 | Detalle completo de artista | `artistas`, `canciones` | `get_detalle_artista_mongo` | `detalle_artista` |
| 17 | Detalle completo de álbum | `artistas` (subdocumento `albumes`), `canciones` | `get_detalle_album_mongo` | `detalle_album` |
| 18 | CRUD administrativo de usuarios | `usuarios`, `suscripciones`, `playlists`, `reproducciones` | `crear_usuario_sp`, `actualizar_usuario_sp`, `eliminar_usuario_sp` | `crear_oyente`, `editar_oyente`, `eliminar_oyente` |
| 19 | CRUD administrativo de artistas | `artistas`, `canciones`, `playlists`, `reproducciones` | `crear_artista_sp`, `actualizar_artista_sp`, `eliminar_artista_sp` | `crear_artista`, `editar_artista`, `eliminar_artista` |
| 20 | Protección de usuario principal (no eliminable) | `usuarios` | `eliminar_usuario_bd` (valida contra ID `12` / `usuario_protegido_id`) | `eliminar_oyente` / `eliminar_usuario` |

---

### Hallazgos de la Auditoría Técnica sobre el Modelo Embebido

*   **Casos 7 (Likes), 8 (Artistas Seguidos) y 13 (Notificaciones)**: Estas características están definidas en el esquema NoSQL NoSQL-documental como colecciones/arreglos embebidos en el documento de `usuarios` en MongoDB (ej: `"likes_canciones": []`). Sin embargo, no se crearon funciones de escritura dedicadas en la capa de utilidades ni llamadas en vistas de Django, quedando como datos pasivos inicializados en vacío en el registro de usuarios.
*   **Caso 15 (Regalías)**: No requiere una función dedicada, pues su cálculo es aritmético y en tiempo real. Se obtiene directamente multiplicando la cantidad de reproducciones de las canciones del artista por `0.004` (Tarifa por stream) de forma inline dentro de las funciones de recolección de estadísticas de administración y generación de reportes.
