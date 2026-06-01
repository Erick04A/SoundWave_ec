import os
import pyodbc
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Union
from django.conf import settings

import threading
_thread_local = threading.local()

def get_connection():
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        conn_str_req = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=DESKTOP-6GO61O3\\SQLEXPRESS;"
            "DATABASE=SoundWaveDB;"
            "Trusted_Connection=yes;"
            "Connection Timeout=3;"
        )
        conn_str_local = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost\\SQLEXPRESS;"
            "DATABASE=SoundWaveDB;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
            "Connection Timeout=3;"
        )
        try:
            _thread_local.connection = pyodbc.connect(conn_str_req, timeout=3)
        except pyodbc.Error:
            try:
                _thread_local.connection = pyodbc.connect(conn_str_local, timeout=3)
            except pyodbc.Error as e:
                raise Exception(f"No se pudo conectar a SoundWaveDB: {e}")
    return _thread_local.connection

def close_connection():
    if hasattr(_thread_local, 'connection') and _thread_local.connection:
        try:
            _thread_local.connection.close()
        except:
            pass
        _thread_local.connection = None


@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = get_connection()
        yield conn
    except pyodbc.Error as e:
        print(f"[SoundWave DB Error] Error de conexión pyodbc: {e}")
        raise e
    finally:
        pass  # Las conexiones se cierran al final de la vista vía close_connection()


def execute_stored_procedure(sp_name: str, params: Union[List[Any], None] = None) -> List[Dict[str, Any]]:
    if params is None:
        params = []
        
    placeholders = ", ".join(["?"] * len(params))
    call_query = f"{{CALL {sp_name}({placeholders})}}" if placeholders else f"{{CALL {sp_name}}}"
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(call_query, params)
            
            try:
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    conn.commit()
                    return []
            except pyodbc.ProgrammingError as e:
                conn.commit()
                return []


def execute_non_query(query: str, params: Union[List[Any], None] = None) -> int:
    if params is None:
        params = []
        
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount


def execute_scalar(query: str, params: Union[List[Any], None] = None) -> Any:
    if params is None:
        params = []
        
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else None


def get_dashboard_fallback(error_msg):
    return {
        'error': error_msg,
        'stats': {
            'canciones_escuchadas': 0,
            'albumes_biblioteca': 0,
            'horas_reproduccion': 0.0,
            'nombre_usuario': 'Usuario Temporal',
            'email_usuario': 'temporal@soundwave.com',
            'estado': 'Inactivo',
            'plan_activo': 'Gratuito'
        },
        'albumes': [],
        'historial_reciente': [],
        'cancion_actual': {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'},
        'top_canciones': [],
        'top10_global': [],
        'recomendaciones': []
    }

USUARIO_PROTEGIDO = 12  # Maria Lopez - nunca eliminar

def eliminar_usuario_bd(id_usuario):
    if int(id_usuario) == USUARIO_PROTEGIDO:
        raise Exception("No se puede eliminar el usuario principal del sistema.")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Borrado en cascada manual de todas las dependencias
        cursor.execute(
            "DELETE FROM negocio.PLAYLIST_CANCION WHERE id_playlist IN (SELECT id_playlist FROM negocio.PLAYLIST WHERE id_usuario = ?)",
            [id_usuario]
        )
        cursor.execute("DELETE FROM negocio.PLAYLIST WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM negocio.ALBUM_GUARDADO WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM negocio.HISTORIAL_REPRODUCCION WHERE id_usuario = ?", [id_usuario])
        cursor.execute(
            "DELETE FROM negocio.PAGO WHERE id_suscripcion IN (SELECT id_suscripcion FROM negocio.SUSCRIPCION WHERE id_usuario = ?)",
            [id_usuario]
        )
        cursor.execute("DELETE FROM negocio.SUSCRIPCION WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM negocio.SEGUIMIENTO_ARTISTA WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM negocio.LIKES WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM negocio.NOTIFICACION WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM catalogo.ARTISTA WHERE id_usuario = ?", [id_usuario])
        cursor.execute("DELETE FROM negocio.USUARIO WHERE id_usuario = ?", [id_usuario])
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        close_connection()

def get_dashboard_data(id_usuario):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar si el usuario existe antes de consultar
        cursor.execute("SELECT COUNT(*) FROM negocio.USUARIO WHERE id_usuario = ?", [id_usuario])
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.close()
            return get_dashboard_fallback(f"El usuario con ID #{id_usuario} no existe en la base de datos.")
            
        resultado = {}
        
        # 1. Obtener estadísticas del usuario y perfil
        try:
            # Intentar con negocio.fn_ObtenerPlanActivo
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM negocio.HISTORIAL_REPRODUCCION WHERE id_usuario = ?) AS canciones_escuchadas,
                    (SELECT COUNT(*) FROM negocio.ALBUM_GUARDADO WHERE id_usuario = ?) AS albumes_biblioteca,
                    CAST(ISNULL((SELECT SUM(duracion_escuchada) FROM negocio.HISTORIAL_REPRODUCCION WHERE id_usuario = ?), 0) / 3600.0 AS DECIMAL(10,1)) AS horas_reproduccion,
                    u.nombre_usuario,
                    u.email_usuario,
                    u.estado,
                    negocio.fn_ObtenerPlanActivo(?) AS plan_activo
                FROM negocio.USUARIO u
                WHERE u.id_usuario = ?
            """, [id_usuario, id_usuario, id_usuario, id_usuario, id_usuario])
        except pyodbc.Error:
            # Fallback al esquema dbo
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM negocio.HISTORIAL_REPRODUCCION WHERE id_usuario = ?) AS canciones_escuchadas,
                    (SELECT COUNT(*) FROM negocio.ALBUM_GUARDADO WHERE id_usuario = ?) AS albumes_biblioteca,
                    CAST(ISNULL((SELECT SUM(duracion_escuchada) FROM negocio.HISTORIAL_REPRODUCCION WHERE id_usuario = ?), 0) / 3600.0 AS DECIMAL(10,1)) AS horas_reproduccion,
                    u.nombre_usuario,
                    u.email_usuario,
                    u.estado,
                    dbo.fn_ObtenerPlanActivo(?) AS plan_activo
                FROM negocio.USUARIO u
                WHERE u.id_usuario = ?
            """, [id_usuario, id_usuario, id_usuario, id_usuario, id_usuario])
            
        row = cursor.fetchone()
        if row:
            cols = [col[0] for col in cursor.description]
            resultado['stats'] = dict(zip(cols, row))
        else:
            resultado['stats'] = {}
            
        # 2. Cargar álbumes guardados (biblioteca personal)
        cursor.execute("""
            SELECT TOP 5 a.titulo_album, ar.nombre_artistico, ag.fecha_guardado
            FROM negocio.ALBUM_GUARDADO ag
            JOIN catalogo.ALBUM a ON ag.id_album = a.id_album
            JOIN catalogo.ARTISTA ar ON a.id_artista = ar.id_artista
            WHERE ag.id_usuario = ?
            ORDER BY ag.fecha_guardado DESC
        """, [id_usuario])
        cols = [col[0] for col in cursor.description]
        resultado['albumes'] = [dict(zip(cols, r)) for r in cursor.fetchall()]
        
        # 3. Historial reciente
        cursor.execute("""
            SELECT TOP 10
                c.titulo_cancion,
                ar.nombre_artistico,
                FORMAT(h.fecha_hora, 'dd/MM/yyyy HH:mm') AS fecha_hora
            FROM negocio.HISTORIAL_REPRODUCCION h
            JOIN catalogo.CANCION c ON h.id_cancion = c.id_cancion
            JOIN catalogo.ARTISTA ar ON c.id_artista = ar.id_artista
            WHERE h.id_usuario = ?
            ORDER BY h.fecha_hora DESC
        """, [id_usuario])
        cols = [col[0] for col in cursor.description]
        resultado['historial_reciente'] = [dict(zip(cols, r)) for r in cursor.fetchall()]
        
        # 4. Última canción escuchada para el reproductor musical lateral (obtener_cancion_actual)
        cursor.execute("""
            SELECT TOP 1 C.titulo_cancion, A.nombre_artistico
            FROM negocio.HISTORIAL_REPRODUCCION H
            INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
            INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
            WHERE H.id_usuario = ?
            ORDER BY H.fecha_hora DESC
        """, [id_usuario])
        row = cursor.fetchone()
        if row:
            resultado['cancion_actual'] = {'cancion_actual': row[0], 'artista_actual': row[1]}
        else:
            resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
            
        # 5. Top canciones globales (sp_ReporteCanciones / query consolidada)
        cursor.execute("""
            SELECT TOP 10 
                c.id_cancion, 
                c.titulo_cancion AS Cancion, 
                a.nombre_artistico AS Artista, 
                c.duracion_seg AS Duracion, 
                c.num_reproducciones AS Reproducciones
            FROM catalogo.CANCION c
            JOIN catalogo.ARTISTA a ON c.id_artista = a.id_artista
            WHERE c.estado = 'Activo'
            ORDER BY c.num_reproducciones DESC
        """)
        cols = [col[0] for col in cursor.description]
        resultado['top_canciones'] = [dict(zip(cols, r)) for r in cursor.fetchall()]
        
        # Guardar en resultado['top10_global'] con las columnas exactas esperadas
        cursor.execute("""
            SELECT TOP 10 
                c.titulo_cancion, 
                ar.nombre_artistico, 
                c.num_reproducciones
            FROM catalogo.CANCION c
            JOIN catalogo.ARTISTA ar ON c.id_artista = ar.id_artista
            ORDER BY c.num_reproducciones DESC
        """)
        cols_t10 = [col[0] for col in cursor.description]
        resultado['top10_global'] = [dict(zip(cols_t10, r)) for r in cursor.fetchall()]
        
        # 6. Recomendaciones del motor personalizadas
        cursor.execute("""
            SELECT DISTINCT CG.id_genero
            FROM negocio.HISTORIAL_REPRODUCCION HR
            INNER JOIN catalogo.CANCION_GENERO CG ON HR.id_cancion = CG.id_cancion
            WHERE HR.id_usuario = ?
        """, [id_usuario])
        generos_escuchados = [r[0] for r in cursor.fetchall()]
        
        recomendaciones = []
        if generos_escuchados:
            placeholders = ", ".join(["?"] * len(generos_escuchados))
            cursor.execute(f"""
                WITH pool_generos AS (
                    SELECT
                        C.id_cancion,
                        C.titulo_cancion   AS Cancion,
                        A.nombre_artistico AS Artista,
                        G.nombre_genero    AS Genero,
                        C.num_reproducciones,
                        ROW_NUMBER() OVER (PARTITION BY C.id_cancion ORDER BY G.id_genero) AS rn
                    FROM catalogo.CANCION C
                    INNER JOIN catalogo.ARTISTA        A  ON C.id_artista = A.id_artista
                    INNER JOIN catalogo.CANCION_GENERO CG ON C.id_cancion  = CG.id_cancion
                    INNER JOIN catalogo.GENERO         G  ON CG.id_genero  = G.id_genero
                    WHERE CG.id_genero IN ({placeholders})
                      AND C.id_artista NOT IN (
                            SELECT DISTINCT C2.id_artista
                            FROM negocio.HISTORIAL_REPRODUCCION HR2
                            INNER JOIN catalogo.CANCION C2 ON HR2.id_cancion = C2.id_cancion
                            WHERE HR2.id_usuario = ?
                      )
                      AND C.id_artista NOT IN (
                            SELECT DISTINCT id_artista
                            FROM catalogo.CANCION
                            WHERE id_cancion IN (
                                SELECT TOP 10 id_cancion
                                FROM catalogo.CANCION
                                WHERE estado = 'Activo'
                                ORDER BY num_reproducciones DESC
                            )
                      )
                      AND C.estado = 'Activo'
                )
                SELECT TOP 5
                    Cancion,
                    Artista,
                    Genero
                FROM pool_generos
                WHERE rn = 1
                ORDER BY NEWID()
            """, *(generos_escuchados + [id_usuario]))
            cols = [col[0] for col in cursor.description]
            recomendaciones = [dict(zip(cols, r)) for r in cursor.fetchall()]
            
        if len(recomendaciones) < 5:
            ya_artistas  = {rec["Artista"] for rec in recomendaciones}
            ya_canciones = {rec["Cancion"]  for rec in recomendaciones}
            cursor.execute("""
                WITH pool_global AS (
                    SELECT
                        C.id_cancion,
                        C.titulo_cancion   AS Cancion,
                        A.nombre_artistico AS Artista,
                        G.nombre_genero    AS Genero,
                        C.num_reproducciones,
                        ROW_NUMBER() OVER (PARTITION BY C.id_cancion ORDER BY G.id_genero) AS rn
                    FROM catalogo.CANCION C
                    INNER JOIN catalogo.ARTISTA        A  ON C.id_artista = A.id_artista
                    INNER JOIN catalogo.CANCION_GENERO CG ON C.id_cancion  = CG.id_cancion
                    INNER JOIN catalogo.GENERO         G  ON CG.id_genero  = G.id_genero
                    WHERE C.id_artista NOT IN (
                            SELECT DISTINCT C2.id_artista
                            FROM negocio.HISTORIAL_REPRODUCCION HR2
                            INNER JOIN catalogo.CANCION C2 ON HR2.id_cancion = C2.id_cancion
                            WHERE HR2.id_usuario = ?
                      )
                      AND C.id_artista NOT IN (
                            SELECT DISTINCT id_artista
                            FROM catalogo.CANCION
                            WHERE id_cancion IN (
                                SELECT TOP 10 id_cancion
                                FROM catalogo.CANCION
                                WHERE estado = 'Activo'
                                ORDER BY num_reproducciones DESC
                            )
                      )
                      AND C.estado = 'Activo'
                )
                SELECT TOP 10
                    Cancion,
                    Artista,
                    Genero
                FROM pool_global
                WHERE rn = 1
                ORDER BY NEWID()
            """, [id_usuario])
            cols = [col[0] for col in cursor.description]
            complemento = [
                dict(zip(cols, r))
                for r in cursor.fetchall()
                if r[1] not in ya_artistas and r[0] not in ya_canciones
            ]
            recomendaciones = (recomendaciones + complemento)[:5]
            
        resultado['recomendaciones'] = recomendaciones
        cursor.close()
        return resultado
    except Exception as e:
        print(f"Error cargando dashboard real para usuario {id_usuario}: {e}")
        return get_dashboard_fallback(f"Error de base de datos o de conexión: {str(e)}")


def get_catalogo_completo(id_usuario, filtro_artista: str = '', filtro_genero: str = ''):
    conn = get_connection()
    cursor = conn.cursor()
    resultado = {}

    # 1. Ranking de artistas populares
    cursor.execute("""
        SELECT
            ar.nombre_artistico,
            ISNULL(ar.pais, 'Sin datos') AS pais,
            SUM(c.num_reproducciones) AS total_reproducciones
        FROM catalogo.ARTISTA ar
        JOIN catalogo.CANCION c ON ar.id_artista = c.id_artista
        GROUP BY ar.nombre_artistico, ar.pais
        ORDER BY total_reproducciones DESC
    """)
    cols = [col[0] for col in cursor.description]
    resultado['artistas'] = [dict(zip(cols, row)) for row in cursor.fetchall()]

    # 2. Lista de artistas únicos para el dropdown de filtro
    cursor.execute("""
        SELECT DISTINCT ar.nombre_artistico
        FROM catalogo.ARTISTA ar
        JOIN catalogo.CANCION c ON ar.id_artista = c.id_artista
        WHERE c.estado = 'Activo'
        ORDER BY ar.nombre_artistico
    """)
    resultado['lista_artistas'] = [row[0] for row in cursor.fetchall()]

    # 3. Lista de géneros únicos para el dropdown de filtro
    cursor.execute("SELECT nombre_genero FROM catalogo.GENERO ORDER BY nombre_genero")
    resultado['lista_generos'] = [row[0] for row in cursor.fetchall()]

    if filtro_artista or filtro_genero:
        query = """
            SELECT
                C.id_cancion AS id_cancion,
                C.titulo_cancion AS Cancion,
                A.nombre_artistico AS Artista,
                AL.titulo_album AS Album,
                C.duracion_seg AS Segundos,
                C.num_reproducciones AS Reproducciones
            FROM catalogo.CANCION C
            INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
            INNER JOIN catalogo.ALBUM AL ON C.id_album = AL.id_album
            LEFT JOIN catalogo.CANCION_GENERO CG ON C.id_cancion = CG.id_cancion
            LEFT JOIN catalogo.GENERO G ON CG.id_genero = G.id_genero
            WHERE C.estado = 'Activo'
        """
        params: List[Any] = []
        if filtro_artista:
            query += " AND A.nombre_artistico = ?"
            params.append(filtro_artista)
        if filtro_genero:
            query += " AND G.nombre_genero = ?"
            params.append(filtro_genero)
        query += """
            GROUP BY C.id_cancion, C.titulo_cancion, A.nombre_artistico,
                     AL.titulo_album, C.duracion_seg, C.num_reproducciones
            ORDER BY C.num_reproducciones DESC
        """
        cursor.execute(query, params)
    else:
        cursor.execute("""
            SELECT TOP 20
                C.id_cancion AS id_cancion,
                C.titulo_cancion AS Cancion,
                A.nombre_artistico AS Artista,
                AL.titulo_album AS Album,
                C.duracion_seg AS Segundos,
                C.num_reproducciones AS Reproducciones
            FROM catalogo.CANCION C
            INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
            INNER JOIN catalogo.ALBUM AL ON C.id_album = AL.id_album
            WHERE C.estado = 'Activo'
            ORDER BY C.num_reproducciones DESC
        """)
    cols = [col[0] for col in cursor.description]
    resultado['canciones'] = [dict(zip(cols, r)) for r in cursor.fetchall()]


    # 5. Última canción escuchada
    cursor.execute("""
        SELECT TOP 1 C.titulo_cancion, A.nombre_artistico
        FROM negocio.HISTORIAL_REPRODUCCION H
        INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
        INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
        WHERE H.id_usuario = ?
        ORDER BY H.fecha_hora DESC
    """, id_usuario)
    row = cursor.fetchone()
    if row:
        resultado['cancion_actual'] = {'cancion_actual': row[0], 'artista_actual': row[1]}
    else:
        resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}

    cursor.close()
    return resultado


def get_historial_completo(id_usuario, fecha_inicio, fecha_fin, genero):
    conn = get_connection()
    cursor = conn.cursor()
    resultado = {}
    
    # 1. Historial de reproducción con filtros
    query = """
        SELECT 
            H.fecha_hora AS FechaHora,
            C.titulo_cancion AS Cancion,
            A.nombre_artistico AS Artista,
            G.nombre_genero AS Genero,
            H.duracion_escuchada AS Segundos
        FROM negocio.HISTORIAL_REPRODUCCION H
        INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
        INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
        INNER JOIN catalogo.CANCION_GENERO CG ON C.id_cancion = CG.id_cancion
        INNER JOIN catalogo.GENERO G ON CG.id_genero = G.id_genero
        WHERE H.id_usuario = ?
    """
    params = [id_usuario]
    if fecha_inicio and fecha_fin:
        query += " AND H.fecha_hora BETWEEN ? AND ?"
        params.extend([fecha_inicio + " 00:00:00", fecha_fin + " 23:59:59"])
    elif fecha_inicio:
        query += " AND H.fecha_hora >= ?"
        params.append(fecha_inicio + " 00:00:00")
    elif fecha_fin:
        query += " AND H.fecha_hora <= ?"
        params.append(fecha_fin + " 23:59:59")
        
    if genero:
        query += " AND G.nombre_genero = ?"
        params.append(genero)
        
    query += " ORDER BY H.fecha_hora DESC"
    
    cursor.execute(query, params)
    cols = [col[0] for col in cursor.description]
    resultado['reporte_datos'] = [dict(zip(cols, r)) for r in cursor.fetchall()]
    
    # 2. Dropdown de géneros
    cursor.execute("SELECT nombre_genero FROM catalogo.GENERO ORDER BY nombre_genero")
    resultado['lista_generos'] = [row[0] for row in cursor.fetchall()]
    
    # 3. Última canción escuchada
    cursor.execute("""
        SELECT TOP 1 C.titulo_cancion, A.nombre_artistico
        FROM negocio.HISTORIAL_REPRODUCCION H
        INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
        INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
        WHERE H.id_usuario = ?
        ORDER BY H.fecha_hora DESC
    """, id_usuario)
    row = cursor.fetchone()
    if row:
        resultado['cancion_actual'] = {'cancion_actual': row[0], 'artista_actual': row[1]}
    else:
        resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
        
    cursor.close()
    return resultado


def get_suscripcion_data(id_usuario):
    conn = get_connection()
    cursor = conn.cursor()
    resultado = {}
    
    # 1. Datos de la suscripción activa
    cursor.execute("""
        SELECT TOP 1 id_suscripcion, tipo_plan, fecha_inicio, fecha_fin, estado
        FROM negocio.SUSCRIPCION
        WHERE id_usuario = ? AND estado = 'Activa'
        ORDER BY fecha_inicio DESC
    """, id_usuario)
    row = cursor.fetchone()
    if row:
        resultado['sub_actual'] = {
            'id_suscripcion': row[0],
            'tipo_plan': row[1],
            'fecha_inicio': row[2],
            'fecha_fin': row[3],
            'estado': row[4]
        }
    else:
        resultado['sub_actual'] = {'id_suscripcion': 1, 'tipo_plan': 'Premium', 'estado': 'Activa'}
        
    # 2. Última canción escuchada
    cursor.execute("""
        SELECT TOP 1 C.titulo_cancion, A.nombre_artistico
        FROM negocio.HISTORIAL_REPRODUCCION H
        INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
        INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
        WHERE H.id_usuario = ?
        ORDER BY H.fecha_hora DESC
    """, id_usuario)
    row = cursor.fetchone()
    if row:
        resultado['cancion_actual'] = {'cancion_actual': row[0], 'artista_actual': row[1]}
    else:
        resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
        
    cursor.close()
    return resultado
