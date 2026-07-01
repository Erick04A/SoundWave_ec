# SoundWave

> Plataforma de streaming musical con base de datos MongoDB Atlas y aplicación web Django.
> Proyecto Integrador — Base de Datos II · Universidad de las Américas · Equipo 6 · 2026

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Base de datos | MongoDB Atlas (ClusterUdla02, AWS São Paulo) |
| Conexión BD | PyMongo 4.10.1 con pool de conexiones |
| Backend | Python 3.x + Django 5.2.14 |
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Reportes | ReportLab (exportación PDF) |
| Versiones | Git + GitHub |

---

## Instalación rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/Erick04A/SoundWave_ec.git
cd SoundWave_ec

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar credenciales
copy config.example.json config.json
# Abrir config.json y completar usuario y contrasena de MongoDB

# 5. Levantar el servidor
python manage.py runserver
```

Acceder en `http://127.0.0.1:8000`

---

## Cómo interactuar con la base de datos en MongoDB Compass

La base de datos vive en MongoDB Atlas (nube). Cualquier cambio hecho desde Compass se refleja inmediatamente en la web, y viceversa.

### Conectarse a Atlas desde Compass

1. Abrir MongoDB Compass
2. Pegar la cadena de conexión:
```
   mongodb+srv://TU_USUARIO@clusterudla02.cf3j95i.mongodb.net/
```
3. Reemplazar `TU_USUARIO` y la contraseña con tus propias credenciales
4. Clic en **Connect**
5. Seleccionar la base de datos `SoundWaveDB`

### Agregar un documento nuevo (ejemplo: nuevo usuario)

1. Abrir la colección `usuarios`
2. Clic en **Add Data → Insert Document**
3. Pegar el JSON con los datos del nuevo usuario:
```json
   {
     "id_usuario": 99,
     "nombre_usuario": "Nuevo Usuario",
     "email_usuario": "nuevo@soundwave.ec",
     "estado": "Activo",
     "rol": "Oyente",
     "suscripcion_activa": null,
     "albumes_guardados": [],
     "likes_canciones": [],
     "artistas_seguidos": [],
     "notificaciones": []
   }
```
4. Clic en **Insert**
5. Refrescar `/administracion/` en el navegador — el usuario aparece inmediatamente

### Buscar un documento específico

En la barra de filtro de Compass escribe el criterio de búsqueda y clic en **Apply**:

```json
// Buscar por ID de usuario
{ "id_usuario": 99 }

// Buscar por email
{ "email_usuario": "mlopez@soundwave.ec" }

// Buscar por nombre
{ "nombre_usuario": "Maria Lopez" }

// Buscar suscripciones activas
{ "estado": "Activa" }
```

O desde el shell MongoDB (`>_MONGOSH`) en Compass:
```javascript
use('SoundWaveDB')
db.usuarios.findOne({ "id_usuario": 99 })
```

### Eliminar un documento

Opción 1 — Interfaz gráfica:
1. Aplica el filtro para encontrar el documento
2. Pasa el mouse sobre el documento
3. Clic en el ícono de **papelera** que aparece a la derecha
4. Confirmar con **Delete**

Opción 2 — Shell:
```javascript
db.usuarios.deleteOne({ "id_usuario": 99 })
```

### Verificar que el cambio se refleja en la web

Después de cualquier operación en Compass, simplemente refresca la página en el navegador sin reiniciar el servidor — los datos se sincronizan en tiempo real porque Django consulta Atlas directamente en cada request, sin caché intermedia.

---

## Colecciones de SoundWaveDB

| Colección | Documentos | Descripción |
|---|---|---|
| `usuarios` | 27 | Oyentes, artistas y administradores |
| `artistas` | 15 | Perfiles con discografía embebida |
| `canciones` | 28 | Catálogo musical con géneros |
| `playlists` | 10 | Listas de reproducción |
| `reproducciones` | 71+ | Historial de escuchas |
| `suscripciones` | 9 | Contratos y pagos |

---

## Vistas de la aplicación web

| Vista | URL | Acceso |
|---|---|---|
| Dashboard | `/` | Oyente / Admin |
| Catálogo | `/catalogo/` | Oyente |
| Historial | `/historial/` | Oyente |
| Suscripción | `/suscripcion/` | Oyente |
| Reportes | `/reportes/` | Oyente (reportes propios) / Admin (todos) |
| Panel Admin | `/administracion/` | Solo Administrador |
| Login | `/login/` | Público |

---

## Fases del proyecto

| Fase | Descripción | Nota |
|---|---|---|
| Fase 1 | Análisis del caso de negocio y casos de uso | — |
| Fase 2 | Diseño lógico y físico SQL Server | — |
| Fase 3 | Implementación SQL Server + stored procedures | **10/10** |
| Fase 4 | Aplicación web Django + pyodbc + SQL Server | — |
| Fase 5 | Diseño del modelo NoSQL en MongoDB | — |
| Fase 6 | Implementación MongoDB (migración + playground) | — |
| Fase 7 | Aplicación web Django + PyMongo + MongoDB Atlas | En curso |

---

## Equipo

**Equipo 6 · Base de Datos II · UDLA 2026**

| Integrante | Rol Scrum | Contribución |
|---|---|---|
| Erick Quinchiguango | Scrum Master · Dev Lead | Arquitectura Django, PyMongo, integración, GitHub |
| Nicole Yépez | Product Owner · Documentación | Documentación técnica, análisis, entregables |
| Martín Gaona | Developer · Producción | Frontend, CSS, video de demostración |

---

*Base de Datos II · Universidad de las Américas · 2026*
