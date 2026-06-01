# 🎵 SoundWave — Plataforma de Streaming Musical

Proyecto integrador desarrollado para la materia **Base de Datos II** — UDLA 2026.

## Descripción

SoundWave es una plataforma de streaming musical completa con base de datos transaccional en **Microsoft SQL Server** e interfaz web construida con **Django + Python**.

## Stack tecnológico

- **Backend:** Python 3.x + Django 4.2
- **Base de datos:** Microsoft SQL Server 2022
- **Conexión BD:** pyodbc (sin ORM, queries directas)
- **Frontend:** HTML, CSS, JavaScript vanilla

## Estructura del proyecto
AvancesSQL/
plataforma/
templates/       # Vistas HTML
static/          # CSS, JS, imágenes
db_utils.py      # Capa de acceso a datos
views.py         # Controladores
urls.py          # Rutas
SoundWaveProject/  # Configuración Django
recreate_soundwave_db.sql  # Script completo de BD
manage.py
requirements.txt

## Funcionalidades principales

- Dashboard con estadísticas reales del oyente
- Catálogo musical con ranking por reproducciones
- Historial con filtros por fecha y género + exportación PDF
- Pasarela de pagos que invoca stored procedures en SQL Server
- Panel de administración con CRUD completo de usuarios
- Búsqueda en tiempo real sin recarga de página

## Stored Procedures implementados

| SP | Función |
|---|---|
| `sp_RegistrarReproduccion` | Registra reproducción con transacción atómica |
| `sp_CalcularRegalias` | Calcula liquidación mensual por artista |
| `sp_ProcesarRenovacion` | Gestiona pagos exitosos y fallidos |
| `sp_NotificarSuscripcionesProximas` | Alertas de vencimiento con cursor |

## Configuración

1. Instalar dependencias: `pip install -r requirements.txt`
2. Configurar SQL Server en `SoundWaveProject/settings.py`
3. Ejecutar `recreate_soundwave_db.sql` en SQL Server
4. Correr el servidor: `python manage.py runserver`

## Equipo

**Equipo 6 — Base de Datos II UDLA 2026**
- Yepez, Nicole
- Quinchiguango, Erick  
- Gaona, Martin
