from django.shortcuts import render, redirect
from django.db import connection
from plataforma.db_utils import execute_scalar, execute_stored_procedure, get_db_connection

def dashboard_usuario(request):
    id_usuario = int(request.GET.get('id_usuario', 12))
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        telefono = request.POST.get('telefono')
        pais = request.POST.get('pais')
        accion = request.POST.get('accion')
        plan = request.POST.get('plan', 'Gratuito')
        
        with connection.cursor() as cursor:
            if accion == 'CREATE':
                cursor.execute(
                    "INSERT INTO negocio.USUARIO (id_rol, nombre_usuario, email_usuario, contrasena, telefono, pais, estado) VALUES (%s, %s, %s, 'hash_default123', %s, %s, 'Activo')",
                    [4 if plan == 'Premium' else 3, nombre, email, telefono or '', pais]
                )
                if plan == 'Premium':
                    cursor.execute("SELECT @@IDENTITY")
                    nuevo_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO negocio.SUSCRIPCION (id_usuario, tipo_plan, fecha_inicio, fecha_fin, estado) VALUES (%s, 'Premium', GETDATE(), DATEADD(YEAR, 1, GETDATE()), 'Activa')",
                        [nuevo_id]
                    )
            else:
                cursor.execute(
                    "EXEC negocio.usp_RegistrarModificarUsuario @id_usuario = %s, @nombre = %s, @email = %s, @telefono = %s, @pais = %s, @accion = %s",
                    [id_usuario, nombre, email, telefono, pais, accion]
                )
            connection.commit()
        return redirect('dashboard')

    with connection.cursor() as cursor:
        cursor.execute("SELECT nombre_usuario, email_usuario, telefono, pais, estado FROM negocio.USUARIO WHERE id_usuario = %s", [id_usuario])
        row = cursor.fetchone()
        if row:
            datos_usuario = {
                'nombre': row[0],
                'email': row[1],
                'telefono': row[2] or '',
                'pais': row[3] or '',
                'estado': row[4]
            }
        else:
            datos_usuario = None

    with connection.cursor() as cursor:
        cursor.execute("SELECT negocio.fn_ObtenerPlanActivo(12)")
        plan_actual = cursor.fetchone()[0]

    albumes_guardados = execute_stored_procedure("negocio.sp_ReporteAlbumesGuardados", [id_usuario])
    albumes_tuplas = [tuple(album.values()) for album in albumes_guardados]
    historial_usuario = execute_stored_procedure("negocio.sp_ReporteHistorialUsuario", [id_usuario])
    historial_tuplas = [tuple(item.values()) for item in historial_usuario]
    canciones_global = execute_stored_procedure("negocio.sp_ReporteCanciones")

    recomendaciones = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT CG.id_genero
                FROM negocio.HISTORIAL_REPRODUCCION HR
                INNER JOIN catalogo.CANCION_GENERO CG ON HR.id_cancion = CG.id_cancion
                WHERE HR.id_usuario = ?
                """,
                [id_usuario]
            )
            generos_escuchados = [row[0] for row in cur.fetchall()]

        if generos_escuchados:
            placeholders = ", ".join(["?"] * len(generos_escuchados))
            with conn.cursor() as cur:
                cur.execute(
                    f"""
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
                    """,
                    generos_escuchados + [id_usuario]
                )
                cols = [col[0] for col in cur.description]
                recomendaciones = [dict(zip(cols, row)) for row in cur.fetchall()]

        if len(recomendaciones) < 5:
            ya_artistas  = {rec["Artista"] for rec in recomendaciones}
            ya_canciones = {rec["Cancion"]  for rec in recomendaciones}
            with conn.cursor() as cur:
                cur.execute(
                    """
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
                    """,
                    [id_usuario]
                )
                cols = [col[0] for col in cur.description]
                complemento = [
                    dict(zip(cols, row))
                    for row in cur.fetchall()
                    if row[1] not in ya_artistas and row[0] not in ya_canciones
                ]
            recomendaciones = (recomendaciones + complemento)[:5]

    contexto = {
        'id_usuario': id_usuario,
        'plan': plan_actual,
        'albumes': albumes_tuplas,
        'historial': historial_tuplas,
        'top_canciones': canciones_global,
        'recomendaciones': recomendaciones,
        'datos_usuario': datos_usuario,
    }
    return render(request, 'plataforma/dashboard.html', contexto)

def procesar_suscripcion(request):
    if request.method == 'POST':
        metodo = request.POST.get('metodo_pago')
        estado_tx = request.POST.get('estado_transaccion')
        if estado_tx == 'Aprobar Renovación' or estado_tx == 'Completado':
            estado_pago = 'Completado'
        else:
            estado_pago = 'Fallido'
        cursor = connection.cursor()
        cursor.execute("EXEC negocio.sp_ProcesarRenovacion @id_suscripcion = 1, @estado_pago = %s, @metodo = %s", [estado_pago, metodo])
        connection.commit()
        return redirect('dashboard')
    return render(request, 'plataforma/suscripcion.html')

def catalogo_artistas(request):
    lista_artistas = execute_stored_procedure("negocio.sp_ReporteArtistasPopulares")
    return render(request, 'plataforma/catalogo.html', {'artistas': lista_artistas})

def historial_reproduccion(request):
    id_usuario = int(request.GET.get('id_usuario', 12))
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    genero = request.GET.get('genero', '')

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

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            cols = [col[0] for col in cur.description]
            reporte_datos = [dict(zip(cols, row)) for row in cur.fetchall()]

        with conn.cursor() as cur:
            cur.execute("SELECT nombre_genero FROM catalogo.GENERO ORDER BY nombre_genero")
            lista_generos = [row[0] for row in cur.fetchall()]

    contexto = {
        'id_usuario': id_usuario,
        'reporte_datos': reporte_datos,
        'lista_generos': lista_generos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'genero_seleccionado': genero,
    }
    return render(request, 'plataforma/historial.html', contexto)
