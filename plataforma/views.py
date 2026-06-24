from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
import pyodbc
from plataforma.db_utils import (
    execute_scalar, execute_stored_procedure, get_db_connection, get_connection, 
    get_catalogo_completo, get_historial_completo, 
    get_suscripcion_data, close_connection, eliminar_usuario_bd
)
from plataforma.fase7_mongo_db_utils import (
    get_mongo_db,
    validar_credenciales_mongo,
    get_dashboard_data,
    crear_artista_sp,
    actualizar_artista_sp,
    eliminar_artista_sp,
    crear_album_sp,
    actualizar_album_sp,
    eliminar_album_sp,
    crear_cancion_sp,
    actualizar_cancion_sp,
    eliminar_cancion_sp,
    get_detalle_artista_mongo,
    get_detalle_album_mongo,
    get_detalle_playlist_mongo,
    generar_reporte_mongo
)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime, date

def get_usuario_activo():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM negocio.USUARIO WHERE id_usuario = 12")
        exists = cursor.fetchone()[0]
        if exists:
            cursor.close()
            return 12
        cursor.execute("SELECT TOP 1 id_usuario FROM negocio.USUARIO ORDER BY id_usuario")
        row = cursor.fetchone()
        cursor.close()
        if row:
            return row[0]
    except Exception:
        pass
    return 12

def eliminar_usuario(request):
    if request.method == 'POST':
        try:
            id_a_eliminar = int(request.POST.get('id_usuario'))
        except (ValueError, TypeError):
            messages.error(request, 'ID de usuario inválido.')
            return redirect('dashboard')
        usuario_activo = get_usuario_activo()
        if id_a_eliminar == usuario_activo:
            messages.error(request, 
                'No puedes eliminar el usuario activo de la plataforma. '
                'Selecciona otro usuario para eliminar.')
            return redirect('dashboard')
        try:
            eliminar_usuario_bd(id_a_eliminar)
            messages.success(request, 'Usuario eliminado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {e}')
        return redirect('dashboard')
    return redirect('dashboard')

def dashboard_usuario(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    try:
        db_data = get_dashboard_data(id_usuario)
        stats = db_data.get('stats', {})
        if stats:
            datos_usuario = {
                'nombre': stats.get('nombre_usuario', ''),
                'email': stats.get('email_usuario', ''),
                'telefono': '',
                'pais': '',
                'estado': stats.get('estado', '')
            }
            plan_actual = stats.get('plan_active') or stats.get('plan_activo') or 'Gratuito'
            canciones_escuchadas = stats.get('canciones_escuchadas', 0) or 0
            albumes_conteo = stats.get('albumes_biblioteca', 0) or 0
            horas_reproduccion = float(stats.get('horas_reproduccion', 0.0) or 0.0)
        else:
            datos_usuario = None
            plan_actual = 'Gratuito'
            canciones_escuchadas = 0
            albumes_conteo = 0
            horas_reproduccion = 0.0
        albumes_tuplas = [
            (
                r.get('titulo_album', ''),
                r.get('titulo_album', ''),
                r.get('nombre_artistico', ''),
                r.get('fecha_guardado').strftime('%d/%m/%Y %H:%M') if r.get('fecha_guardado') else ''
            )
            for r in db_data.get('albumes', [])
        ]
        historial_tuplas = [
            (
                stats.get('nombre_usuario', ''),
                r.get('titulo_cancion', ''),
                r.get('nombre_artistico', ''),
                ''
            )
            for r in db_data.get('historial_reciente', [])
        ]
        canciones_global = [
            (
                r.get('id_cancion', 0),
                r.get('Cancion', ''),
                r.get('Artista', ''),
                r.get('Duracion', 0),
                r.get('Reproducciones', 0)
            )
            for r in db_data.get('top_canciones', [])
        ]
        recomendaciones = db_data.get('recomendaciones', [])
        player_info = db_data.get('cancion_actual', {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'})
    except Exception as e:
        raise e
    contexto = {
        'id_usuario': id_usuario,
        'plan': plan_actual,
        'albumes': albumes_tuplas,
        'historial': historial_tuplas,
        'top_canciones': canciones_global,
        'recomendaciones': recomendaciones,
        'datos_usuario': datos_usuario,
        'canciones_escuchadas': canciones_escuchadas,
        'albumes_conteo': albumes_conteo,
        'horas_reproduccion': horas_reproduccion,
        'cancion_actual': player_info['cancion_actual'],
        'artista_actual': player_info['artista_actual'],
        'error': db_data.get('error'),
        'datos': db_data,
    }
    return render(request, 'plataforma/dashboard.html', contexto)

def procesar_suscripcion(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    id_suscripcion = 1
    resultado_transaccion = None
    if request.method == 'POST':
        metodo = request.POST.get('metodo_pago', 'Tarjeta Credito')
        estado_tx = request.POST.get('estado_transaccion')
        estado_pago = 'Completado' if estado_tx == 'Completado' else 'Fallido'
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "EXEC negocio.sp_ProcesarRenovacion ?, ?",
                [id_suscripcion, estado_pago]
            )
            conn.commit()
            cursor.close()
            close_connection()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_plan, FORMAT(fecha_fin, 'dd/MM/yyyy'), estado FROM negocio.SUSCRIPCION WHERE id_suscripcion = ?", [id_suscripcion])
            row_res = cursor.fetchone()
            cursor.close()
            close_connection()
            if row_res:
                resultado_transaccion = {
                    'plan': row_res[0],
                    'fecha_fin': row_res[1] if row_res[1] else 'Indefinida',
                    'estado': row_res[2],
                    'exito': estado_pago == 'Completado'
                }
                if estado_pago == 'Completado':
                    messages.success(request, f"¡Transacción exitosa! Tu suscripción Premium ha sido renovada hasta el {resultado_transaccion['fecha_fin']}.")
                else:
                    messages.warning(request, "Transacción declinada. Tu suscripción se encuentra ahora en estado 'Vencida'.")
        except Exception as e:
            messages.error(request, f"Error al procesar renovación: {e}")
        finally:
            close_connection()
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 
                s.id_suscripcion,
                s.tipo_plan,
                s.fecha_inicio,
                s.fecha_fin,
                s.estado,
                dbo.fn_ObtenerPlanActivo(s.id_usuario) AS plan_activo
            FROM negocio.SUSCRIPCION s
            WHERE s.id_usuario = ?
            ORDER BY s.fecha_inicio DESC
        """, [id_usuario])
        row = cursor.fetchone()
        cursor.close()
        close_connection()
    except Exception as e:
        row = None
        print(f"Error al leer suscripción: {e}")
    finally:
        close_connection()
    suscripcion = {}
    if row:
        suscripcion = {
            'id_suscripcion': row[0],
            'tipo_plan': row[1],
            'plan': row[1],
            'fecha_fin': row[3].strftime('%d/%m/%Y') if row[3] else 'Indefinida',
            'estado': row[4],
            'plan_activo': row[5]
        }
    else:
        suscripcion = {
            'id_suscripcion': 1,
            'tipo_plan': 'Gratuito',
            'plan': 'Gratuito',
            'fecha_fin': 'Indefinida',
            'estado': 'Inactiva',
            'plan_activo': 'Gratuito'
        }
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 C.titulo_cancion, A.nombre_artistico
            FROM negocio.HISTORIAL_REPRODUCCION H
            INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
            INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
            WHERE H.id_usuario = ?
            ORDER BY H.fecha_hora DESC
        """, [id_usuario])
        row_player = cursor.fetchone()
        cursor.close()
        close_connection()
        if row_player:
            player_info = {'cancion_actual': row_player[0], 'artista_actual': row_player[1]}
    except Exception:
        pass
    finally:
        close_connection()
    contexto = {
        'id_usuario': id_usuario,
        'suscripcion': suscripcion,
        'sub_actual': suscripcion,
        'resultado_transaccion': resultado_transaccion,
        'cancion_actual': player_info['cancion_actual'],
        'artista_actual': player_info['artista_actual'],
    }
    return render(request, 'plataforma/suscripcion.html', contexto)

def catalogo_artistas(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    filtro_artista = request.GET.get('filtro_artista', '').strip()
    filtro_genero = request.GET.get('filtro_genero', '').strip()
    lista_artistas = []
    lista_canciones = []
    lista_artistas_dropdown = []
    lista_generos_dropdown = []
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    try:
        db_data = get_catalogo_completo(id_usuario, filtro_artista, filtro_genero)
        lista_artistas = db_data.get('artistas', [])
        lista_artistas_dropdown = db_data.get('lista_artistas', [])
        lista_generos_dropdown = db_data.get('lista_generos', [])
        raw_songs = db_data.get('canciones', [])
        player_info = db_data.get('cancion_actual', player_info)
        for s in raw_songs:
            minutos = s['Segundos'] // 60
            segundos = s['Segundos'] % 60
            s['DuracionFormateada'] = f"{minutos}:{segundos:02d}"
            lista_canciones.append(s)
    except Exception as e:
        print(f"Error al cargar catálogo completo: {e}")
    finally:
        close_connection()
    contexto = {
        'id_usuario': id_usuario,
        'artistas': lista_artistas,
        'canciones': lista_canciones,
        'lista_artistas_dropdown': lista_artistas_dropdown,
        'lista_generos_dropdown': lista_generos_dropdown,
        'filtro_artista': filtro_artista,
        'filtro_genero': filtro_genero,
        'cancion_actual': player_info['cancion_actual'],
        'artista_actual': player_info['artista_actual'],
    }
    return render(request, 'plataforma/catalogo.html', contexto)

def reproducir_cancion(request, id_cancion):
    id_usuario = get_usuario_activo()
    try:
        query_cancion = """
            SELECT C.titulo_cancion, A.nombre_artistico, C.duracion_seg
            FROM catalogo.CANCION C
            INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
            WHERE C.id_cancion = ?
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query_cancion, [id_cancion])
                row = cur.fetchone()
                if not row:
                    return JsonResponse({'success': False, 'error': 'Canción no encontrada'}, status=404)
                titulo, artista, duracion = row[0], row[1], row[2]
                cur.execute("EXEC negocio.sp_RegistrarReproduccion ?, ?, ?", [id_usuario, id_cancion, duracion])
                conn.commit()
                cur.execute("SELECT num_reproducciones FROM catalogo.CANCION WHERE id_cancion = ?", [id_cancion])
                nuevas_reproducciones = cur.fetchone()[0]
        return JsonResponse({
            'success': True,
            'titulo': titulo,
            'artista': artista,
            'reproducciones': nuevas_reproducciones
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    finally:
        close_connection()

def historial_reproduccion(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    genero = request.GET.get('genero', '')
    reporte_datos = []
    lista_generos = []
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    try:
        db_data = get_historial_completo(id_usuario, fecha_inicio, fecha_fin, genero)
        raw_data = db_data.get('reporte_datos', [])
        lista_generos = db_data.get('lista_generos', [])
        player_info = db_data.get('cancion_actual', player_info)
        for item in raw_data:
            minutos = item['Segundos'] // 60
            segundos = item['Segundos'] % 60
            item['DuracionFormateada'] = f"{minutos}:{segundos:02d}"
            reporte_datos.append(item)
    except Exception as e:
        messages.error(request, f"Error al cargar el historial de reproducciones: {e}")
    finally:
        close_connection()
    contexto = {
        'id_usuario': id_usuario,
        'reporte_datos': reporte_datos,
        'lista_generos': lista_generos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'genero_seleccionado': genero,
        'cancion_actual': player_info['cancion_actual'],
        'artista_actual': player_info['artista_actual'],
    }
    return render(request, 'plataforma/historial.html', contexto)

def exportar_historial_pdf(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
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
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                cols = [col[0] for col in cur.description]
                datos = [dict(zip(cols, row)) for row in cur.fetchall()]
                cur.execute("SELECT nombre_usuario FROM negocio.USUARIO WHERE id_usuario = ?", [id_usuario])
                user_row = cur.fetchone()
                nombre_usuario = user_row[0] if user_row else f"Usuario #{id_usuario}"
    except Exception as e:
        return HttpResponse(f"Error de base de datos al generar PDF: {e}", status=500)
    finally:
        close_connection()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="historial_reproduccion_{id_usuario}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#c9a84c'),
        spaceAfter=20
    )
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#1a1a1a')
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#ffffff')
    )
    story.append(Paragraph("SoundWave - Reporte de Reproducciones", title_style))
    filtro_info = f"Oyente: {nombre_usuario} | ID #{id_usuario}"
    if fecha_inicio or fecha_fin or genero:
        filtro_info += " | Filtros - "
        if fecha_inicio: filtro_info += f"Desde: {fecha_inicio} "
        if fecha_fin: filtro_info += f"Hasta: {fecha_fin} "
        if genero: filtro_info += f"Género: {genero}"
    story.append(Paragraph(filtro_info, subtitle_style))
    story.append(Spacer(1, 10))
    table_data = [[
        Paragraph("Fecha/Hora", header_style),
        Paragraph("Canción", header_style),
        Paragraph("Artista", header_style),
        Paragraph("Género", header_style),
        Paragraph("Duración", header_style)
    ]]
    for row in datos:
        duracion_min = f"{row['Segundos'] // 60}:{row['Segundos'] % 60:02d}"
        table_data.append([
            Paragraph(row['FechaHora'].strftime('%d/%m/%Y %H:%M') if row['FechaHora'] else '', normal_style),
            Paragraph(row['Cancion'] or '', normal_style),
            Paragraph(row['Artista'] or '', normal_style),
            Paragraph(row['Genero'] or '', normal_style),
            Paragraph(duracion_min, normal_style)
        ])
    t = Table(table_data, colWidths=[120, 140, 110, 80, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f0e8'), colors.HexColor('#ffffff')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c9a84c')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    doc.build(story)
    return response

def administracion(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 C.titulo_cancion, A.nombre_artistico
            FROM negocio.HISTORIAL_REPRODUCCION H
            INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
            INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
            WHERE H.id_usuario = ?
            ORDER BY H.fecha_hora DESC
        """, [id_usuario])
        row_player = cursor.fetchone()
        cursor.close()
        close_connection()
        if row_player:
            player_info = {'cancion_actual': row_player[0], 'artista_actual': row_player[1]}
    except Exception:
        pass
    finally:
        close_connection()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id_usuario, u.nombre_usuario, u.email_usuario,
               u.estado, r.nombre_rol,
               dbo.fn_ObtenerPlanActivo(u.id_usuario) AS plan_activo,
               FORMAT(u.fecha_registro, 'dd/MM/yyyy') AS fecha_registro
        FROM negocio.USUARIO u
        JOIN negocio.ROL r ON u.id_rol = r.id_rol
        WHERE r.nombre_rol IN ('Oyente', 'Premium')
        ORDER BY u.id_usuario DESC
    """)
    cols = [col[0] for col in cursor.description]
    oyentes = [dict(zip(cols, r)) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT 
            u.id_usuario, u.nombre_usuario, u.email_usuario,
            u.estado, FORMAT(u.fecha_registro, 'dd/MM/yyyy') AS fecha_registro,
            ar.nombre_artistico, ar.pais,
            (SELECT COUNT(*) FROM catalogo.ALBUM al WHERE al.id_artista = ar.id_artista) AS total_albumes,
            (SELECT COUNT(*) FROM catalogo.CANCION c WHERE c.id_artista = ar.id_artista) AS total_canciones,
            (SELECT ISNULL(SUM(c2.num_reproducciones),0) FROM catalogo.CANCION c2 WHERE c2.id_artista = ar.id_artista) AS total_reproducciones
        FROM negocio.USUARIO u
        JOIN negocio.ROL r ON u.id_rol = r.id_rol
        JOIN catalogo.ARTISTA ar ON ar.id_usuario = u.id_usuario
        WHERE r.nombre_rol = 'Artista'
        ORDER BY total_reproducciones DESC
    """)
    cols2 = [col[0] for col in cursor.description]
    artistas = [dict(zip(cols2, r)) for r in cursor.fetchall()]
    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM negocio.USUARIO) AS total_usuarios,
            (SELECT COUNT(*) FROM catalogo.CANCION) AS total_canciones,
            (SELECT COUNT(*) FROM catalogo.ALBUM) AS total_albumes,
            (SELECT COUNT(*) FROM negocio.HISTORIAL_REPRODUCCION) AS total_reproducciones,
            (SELECT COUNT(*) FROM negocio.SUSCRIPCION WHERE estado='Activa') AS suscripciones_activas,
            (SELECT ISNULL(SUM(monto_calculado),0) FROM negocio.REGALIAS) AS total_regalias
    """)
    row = cursor.fetchone()
    cols3 = [col[0] for col in cursor.description]
    sistema_stats = dict(zip(cols3, row))
    cursor.close()
    close_connection()
    contexto = {
        'id_usuario': id_usuario,
        'oyentes': oyentes,
        'artistas': artistas,
        'sistema_stats': sistema_stats,
        'cancion_actual': player_info['cancion_actual'],
        'artista_actual': player_info['artista_actual'],
    }
    return render(request, 'plataforma/administracion.html', contexto)

def crear_oyente(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        nombre = request.POST.get('nombre_usuario', '').strip()
        email = request.POST.get('email_usuario', '').strip()
        pais = request.POST.get('pais', '').strip()
        plan = request.POST.get('plan', 'Gratuito')
        estado = 'Activo'
        email_exists = execute_scalar("SELECT COUNT(*) FROM negocio.USUARIO WHERE email_usuario = ?", [email])
        if email_exists > 0:
            messages.error(request, f"Error: El correo electrónico '{email}' ya se encuentra registrado.")
            return redirect(f'/administracion/?id_usuario={id_usuario}')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            id_rol = 4 if plan == 'Premium' else 3
            cursor.execute("""
                INSERT INTO negocio.USUARIO 
                    (id_rol, nombre_usuario, email_usuario, contrasena, pais, fecha_registro, estado)
                VALUES (?, ?, ?, ?, ?, GETDATE(), ?)
            """, id_rol, nombre, email, f'hash_{nombre.lower().replace(" ","")}', pais or None, estado)
            if plan == 'Premium':
                cursor.execute("SELECT @@IDENTITY")
                nuevo_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO negocio.SUSCRIPCION (id_usuario, tipo_plan, fecha_inicio, fecha_fin, estado)
                    VALUES (?, 'Premium', GETDATE(), DATEADD(YEAR, 1, GETDATE()), 'Activa')
                """, nuevo_id)
            conn.commit()
            cursor.close()
            close_connection()
            messages.success(request, f'Oyente {nombre} registrado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al registrar: {e}')
        finally:
            close_connection()
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def editar_oyente(request, id_usuario):
    id_activo = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        nombre = request.POST.get('nombre_usuario', '').strip()
        email = request.POST.get('email_usuario', '').strip()
        estado = request.POST.get('estado', 'Activo')
        email_exists = execute_scalar("SELECT COUNT(*) FROM negocio.USUARIO WHERE email_usuario = ? AND id_usuario != ?", [email, id_usuario])
        if email_exists > 0:
            messages.error(request, f"Error al editar perfil: El correo electrónico '{email}' ya está en uso por otro usuario.")
            return redirect(f'/administracion/?id_usuario={id_activo}')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE negocio.USUARIO 
                SET nombre_usuario=?, email_usuario=?, estado=?
                WHERE id_usuario=?
            """, nombre, email, estado, id_usuario)
            conn.commit()
            cursor.close()
            close_connection()
            messages.success(request, 'Usuario actualizado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {e}')
        finally:
            close_connection()
    return redirect(f'/administracion/?id_usuario={id_activo}')

def eliminar_oyente(request, id_usuario):
    id_activo = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        if int(id_usuario) == 12:
            messages.error(request, 'No se puede eliminar el usuario principal del sistema.')
            return redirect(f'/administracion/?id_usuario={id_activo}')
        try:
            eliminar_usuario_bd(id_usuario)
            messages.success(request, 'Usuario eliminado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {e}')
    return redirect(f'/administracion/?id_usuario={id_activo}')

def landing_or_dashboard(request):
    if request.session.get('id_usuario'):
        return dashboard_usuario(request)
    return render(request, 'plataforma/landing.html')

def login_view(request):
    error = None
    plan = request.GET.get('plan', '')
    if plan:
        request.session['plan_seleccionado'] = plan
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        contrasena = request.POST.get('contrasena', '').strip()
        res = validar_credenciales_mongo(email, contrasena)
        if res:
            request.session['id_usuario'] = res['id_usuario']
            request.session['nombre_usuario'] = res['nombre_usuario']
            request.session['rol'] = res['rol']
            request.session['plan'] = res['plan']
            return redirect('dashboard')
        else:
            error = "Credenciales incorrectas o usuario inactivo."
    return render(request, 'plataforma/login.html', {'error': error, 'plan': plan})

def logout_view(request):
    request.session.flush()
    return redirect('login')

def ajustes(request):
    id_usuario = request.session.get('id_usuario')
    if not id_usuario:
        return redirect('login')
    db = get_mongo_db()
    user = db.usuarios.find_one({"id_usuario": int(id_usuario)})
    if not user:
        return redirect('login')
    success = None
    error = None
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        contrasena = request.POST.get('contrasena', '').strip()
        if not nombre or not email:
            error = "El nombre y el correo son obligatorios."
        else:
            existing = db.usuarios.find_one({"email_usuario": email, "id_usuario": {"$ne": int(id_usuario)}})
            if existing:
                error = "El correo ya está registrado por otro usuario."
            else:
                update_fields = {
                    "nombre_usuario": nombre,
                    "email_usuario": email
                }
                if contrasena:
                    update_fields["contrasena"] = contrasena if contrasena.startswith("hash_") else f"hash_{contrasena}"
                db.usuarios.update_one(
                    {"id_usuario": int(id_usuario)},
                    {"$set": update_fields}
                )
                db.playlists.update_many(
                    {"usuario.id_usuario": int(id_usuario)},
                    {"$set": {"usuario.nombre_usuario": nombre}}
                )
                db.reproducciones.update_many(
                    {"usuario.id_usuario": int(id_usuario)},
                    {"$set": {
                        "usuario.nombre_usuario": nombre,
                        "usuario.email_usuario": email
                    }}
                )
                request.session['nombre_usuario'] = nombre
                success = "Ajustes actualizados correctamente."
                user = db.usuarios.find_one({"id_usuario": int(id_usuario)})
    user_data = {
        'nombre': user.get('nombre_usuario', ''),
        'email': user.get('email_usuario', ''),
        'contrasena': user.get('contrasena', '').replace('hash_', '') if user.get('contrasena') else ''
    }
    cancion_actual = 'Shape of You'
    artista_actual = 'Ed Sheeran'
    try:
        latest_play = db.reproducciones.find_one({"usuario.id_usuario": int(id_usuario)}, sort=[("fecha_hora", -1)])
        if latest_play:
            cancion_actual = latest_play.get('cancion', {}).get('titulo_cancion', cancion_actual)
            artista_actual = latest_play.get('artista', {}).get('nombre_artistico', artista_actual)
    except Exception:
        pass
    contexto = {
        'user_data': user_data,
        'success': success,
        'error': error,
        'cancion_actual': cancion_actual,
        'artista_actual': artista_actual,
    }
    return render(request, 'plataforma/ajustes.html', contexto)

def crear_artista(request):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        nombre_artistico = request.POST.get('nombre_artistico', '').strip()
        email = request.POST.get('email', '').strip()
        pais = request.POST.get('pais', '').strip()
        genero_musical = request.POST.get('genero_musical', '').strip()
        biografia = request.POST.get('biografia', '').strip()
        try:
            crear_artista_sp(nombre_artistico, email, pais, genero_musical or None, biografia or None)
            messages.success(request, f"Artista '{nombre_artistico}' creado correctamente en MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al crear artista: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def editar_artista(request, id_artista):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        nombre_artistico = request.POST.get('nombre_artistico', '').strip()
        pais = request.POST.get('pais', '').strip()
        genero_musical = request.POST.get('genero_musical', '').strip()
        biografia = request.POST.get('biografia', '').strip()
        estado = request.POST.get('estado', 'Activo').strip()
        try:
            actualizar_artista_sp(id_artista, nombre_artistico, pais, genero_musical or None, biografia or None, estado or None)
            messages.success(request, f"Artista ID {id_artista} actualizado correctamente en MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al editar artista: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def eliminar_artista(request, id_artista):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        try:
            eliminar_artista_sp(id_artista)
            messages.success(request, f"Artista ID {id_artista} eliminado correctamente de MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al eliminar artista: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def crear_album(request):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        try:
            id_artista = int(request.POST.get('id_artista'))
        except (ValueError, TypeError):
            messages.error(request, "ID de artista invalido.")
            return redirect(f'/administracion/?id_usuario={id_usuario}')
        titulo_album = request.POST.get('titulo_album', '').strip()
        fecha_lanzamiento = request.POST.get('fecha_lanzamiento', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        try:
            crear_album_sp(id_artista, titulo_album, fecha_lanzamiento or None, descripcion or None)
            messages.success(request, f"Album '{titulo_album}' creado correctamente en MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al crear album: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def editar_album(request, id_album):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        titulo_album = request.POST.get('titulo_album', '').strip()
        fecha_lanzamiento = request.POST.get('fecha_lanzamiento', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        try:
            actualizar_album_sp(id_album, titulo_album, fecha_lanzamiento or None, descripcion or None)
            messages.success(request, f"Album ID {id_album} actualizado correctamente en MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al editar album: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def eliminar_album(request, id_album):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        try:
            eliminar_album_sp(id_album)
            messages.success(request, f"Album ID {id_album} eliminado correctamente de MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al eliminar album: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def crear_cancion(request):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        try:
            id_album = int(request.POST.get('id_album'))
        except (ValueError, TypeError):
            messages.error(request, "ID de album invalido.")
            return redirect(f'/administracion/?id_usuario={id_usuario}')
        titulo_cancion = request.POST.get('titulo_cancion', '').strip()
        try:
            duracion_seg = int(request.POST.get('duracion_seg', 0))
        except (ValueError, TypeError):
            duracion_seg = 0
        genero_musical = request.POST.get('genero_musical', '').strip()
        try:
            crear_cancion_sp(id_album, titulo_cancion, duracion_seg, genero_musical or None)
            messages.success(request, f"Cancion '{titulo_cancion}' creada correctamente en MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al crear cancion: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def editar_cancion(request, id_cancion):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        titulo_cancion = request.POST.get('titulo_cancion', '').strip()
        try:
            duracion_seg = int(request.POST.get('duracion_seg', 0))
        except (ValueError, TypeError):
            duracion_seg = 0
        genero_musical = request.POST.get('genero_musical', '').strip()
        try:
            actualizar_cancion_sp(id_cancion, titulo_cancion, duracion_seg, genero_musical or None)
            messages.success(request, f"Cancion ID {id_cancion} actualizada correctamente en MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al editar cancion: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def eliminar_cancion(request, id_cancion):
    if request.session.get('rol') != 'Administrador' or not request.session.get('modo_desarrollador_activo'):
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard')
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        try:
            eliminar_cancion_sp(id_cancion)
            messages.success(request, f"Cancion ID {id_cancion} eliminada correctamente de MongoDB.")
        except Exception as e:
            messages.error(request, f"Error al eliminar cancion: {e}")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def detalle_artista(request, id_artista):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    res = get_detalle_artista_mongo(id_artista, id_usuario)
    if not res:
        return redirect('dashboard')
    contexto = {
        'id_usuario': id_usuario,
        'artista': res['artista'],
        'albumes': res['albumes'],
        'cancion_actual': res['player_info']['cancion_actual'],
        'artista_actual': res['player_info']['artista_actual']
    }
    return render(request, 'plataforma/detalle_artista.html', contexto)

def detalle_album(request, id_album):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    res = get_detalle_album_mongo(id_album, id_usuario)
    if not res:
        return redirect('dashboard')
    contexto = {
        'id_usuario': id_usuario,
        'album': res['album'],
        'canciones': res['canciones'],
        'cancion_actual': res['player_info']['cancion_actual'],
        'artista_actual': res['player_info']['artista_actual']
    }
    return render(request, 'plataforma/detalle_album.html', contexto)

def detalle_playlist(request, id_playlist):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    res = get_detalle_playlist_mongo(id_playlist, id_usuario)
    if not res:
        return redirect('dashboard')
    contexto = {
        'id_usuario': id_usuario,
        'playlist': res['playlist'],
        'canciones': res['canciones'],
        'cancion_actual': res['player_info']['cancion_actual'],
        'artista_actual': res['player_info']['artista_actual']
    }
    return render(request, 'plataforma/detalle_playlist.html', contexto)

def informacion(request):
    id_usuario = request.session.get('id_usuario') or get_usuario_activo()
    cancion_actual = 'Shape of You'
    artista_actual = 'Ed Sheeran'
    try:
        db = get_mongo_db()
        latest_play = db.reproducciones.find_one({"usuario.id_usuario": int(id_usuario)}, sort=[("fecha_hora", -1)])
        if latest_play:
            cancion_actual = latest_play.get('cancion', {}).get('titulo_cancion', cancion_actual)
            artista_actual = latest_play.get('artista', {}).get('nombre_artistico', artista_actual)
    except Exception:
        pass
    contexto = {
        'cancion_actual': cancion_actual,
        'artista_actual': artista_actual
    }
    return render(request, 'plataforma/informacion.html', contexto)

def planes(request):
    return render(request, 'plataforma/planes.html')

def registro_view(request):
    return render(request, 'plataforma/registro.html')

def soporte(request):
    return render(request, 'plataforma/soporte.html')

def terminos_condiciones(request):
    return render(request, 'plataforma/terminos_condiciones.html')

def verificacion_estudiantil(request):
    if request.method == 'POST':
        return redirect('/login/?plan=estudiante')
    return render(request, 'plataforma/verificacion_estudiantil.html')

def verificacion_telefono(request):
    return render(request, 'plataforma/verificacion_telefono.html')

def verificar_admin(request):
    id_usuario = int(request.GET.get('id_usuario', get_usuario_activo()))
    if request.method == 'POST':
        contrasena = request.POST.get('password', '').strip()
        res = validar_credenciales_mongo('admin@soundwave.ec', contrasena)
        if res:
            request.session['modo_desarrollador_activo'] = True
            request.session['modo_desarrollador'] = True
            messages.success(request, "Modo desarrollador activado correctamente.")
        else:
            messages.error(request, "Contrasena de administrador incorrecta.")
    return redirect(f'/administracion/?id_usuario={id_usuario}')

def reportes(request):
    db = get_mongo_db()
    artistas_list = []
    for art in db.artistas.find({"estado": "Activo"}).sort("nombre_artistico", 1):
        artistas_list.append({
            'id': art.get('id_artista'),
            'nombre': art.get('nombre_artistico')
        })
    usuarios_list = []
    for usr in db.usuarios.find({"estado": "Activo"}).sort("nombre_usuario", 1):
        usuarios_list.append({
            'id': usr.get('id_usuario'),
            'nombre': usr.get('nombre_usuario')
        })
    report_id = request.GET.get('report_id')
    export = request.GET.get('export')
    contexto = {
        'artistas_list': artistas_list,
        'usuarios_list': usuarios_list,
        'report_id': report_id,
        'param_artista': int(request.GET.get('artista_id')) if request.GET.get('artista_id') else None,
        'param_usuario': int(request.GET.get('usuario_id')) if request.GET.get('usuario_id') else None,
        'param_fecha_inicio': request.GET.get('fecha_inicio'),
        'param_fecha_fin': request.GET.get('fecha_fin'),
        'error_msg': None,
        'report_title': "",
        'cols': [],
        'rows': []
    }
    if report_id:
        try:
            param_art = request.GET.get('artista_id')
            param_usr = request.GET.get('usuario_id')
            f_inicio = request.GET.get('fecha_inicio')
            f_fin = request.GET.get('fecha_fin')
            if report_id == 'usuario_completo':
                title = "Reporte Completo de Usuarios"
                cols = ["ID Usuario", "Nombre", "Email", "Rol", "Estado", "Plan Activo"]
                rows = []
                for u in db.usuarios.find().sort("id_usuario", 1):
                    sub = u.get("suscripcion_activa")
                    plan_act = "Gratuito"
                    if sub and sub.get("estado") == "Activa":
                        plan_act = sub.get("tipo_plan", "Premium")
                    rows.append([
                        u.get("id_usuario"),
                        u.get("nombre_usuario"),
                        u.get("email_usuario"),
                        u.get("rol"),
                        u.get("estado"),
                        plan_act
                    ])
            elif report_id == 'catalogo_completo':
                title = "Reporte de Catalogo Musical"
                cols = ["ID Cancion", "Cancion", "Artista", "Album", "Duracion (seg)", "Reproducciones"]
                rows = []
                for c in db.canciones.find().sort("id_cancion", 1):
                    rows.append([
                        c.get("id_cancion"),
                        c.get("titulo_cancion"),
                        c.get("artista", {}).get("nombre_artistico"),
                        c.get("album", {}).get("titulo_album"),
                        c.get("duracion_seg"),
                        c.get("num_reproducciones")
                    ])
            elif report_id == 'resumen_financiero':
                title = "Reporte de Resumen Financiero"
                cols = ["Plan", "Usuarios Activos", "Ingresos Estimados"]
                rows = []
                for p_name, price in [("Gratuito", 0.0), ("Premium", 5.99), ("Estudiante", 2.99), ("Familiar", 8.99)]:
                    if p_name == "Gratuito":
                        count = db.usuarios.count_documents({
                            "$or": [
                                {"suscripcion_activa": None},
                                {"suscripcion_activa.estado": {"$ne": "Activa"}},
                                {"suscripcion_activa.estado": "Activa", "suscripcion_activa.tipo_plan": "Gratuito"}
                            ]
                        })
                    else:
                        count = db.usuarios.count_documents({
                            "suscripcion_activa.estado": "Activa",
                            "suscripcion_activa.tipo_plan": p_name
                        })
                    rows.append([
                        p_name,
                        count,
                        f"${count * price:.2f}"
                    ])
            else:
                title, cols, rows = generar_reporte_mongo(
                    report_id,
                    param_artista=param_art,
                    param_usuario=param_usr,
                    param_fecha_inicio=f_inicio,
                    param_fecha_fin=f_fin
                )
            contexto['report_title'] = title
            contexto['cols'] = cols
            contexto['rows'] = rows
            if export == 'pdf':
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="reporte_{report_id}.pdf"'
                doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
                story = []
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'TitleStyle',
                    parent=styles['Heading1'],
                    fontName='Helvetica-Bold',
                    fontSize=20,
                    textColor=colors.HexColor('#1a1a1a'),
                    spaceAfter=8
                )
                subtitle_style = ParagraphStyle(
                    'SubTitleStyle',
                    parent=styles['Normal'],
                    fontName='Helvetica',
                    fontSize=10,
                    textColor=colors.HexColor('#c9a84c'),
                    spaceAfter=20
                )
                normal_style = ParagraphStyle(
                    'NormalStyle',
                    parent=styles['Normal'],
                    fontName='Helvetica',
                    fontSize=8,
                    textColor=colors.HexColor('#1a1a1a')
                )
                header_style = ParagraphStyle(
                    'HeaderStyle',
                    parent=styles['Normal'],
                    fontName='Helvetica-Bold',
                    fontSize=8,
                    textColor=colors.HexColor('#ffffff')
                )
                story.append(Paragraph(f"SoundWave - {title}", title_style))
                story.append(Paragraph(f"Reporte de Auditoria Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
                story.append(Spacer(1, 10))
                table_data = [[Paragraph(c, header_style) for c in cols]]
                for r in rows:
                    row_cells = []
                    for val in r:
                        if isinstance(val, datetime):
                            val_str = val.strftime('%d/%m/%Y %H:%M')
                        else:
                            val_str = str(val) if val is not None else 'null'
                        row_cells.append(Paragraph(val_str, normal_style))
                    table_data.append(row_cells)
                col_width = (doc.width) / len(cols)
                t = Table(table_data, colWidths=[col_width] * len(cols))
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TOPPADDING', (0, 0), (-1, 0), 6),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f0e8'), colors.HexColor('#ffffff')]),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c9a84c')),
                    ('PADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                doc.build(story)
                return response
        except Exception as e:
            contexto['error_msg'] = str(e)
    id_usuario = request.session.get('id_usuario') or get_usuario_activo()
    cancion_actual = 'Shape of You'
    artista_actual = 'Ed Sheeran'
    try:
        latest_play = db.reproducciones.find_one({"usuario.id_usuario": int(id_usuario)}, sort=[("fecha_hora", -1)])
        if latest_play:
            cancion_actual = latest_play.get('cancion', {}).get('titulo_cancion', cancion_actual)
            artista_actual = latest_play.get('artista', {}).get('nombre_artistico', artista_actual)
    except Exception:
        pass
    contexto['cancion_actual'] = cancion_actual
    contexto['artista_actual'] = artista_actual
    return render(request, 'plataforma/reportes.html', contexto)
