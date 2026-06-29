# SoundWave — Guía de Despliegue Rápido

Este proyecto corre 100% sobre MongoDB Atlas (nube). No requiere SQL Server,
no requiere instalar ninguna base de datos local, no requiere configurar IPs.

## Requisitos previos en la nueva PC
- Python 3.11 o superior instalado
- Conexión a internet (para llegar a MongoDB Atlas)
- Git instalado

## Pasos exactos (copiar y pegar en orden)

### 1. Clonar el repositorio
git clone https://github.com/Erick04A/SoundWave.git
cd SoundWave

### 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

### 3. Instalar dependencias exactas
pip install -r requirements.txt

### 4. Crear el archivo de configuración
copy config.example.json config.json

Luego abrir config.json y reemplazar únicamente estos 2 valores
con las credenciales reales que te compartió Erick:
- "usuario": "Admin"
- "contrasena": "(la contraseña real)"

El resto del archivo (cluster, base_datos, app) NO se modifica.

### 5. Levantar el servidor
python manage.py runserver

### 6. Verificar que funciona
Abrir el navegador en http://127.0.0.1:8000
Debe cargar el Dashboard con datos reales de SoundWave (no debe estar vacío).

## Si algo falla
- Error de conexión a MongoDB: revisar que config.json tenga la contraseña correcta, sin comillas extra ni espacios.
- Error "module not found": volver a ejecutar pip install -r requirements.txt dentro del venv activado.
- Puerto ocupado: ejecutar python manage.py runserver 8080 y abrir esa URL en su lugar.

## Importante
Todos los datos están en MongoDB Atlas (nube). No hay base de datos local.
Cualquier cambio que se haga desde esta PC se refleja inmediatamente en
la misma base de datos que usan los demás miembros del equipo.
