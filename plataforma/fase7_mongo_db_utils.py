import os
import json
import threading
import urllib.parse
from contextlib import contextmanager
from typing import List, Dict, Any, Union
from datetime import datetime, date
from pymongo import MongoClient

import urllib.parse
from pymongo.errors import ConnectionFailure

_client = None
_db = None
_thread_local = threading.local()

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()

def _load_config():
    return load_config()

def get_mongo_db():
    global _client, _db
    if _client is None:
        config = _load_config()
        mongo_cfg = config.get('mongodb', {})
        usuario = mongo_cfg.get('usuario')
        contrasena = urllib.parse.quote_plus(mongo_cfg.get('contrasena', ''))
        uri = (
            f"mongodb+srv://{usuario}:{contrasena}"
            f"@{mongo_cfg['cluster']}/?retryWrites=true&w=majority"
            f"&maxPoolSize=10&minPoolSize=2&maxIdleTimeMS=30000"
            f"&connectTimeoutMS=5000&socketTimeoutMS=10000"
        )
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        _db = _client[mongo_cfg['base_datos']]
    return _db

def close_connection():
    # Con pool de conexiones persistentes, mantenemos el cliente abierto para reutilización.
    pass

@contextmanager
def get_db_connection():
    db = None
    try:
        db = get_mongo_db()
        yield db
    except Exception as e:
        print(f"[SoundWave MongoDB Error] Error de conexión PyMongo: {e}")
        raise e
    finally:
        pass

def get_dashboard_fallback(error_msg):
    return {
        'error': error_msg,
        'stats': {
            'canciones_escuchadas': 0,
            'albumes_biblioteca': 0,
            'horas_reproduccion': 0.0,
            'nombre_usuario': 'Usuario Temporal NoSQL',
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

def execute_scalar(query_or_field: str, params: Union[List[Any], None] = None) -> Any:
    db = get_mongo_db()
    if params is None:
        params = []
    
    if "email_usuario" in query_or_field:
        email = params[0]
        if "id_usuario !=" in query_or_field or "!=" in query_or_field:
            user_id = params[1]
            return db.usuarios.count_documents({
                "email_usuario": email,
                "id_usuario": {"$ne": int(user_id)}
            })
        else:
            return db.usuarios.count_documents({"email_usuario": email})
    return 0

def execute_non_query(query: str, params: Union[List[Any], None] = None) -> int:
    return 0

def execute_stored_procedure(sp_name: str, params: Union[List[Any], None] = None) -> List[Dict[str, Any]]:
    return []

def crear_usuario_sp(id_rol, nombre, email, contrasena, estado='Activo', tipo_plan=None):
    db = get_mongo_db()
    rol_map = {1: 'Administrador', 2: 'Artista', 3: 'Oyente', 4: 'Premium'}
    rol_str = rol_map.get(int(id_rol), 'Oyente')
    
    max_user = db.usuarios.find_one({"id_usuario": {"$exists": True}}, sort=[("id_usuario", -1)])
    next_id = (max_user["id_usuario"] + 1) if max_user else 1
    
    suscripcion_doc = None
    if tipo_plan == 'Premium':
        from datetime import timedelta
        max_sub = db.suscripciones.find_one({"id_suscripcion": {"$exists": True}}, sort=[("id_suscripcion", -1)])
        next_sub_id = (max_sub["id_suscripcion"] + 1) if max_sub else 1
        fecha_ini = datetime.now()
        fecha_fi = fecha_ini + timedelta(days=30)
        
        suscripcion_doc = {
            "id_suscripcion": next_sub_id,
            "usuario": {
                "id_usuario": next_id,
                "nombre_usuario": nombre,
                "email_usuario": email
            },
            "tipo_plan": "Premium",
            "fecha_inicio": fecha_ini,
            "fecha_fin": fecha_fi,
            "estado": "Activa",
            "historial_pagos": []
        }
        db.suscripciones.insert_one(suscripcion_doc)
        
    db.usuarios.insert_one({
        "id_usuario": next_id,
        "nombre_usuario": nombre,
        "email_usuario": email,
        "contrasena": contrasena,
        "estado": estado,
        "rol": rol_str,
        "pais": "Ecuador",
        "fecha_registro": datetime.now(),
        "suscripcion_activa": {
            "id_suscripcion": suscripcion_doc["id_suscripcion"],
            "tipo_plan": "Premium",
            "fecha_inicio": suscripcion_doc["fecha_inicio"],
            "fecha_fin": suscripcion_doc["fecha_fin"],
            "estado": "Activa"
        } if suscripcion_doc else None,
        "albumes_guardados": [],
        "likes_canciones": [],
        "artistas_seguidos": [],
        "notificaciones": []
    })

def actualizar_usuario_sp(id_usuario, nombre, email, estado):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    db.usuarios.update_one(
        {"id_usuario": id_usr},
        {"$set": {
            "nombre_usuario": nombre,
            "email_usuario": email,
            "estado": estado
        }}
    )
    db.playlists.update_many(
        {"usuario.id_usuario": id_usr},
        {"$set": {"usuario.nombre_usuario": nombre}}
    )
    db.reproducciones.update_many(
        {"usuario.id_usuario": id_usr},
        {"$set": {
            "usuario.nombre_usuario": nombre,
            "usuario.email_usuario": email
        }}
    )
    db.suscripciones.update_many(
        {"usuario.id_usuario": id_usr},
        {"$set": {
            "usuario.nombre_usuario": nombre,
            "usuario.email_usuario": email
        }}
    )

def eliminar_usuario_sp(id_usuario):
    id_usr = int(id_usuario)
    if id_usr == CONFIG['app']['usuario_protegido_id']:
        raise Exception("No se puede eliminar el usuario principal del sistema.")
    
    db = get_mongo_db()
    db.usuarios.delete_one({"id_usuario": id_usr})
    db.suscripciones.delete_many({"usuario.id_usuario": id_usr})
    db.playlists.delete_many({"usuario.id_usuario": id_usr})
    db.reproducciones.delete_many({"usuario.id_usuario": id_usr})

def eliminar_usuario_bd(id_usuario):
    eliminar_usuario_sp(id_usuario)

def get_dashboard_data(id_usuario):
    try:
        db = get_mongo_db()
        id_usr = int(id_usuario)
        
        user = db.usuarios.find_one({"id_usuario": id_usr})
        if not user:
            return get_dashboard_fallback(f"El usuario con ID NoSQL #{id_usr} no existe en la base de datos.")
            
        resultado = {}
        
        canciones_escuchadas = db.reproducciones.count_documents({"usuario.id_usuario": id_usr})
        
        pipeline = [
            {"$match": {"usuario.id_usuario": id_usr}},
            {"$group": {"_id": None, "total_segundos": {"$sum": "$duracion_escuchada"}}}
        ]
        agg_res = list(db.reproducciones.aggregate(pipeline))
        total_segundos = agg_res[0]["total_segundos"] if agg_res else 0
        horas_reproduccion = round(total_segundos / 3600.0, 1)
        
        albumes_guardados = user.get("albumes_guardados", [])
        albumes_conteo = len(albumes_guardados)
        
        plan_activo = "Gratuito"
        if user.get("suscripcion_activa") and user["suscripcion_activa"].get("estado") == "Activa":
            plan_activo = user["suscripcion_activa"].get("tipo_plan", "Premium")
            
        resultado['stats'] = {
            'canciones_escuchadas': canciones_escuchadas,
            'albumes_biblioteca': albumes_conteo,
            'horas_reproduccion': horas_reproduccion,
            'nombre_usuario': user.get("nombre_usuario"),
            'email_usuario': user.get("email_usuario"),
            'estado': user.get("estado"),
            'plan_activo': plan_activo
        }
        
        sorted_albums = sorted(albumes_guardados, key=lambda x: x.get("fecha_guardado", ""), reverse=True)[:5]
        resultado['albumes'] = []
        for alb in sorted_albums:
            fecha_g = alb.get("fecha_guardado")
            if isinstance(fecha_g, str):
                try:
                    fecha_g = datetime.fromisoformat(fecha_g.replace("Z", "+00:00"))
                except:
                    pass
            resultado['albumes'].append({
                'titulo_album': alb.get('titulo_album'),
                'nombre_artistico': alb.get('nombre_artistico'),
                'fecha_guardado': fecha_g
            })
            
        recent_plays = db.reproducciones.find(
            {"usuario.id_usuario": id_usr}
        ).sort("fecha_hora", -1).limit(10)
        
        resultado['historial_reciente'] = []
        for play in recent_plays:
            fh = play.get("fecha_hora")
            fh_str = ""
            if isinstance(fh, datetime):
                fh_str = fh.strftime('%d/%m/%Y %H:%M')
            elif isinstance(fh, str):
                try:
                    fh_dt = datetime.fromisoformat(fh.replace("Z", "+00:00"))
                    fh_str = fh_dt.strftime('%d/%m/%Y %H:%M')
                except:
                    fh_str = fh
            resultado['historial_reciente'].append({
                'titulo_cancion': play.get('cancion', {}).get('titulo_cancion'),
                'nombre_artistico': play.get('artista', {}).get('nombre_artistico'),
                'fecha_hora': fh_str
            })
            
        latest_play = db.reproducciones.find_one(
            {"usuario.id_usuario": id_usr},
            sort=[("fecha_hora", -1)]
        )
        if latest_play:
            resultado['cancion_actual'] = {
                'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
                'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
            }
        else:
            resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
            
        top_songs = list(db.canciones.find(
            {"estado": "Activo"}
        ).sort("num_reproducciones", -1).limit(10))
        
        resultado['top_canciones'] = []
        for song in top_songs:
            resultado['top_canciones'].append({
                'id_cancion': song.get('id_cancion'),
                'Cancion': song.get('titulo_cancion'),
                'Artista': song.get('artista', {}).get('nombre_artistico'),
                'Duracion': song.get('duracion_seg'),
                'Reproducciones': song.get('num_reproducciones')
            })
            
        resultado['top10_global'] = []
        for song in top_songs:
            resultado['top10_global'].append({
                'titulo_cancion': song.get('titulo_cancion'),
                'nombre_artistico': song.get('artista', {}).get('nombre_artistico'),
                'num_reproducciones': song.get('num_reproducciones')
            })
            
        genres_pipeline = [
            {"$match": {"usuario.id_usuario": id_usr}},
            {"$lookup": {
                "from": "canciones",
                "localField": "cancion.id_cancion",
                "foreignField": "id_cancion",
                "as": "info"
            }},
            {"$unwind": "$info"},
            {"$unwind": "$info.generos"},
            {"$group": {"_id": "$info.generos"}}
        ]
        generos_escuchados = [g["_id"] for g in db.reproducciones.aggregate(genres_pipeline)]
        
        artistas_pipeline = [
            {"$match": {"usuario.id_usuario": id_usr}},
            {"$group": {"_id": "$artista.id_artista"}}
        ]
        artistas_escuchados = [a["_id"] for a in db.reproducciones.aggregate(artistas_pipeline)]
        top_artistas_ids = [s.get('artista', {}).get('id_artista') for s in top_songs]
        
        recomendaciones = []
        if generos_escuchados:
            rec_songs = db.canciones.find({
                "estado": "Activo",
                "generos": {"$in": generos_escuchados},
                "artista.id_artista": {"$nin": artistas_escuchados + top_artistas_ids}
            }).limit(15)
            for s in rec_songs:
                gen_name = s.get("generos", ["Desconocido"])[0]
                
                # Resolvemos portada_url
                id_artista = s.get('artista', {}).get('id_artista')
                id_album = s.get('album', {}).get('id_album')
                album_portada = None
                if id_artista:
                    art_doc = db.artistas.find_one({"id_artista": id_artista}, {"albumes": 1})
                    if art_doc:
                        for alb in art_doc.get('albumes', []):
                            if alb.get('id_album') == id_album:
                                album_portada = alb.get('portada_url')
                                break
                if not album_portada:
                    titulo_alb = s.get('album', {}).get('titulo_album', 'A').replace(' ', '+')
                    album_portada = f"https://ui-avatars.com/api/?name={titulo_alb}&size=200&background=2a2a2a&color=c9a84c&bold=true"
                
                recomendaciones.append({
                    "Cancion": s.get("titulo_cancion"),
                    "Artista": s.get("artista", {}).get("nombre_artistico"),
                    "Genero": gen_name,
                    "album": {
                        "portada_url": album_portada
                    }
                })
                
        if len(recomendaciones) < 5:
            ya_artistas = {r["Artista"] for r in recomendaciones}
            ya_canciones = {r["Cancion"] for r in recomendaciones}
            comp_songs = db.canciones.find({
                "estado": "Activo",
                "artista.id_artista": {"$nin": artistas_escuchados + top_artistas_ids}
            }).limit(15)
            for s in comp_songs:
                art_name = s.get("artista", {}).get("nombre_artistico")
                canc_name = s.get("titulo_cancion")
                if art_name not in ya_artistas and canc_name not in ya_canciones:
                    gen_name = s.get("generos", ["Global"])[0]
                    
                    # Resolvemos portada_url
                    id_artista = s.get('artista', {}).get('id_artista')
                    id_album = s.get('album', {}).get('id_album')
                    album_portada = None
                    if id_artista:
                        art_doc = db.artistas.find_one({"id_artista": id_artista}, {"albumes": 1})
                        if art_doc:
                            for alb in art_doc.get('albumes', []):
                                if alb.get('id_album') == id_album:
                                    album_portada = alb.get('portada_url')
                                    break
                    if not album_portada:
                        titulo_alb = s.get('album', {}).get('titulo_album', 'A').replace(' ', '+')
                        album_portada = f"https://ui-avatars.com/api/?name={titulo_alb}&size=200&background=2a2a2a&color=c9a84c&bold=true"
                    
                    recomendaciones.append({
                        "Cancion": canc_name,
                        "Artista": art_name,
                        "Genero": gen_name,
                        "album": {
                            "portada_url": album_portada
                        }
                    })
                    if len(recomendaciones) >= 5:
                        break
                        
        resultado['recomendaciones'] = recomendaciones[:5]
        return resultado
        
    except Exception as e:
        print(f"Error cargando dashboard NoSQL para usuario {id_usuario}: {e}")
        return get_dashboard_fallback(f"Error de base de datos NoSQL: {str(e)}")

def get_catalogo_completo(id_usuario, filtro_artista: str = '', filtro_genero: str = ''):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    resultado = {}
    
    artistas = list(db.artistas.find({}, {"id_artista": 1, "nombre_artistico": 1, "imagen_url": 1, "pais": 1, "albumes": 1}))
    artistas_map = {a['id_artista']: a for a in artistas if 'id_artista' in a}
    
    artistas_ranking = list(db.artistas.find({}).sort("total_reproducciones", -1))
    resultado['artistas'] = []
    for artista in artistas_ranking:
        imagen = artista.get('imagen_url')
        if not imagen:
            nombre = artista.get('nombre_artistico', 'A').replace(' ', '+')
            imagen = f"https://ui-avatars.com/api/?name={nombre}&size=440&background=1a1a1a&color=c9a84c&bold=true&font-size=0.4"
        resultado['artistas'].append({
            'id_artista': artista.get('id_artista'),
            'nombre_artistico': artista.get('nombre_artistico'),
            'pais': artista.get('pais') if artista.get('pais') else 'Sin datos',
            'total_reproducciones': artista.get('total_reproducciones', 0),
            'imagen_url': imagen
        })
        
    resultado['lista_artistas'] = sorted(list(db.canciones.distinct("artista.nombre_artistico", {"estado": "Activo"})))
    resultado['lista_generos'] = sorted(list(db.canciones.distinct("generos")))
    
    query = {"estado": "Activo"}
    if filtro_artista:
        query["artista.nombre_artistico"] = filtro_artista
    if filtro_genero:
        query["generos"] = filtro_genero
        
    cursor = db.canciones.find(query)
    if not filtro_artista and not filtro_genero:
        cursor = cursor.sort("num_reproducciones", -1).limit(20)
    else:
        cursor = cursor.sort("num_reproducciones", -1)
        
    resultado['canciones'] = []
    for s in cursor:
        id_artista = s.get('artista', {}).get('id_artista')
        
        artista_imagen = None
        if id_artista and id_artista in artistas_map:
            artista_imagen = artistas_map[id_artista].get('imagen_url')
        if not artista_imagen:
            nombre_art = s.get('artista', {}).get('nombre_artistico', 'A').replace(' ', '+')
            artista_imagen = f"https://ui-avatars.com/api/?name={nombre_art}&size=200&background=1a1a1a&color=c9a84c&bold=true"
            
        album_portada = None
        id_album = s.get('album', {}).get('id_album')
        if id_artista and id_artista in artistas_map:
            for alb in artistas_map[id_artista].get('albumes', []):
                if alb.get('id_album') == id_album:
                    album_portada = alb.get('portada_url')
                    break
        if not album_portada:
            titulo_alb = s.get('album', {}).get('titulo_album', 'A').replace(' ', '+')
            album_portada = f"https://ui-avatars.com/api/?name={titulo_alb}&size=200&background=2a2a2a&color=c9a84c&bold=true"
            
        resultado['canciones'].append({
            'id_cancion': s.get('id_cancion'),
            'Cancion': s.get('titulo_cancion'),
            'Artista': s.get('artista', {}).get('nombre_artistico'),
            'id_artista': id_artista,
            'Album': s.get('album', {}).get('titulo_album'),
            'id_album': id_album,
            'Segundos': s.get('duracion_seg'),
            'Reproducciones': s.get('num_reproducciones'),
            'artista': {
                'id_artista': id_artista,
                'nombre_artistico': s.get('artista', {}).get('nombre_artistico'),
                'imagen_url': artista_imagen
            },
            'album': {
                'id_album': id_album,
                'titulo_album': s.get('album', {}).get('titulo_album'),
                'portada_url': album_portada
            }
        })
        
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": id_usr},
        sort=[("fecha_hora", -1)]
    )
    if latest_play:
        resultado['cancion_actual'] = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
    else:
        resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
        
    return resultado

def get_historial_completo(id_usuario, fecha_inicio, fecha_fin, genero):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    resultado = {}
    
    query = {"usuario.id_usuario": id_usr}
    
    if fecha_inicio or fecha_fin:
        date_query = {}
        if fecha_inicio:
            try:
                dt_ini = datetime.combine(date.fromisoformat(fecha_inicio), datetime.min.time())
                date_query["$gte"] = dt_ini
            except:
                date_query["$gte"] = fecha_inicio + " 00:00:00"
        if fecha_fin:
            try:
                dt_fin = datetime.combine(date.fromisoformat(fecha_fin), datetime.max.time())
                date_query["$lte"] = dt_fin
            except:
                date_query["$lte"] = fecha_fin + " 23:59:59"
        query["fecha_hora"] = date_query
        
    if genero:
        canciones_genero = db.canciones.distinct("id_cancion", {"generos": genero})
        query["cancion.id_cancion"] = {"$in": canciones_genero}
        
    canciones_ids = list(db.reproducciones.distinct("cancion.id_cancion", {"usuario.id_usuario": id_usr}))
    canciones_map = {}
    if canciones_ids:
        for c in db.canciones.find({"id_cancion": {"$in": canciones_ids}}, {"id_cancion": 1, "generos": 1}):
            gens = c.get("generos", [])
            canciones_map[c["id_cancion"]] = gens[0] if gens else "General"
            
    cursor_reprod = db.reproducciones.find(query).sort("fecha_hora", -1)
    
    resultado['reporte_datos'] = []
    for play in cursor_reprod:
        c_id = play.get('cancion', {}).get('id_cancion')
        gen_resolved = canciones_map.get(c_id, "General") if not genero else genero
        resultado['reporte_datos'].append({
            'FechaHora': play.get("fecha_hora"),
            'Cancion': play.get('cancion', {}).get('titulo_cancion'),
            'Artista': play.get('artista', {}).get('nombre_artistico'),
            'Genero': gen_resolved,
            'Segundos': play.get('duracion_escuchada')
        })
        
    resultado['lista_generos'] = sorted(list(db.canciones.distinct("generos")))
    
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": id_usr},
        sort=[("fecha_hora", -1)]
    )
    if latest_play:
        resultado['cancion_actual'] = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
    else:
        resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
        
    return resultado

def get_suscripcion_data(id_usuario):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    resultado = {}
    
    sub = db.suscripciones.find_one(
        {"usuario.id_usuario": id_usr, "estado": "Activa"},
        sort=[("fecha_inicio", -1)]
    )
    
    if sub:
        resultado['sub_actual'] = {
            'id_suscripcion': sub.get('id_suscripcion'),
            'tipo_plan': sub.get('tipo_plan'),
            'fecha_inicio': sub.get('fecha_inicio'),
            'fecha_fin': sub.get('fecha_fin'),
            'estado': sub.get('estado')
        }
    else:
        resultado['sub_actual'] = {'id_suscripcion': 1, 'tipo_plan': 'Premium', 'estado': 'Activa'}
        
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": id_usr},
        sort=[("fecha_hora", -1)]
    )
    if latest_play:
        resultado['cancion_actual'] = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
    else:
        resultado['cancion_actual'] = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
        
    return resultado

def registrar_reproduccion_mongo(id_usuario, id_cancion, duracion_seg):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    id_canc = int(id_cancion)
    
    song = db.canciones.find_one({"id_cancion": id_canc})
    if not song:
        raise Exception("Canción no encontrada")
        
    user = db.usuarios.find_one({"id_usuario": id_usr})
    if not user:
        raise Exception("Usuario no encontrado")
        
    max_rep = db.reproducciones.find_one(sort=[("id_historial", -1)])
    next_rep_id = (max_rep["id_historial"] + 1) if max_rep else 1
    
    db.reproducciones.insert_one({
        "id_historial": next_rep_id,
        "fecha_hora": datetime.now(),
        "duracion_escuchada": int(duracion_seg),
        "mes_año": datetime.now().strftime('%Y-%m'),
        "usuario": {
            "id_usuario": user["id_usuario"],
            "nombre_usuario": user["nombre_usuario"],
            "email_usuario": user["email_usuario"]
        },
        "cancion": {
            "id_cancion": song["id_cancion"],
            "titulo_cancion": song["titulo_cancion"],
            "duracion_seg": song["duracion_seg"]
        },
        "artista": {
            "id_artista": song["artista"]["id_artista"],
            "nombre_artistico": song["artista"]["nombre_artistico"]
        }
    })
    
    db.canciones.update_one(
        {"id_cancion": id_canc},
        {"$inc": {"num_reproducciones": 1}}
    )
    
    updated_song = db.canciones.find_one({"id_cancion": id_canc})
    return song.get("titulo_cancion"), song.get("artista", {}).get("nombre_artistico"), updated_song.get("num_reproducciones", 0)

def procesar_renovacion_mongo(id_suscripcion, estado_pago):
    db = get_mongo_db()
    id_sub = int(id_suscripcion)
    
    sub = db.suscripciones.find_one({"id_suscripcion": id_sub})
    if not sub:
        return None
        
    nuevo_estado = "Activa" if estado_pago == "Completado" else "Vencida"
    nueva_fecha_fin = datetime.now()
    if estado_pago == "Completado":
        from datetime import timedelta
        nueva_fecha_fin = datetime.now() + timedelta(days=365)
        
    db.suscripciones.update_one(
        {"id_suscripcion": id_sub},
        {"$set": {
            "estado": nuevo_estado,
            "fecha_fin": nueva_fecha_fin
        }}
    )
    
    user_id = sub["usuario"]["id_usuario"]
    db.usuarios.update_one(
        {"id_usuario": user_id},
        {"$set": {
            "suscripcion_activa.estado": nuevo_estado,
            "suscripcion_activa.fecha_fin": nueva_fecha_fin
        }}
    )
    
    pago_id = db.suscripciones.count_documents({"id_suscripcion": {"$exists": True}}) + 1
    db.suscripciones.update_one(
        {"id_suscripcion": id_sub},
        {"$push": {"historial_pagos": {
            "id_pago": pago_id,
            "fecha_pago": datetime.now(),
            "monto": 9.99,
            "metodo_pago": "Tarjeta Credito",
            "estado_pago": estado_pago
        }}}
    )
    
    return {
        'plan': sub.get('tipo_plan'),
        'fecha_fin': nueva_fecha_fin.strftime('%d/%m/%Y') if estado_pago == "Completado" else 'Indefinida',
        'estado': nuevo_estado,
        'exito': estado_pago == "Completado"
    }

def get_administracion_data_mongo(id_usuario):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    
    oyentes_cursor = db.usuarios.find(
        {"rol": {"$in": ["Oyente", "Premium"]}}
    ).sort("id_usuario", -1)
    
    oyentes = []
    for u in oyentes_cursor:
        fr = u.get("fecha_registro")
        fr_str = fr.strftime('%d/%m/%Y') if isinstance(fr, datetime) else str(fr)
        
        plan_activo = "Gratuito"
        if u.get("suscripcion_activa") and u["suscripcion_activa"].get("estado") == "Activa":
            plan_activo = u["suscripcion_activa"].get("tipo_plan", "Premium")
            
        oyentes.append({
            "id_usuario": u["id_usuario"],
            "nombre_usuario": u["nombre_usuario"],
            "email_usuario": u["email_usuario"],
            "estado": u["estado"],
            "nombre_rol": u["rol"],
            "plan_activo": plan_activo,
            "fecha_registro": fr_str
        })
        
    artistas_cursor = db.artistas.find({"id_artista": {"$exists": True}}).sort("nombre_artistico", 1)
    artistas = []
    for a in artistas_cursor:
        id_art = a["id_artista"]
        albumes_conteo = len(a.get("albumes", []))
        songs = list(db.canciones.find({"artista.id_artista": id_art}))
        canciones_conteo = len(songs)
        total_reprod = sum(s.get("num_reproducciones", 0) for s in songs)
        
        user_art = db.usuarios.find_one({"nombre_usuario": a["nombre_artistico"], "rol": "Artista"})
        fr_str = ""
        if user_art:
            fr = user_art.get("fecha_registro")
            fr_str = fr.strftime('%d/%m/%Y') if isinstance(fr, datetime) else str(fr)
            
        artistas.append({
            "id_usuario": user_art["id_usuario"] if user_art else id_art,
            "nombre_usuario": a["nombre_artistico"],
            "email_usuario": a["email_contacto"],
            "estado": user_art["estado"] if user_art else "Activo",
            "fecha_registro": fr_str,
            "nombre_artistico": a["nombre_artistico"],
            "pais": a["pais"] if a["pais"] else "Sin datos",
            "total_albumes": albumes_conteo,
            "total_canciones": canciones_conteo,
            "total_reproducciones": total_reprod
        })
        
    artistas = sorted(artistas, key=lambda x: x["total_reproducciones"], reverse=True)
    
    total_usuarios = db.usuarios.count_documents({"id_usuario": {"$exists": True}})
    total_canciones = db.canciones.count_documents({"id_cancion": {"$exists": True}})
    total_albumes = db.artistas.aggregate([
        {"$unwind": "$albumes"},
        {"$group": {"_id": None, "count": {"$sum": 1}}}
    ])
    total_albumes_list = list(total_albumes)
    total_albumes_val = total_albumes_list[0]["count"] if total_albumes_list else 0
    total_reproducciones = db.reproducciones.count_documents({"id_historial": {"$exists": True}})
    suscripciones_activas = db.suscripciones.count_documents({"estado": "Activa"})
    total_regalias = total_reproducciones * 0.004
    
    sistema_stats = {
        "total_usuarios": total_usuarios,
        "total_canciones": total_canciones,
        "total_albumes": total_albumes_val,
        "total_reproducciones": total_reproducciones,
        "suscripciones_activas": suscripciones_activas,
        "total_regalias": total_regalias
    }
    
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": id_usr},
        sort=[("fecha_hora", -1)]
    )
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    if latest_play:
        player_info = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
        
    return {
        "oyentes": oyentes,
        "artistas": artistas,
        "sistema_stats": sistema_stats,
        "player_info": player_info
    }

def get_detalle_artista_mongo(id_artista, id_usuario):
    db = get_mongo_db()
    id_art = int(id_artista)
    
    artista = db.artistas.find_one({"id_artista": id_art})
    if not artista:
        return None
        
    total_reprod = sum(s.get("num_reproducciones", 0) for s in db.canciones.find({"artista.id_artista": id_art}))
    
    artista_data = {
        'id_artista': artista.get('id_artista'),
        'nombre_artistico': artista.get('nombre_artistico'),
        'biografia': artista.get('biografia'),
        'pais': artista.get('pais'),
        'fecha_debut': artista.get('fecha_debut'),
        'imagen_perfil': artista.get('imagen_perfil'),
        'imagen_url': artista.get('imagen_url') or artista.get('imagen_perfil'),
        'email_contacto': artista.get('email_contacto'),
        'email_usuario': artista.get('email_contacto'),
        'total_reprod': total_reprod,
        'total_reproducciones': total_reprod
    }
    
    albumes_list = []
    for alb in artista.get("albumes", []):
        id_album = alb.get("id_album")
        canciones_cursor = db.canciones.find({"album.id_album": id_album}).sort("id_cancion", 1)
        canciones_list = []
        for s in canciones_cursor:
            minutos = s['duracion_seg'] // 60
            segundos = s['duracion_seg'] % 60
            canciones_list.append({
                'id_cancion': s.get('id_cancion'),
                'titulo_cancion': s.get('titulo_cancion'),
                'duracion_seg': s.get('duracion_seg'),
                'num_reproducciones': s.get('num_reproducciones'),
                'DuracionFormateada': f"{minutos}:{segundos:02d}"
            })
            
        albumes_list.append({
            'id_album': id_album,
            'titulo_album': alb.get('titulo_album'),
            'fecha_lanzamiento': alb.get('fecha_lanzamiento'),
            'descripcion': alb.get('descripcion'),
            'total_canciones': len(canciones_list),
            'canciones': canciones_list
        })
        
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": int(id_usuario)},
        sort=[("fecha_hora", -1)]
    )
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    if latest_play:
        player_info = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
        
    return {
        'artista': artista_data,
        'albumes': albumes_list,
        'player_info': player_info
    }

def get_detalle_album_mongo(id_album, id_usuario):
    db = get_mongo_db()
    id_alb = int(id_album)
    
    artista_doc = db.artistas.find_one({"albumes.id_album": id_alb})
    if not artista_doc:
        return None
        
    alb_info = next(a for a in artista_doc.get("albumes", []) if a.get("id_album") == id_alb)
    
    album_data = {
        'id_album': id_alb,
        'titulo_album': alb_info.get('titulo_album'),
        'fecha_lanzamiento': alb_info.get('fecha_lanzamiento'),
        'descripcion': alb_info.get('descripcion'),
        'portada_url': alb_info.get('portada_url'),
        'nombre_artistico': artista_doc.get('nombre_artistico'),
        'id_artista': artista_doc.get('id_artista')
    }
    
    canciones_cursor = db.canciones.find({"album.id_album": id_alb}).sort("id_cancion", 1)
    canciones_list = []
    for s in canciones_cursor:
        minutos = s['duracion_seg'] // 60
        segundos = s['duracion_seg'] % 60
        generos_str = ", ".join(s.get("generos", []))
        canciones_list.append({
            'id_cancion': s.get('id_cancion'),
            'titulo_cancion': s.get('titulo_cancion'),
            'duracion_seg': s.get('duracion_seg'),
            'num_reproducciones': s.get('num_reproducciones'),
            'generos': generos_str,
            'DuracionFormateada': f"{minutos}:{segundos:02d}"
        })
        
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": int(id_usuario)},
        sort=[("fecha_hora", -1)]
    )
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    if latest_play:
        player_info = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
        
    return {
        'album': album_data,
        'canciones': canciones_list,
        'player_info': player_info
    }

def get_detalle_playlist_mongo(id_playlist, id_usuario):
    db = get_mongo_db()
    id_pl = int(id_playlist)
    
    playlist = db.playlists.find_one({"id_playlist": id_pl})
    if not playlist:
        return None
        
    playlist_data = {
        'id_playlist': playlist.get('id_playlist'),
        'nombre_playlist': playlist.get('nombre_playlist'),
        'descripcion': playlist.get('descripcion'),
        'es_publica': playlist.get('es_publica'),
        'nombre_usuario': playlist.get('usuario', {}).get('nombre_usuario')
    }
    
    canciones_list = []
    for s in playlist.get("canciones", []):
        minutos = s.get('duracion_seg', 0) // 60
        segundos = s.get('duracion_seg', 0) % 60
        canciones_list.append({
            'orden': s.get('orden'),
            'id_cancion': s.get('id_cancion'),
            'titulo_cancion': s.get('titulo_cancion'),
            'duracion_seg': s.get('duracion_seg'),
            'nombre_artistico': s.get('nombre_artistico'),
            'id_artista': s.get('id_artista'),
            'titulo_album': s.get('titulo_album', 'Album'),
            'id_album': s.get('id_album', 1),
            'DuracionFormateada': f"{minutos}:{segundos:02d}"
        })
        
    latest_play = db.reproducciones.find_one(
        {"usuario.id_usuario": int(id_usuario)},
        sort=[("fecha_hora", -1)]
    )
    player_info = {'cancion_actual': 'Shape of You', 'artista_actual': 'Ed Sheeran'}
    if latest_play:
        player_info = {
            'cancion_actual': latest_play.get('cancion', {}).get('titulo_cancion'),
            'artista_actual': latest_play.get('artista', {}).get('nombre_artistico')
        }
        
    return {
        'playlist': playlist_data,
        'canciones': canciones_list,
        'player_info': player_info
    }

def generar_reporte_mongo(report_id, param_artista=None, param_usuario=None, param_fecha_inicio=None, param_fecha_fin=None):
    db = get_mongo_db()
    cols = []
    rows = []
    report_title = ""
    
    if report_id == '1':
        report_title = "Top 10 Canciones mas Reproducidas"
        cols = ["id_cancion", "Cancion", "Artista", "Duracion", "Reproducciones"]
        songs = db.canciones.find({"estado": "Activo"}).sort("num_reproducciones", -1).limit(10)
        for s in songs:
            rows.append([
                s.get("id_cancion"),
                s.get("titulo_cancion"),
                s.get("artista", {}).get("nombre_artistico"),
                s.get("duracion_seg"),
                s.get("num_reproducciones")
            ])
            
    elif report_id == '2':
        report_title = "Artistas mas Populares"
        cols = ["id_artista", "Nombre Artistico", "Pais", "Total Reproducciones"]
        pipeline = [
            {"$match": {"estado": "Activo"}},
            {"$group": {
                "_id": "$artista.id_artista",
                "nombre_artistico": {"$first": "$artista.nombre_artistico"},
                "pais": {"$first": "$artista.pais"},
                "total_reprod": {"$sum": "$num_reproducciones"}
            }},
            {"$sort": {"total_reprod": -1}}
        ]
        for r in db.canciones.aggregate(pipeline):
            rows.append([
                r["_id"],
                r["nombre_artistico"],
                r["pais"] if r["pais"] else "Sin datos",
                r["total_reprod"]
            ])
            
    elif report_id == '3':
        report_title = "Suscripciones Activas"
        cols = ["id_suscripcion", "Usuario", "Email", "Plan", "Fecha Inicio", "Fecha Fin"]
        subs = db.suscripciones.find({"estado": "Activa"}).sort("fecha_inicio", -1)
        for s in subs:
            rows.append([
                s.get("id_suscripcion"),
                s.get("usuario", {}).get("nombre_usuario"),
                s.get("usuario", {}).get("email_usuario"),
                s.get("tipo_plan"),
                s.get("fecha_inicio"),
                s.get("fecha_fin")
            ])
            
    elif report_id == '4':
        report_title = "Ingresos por Artista"
        cols = ["Artista", "Total Reproducciones", "Tarifa por Reproduccion", "Ingresos Totales"]
        if not param_artista:
            raise Exception("Debe seleccionar un artista.")
        id_art = int(param_artista)
        art = db.artistas.find_one({"id_artista": id_art})
        art_name = art.get("nombre_artistico") if art else f"Artista #{id_art}"
        
        total_reprod = sum(s.get("num_reproducciones", 0) for s in db.canciones.find({"artista.id_artista": id_art}))
        tarifa = 0.004
        ingresos = total_reprod * tarifa
        rows.append([
            art_name,
            total_reprod,
            tarifa,
            ingresos
        ])
        
    elif report_id == '5':
        report_title = "Historial por Usuario"
        cols = ["Fecha/Hora", "Cancion", "Artista", "Duracion (seg)"]
        if not param_usuario:
            raise Exception("Debe seleccionar un usuario.")
        id_usr = int(param_usuario)
        query = {"usuario.id_usuario": id_usr}
        
        if param_fecha_inicio or param_fecha_fin:
            date_query = {}
            if param_fecha_inicio:
                try:
                    dt_ini = datetime.combine(date.fromisoformat(param_fecha_inicio), datetime.min.time())
                    date_query["$gte"] = dt_ini
                except:
                    date_query["$gte"] = param_fecha_inicio + " 00:00:00"
            if param_fecha_fin:
                try:
                    dt_fin = datetime.combine(date.fromisoformat(param_fecha_fin), datetime.max.time())
                    date_query["$lte"] = dt_fin
                except:
                    date_query["$lte"] = param_fecha_fin + " 23:59:59"
            query["fecha_hora"] = date_query
            
        plays = db.reproducciones.find(query).sort("fecha_hora", -1)
        for p in plays:
            rows.append([
                p.get("fecha_hora"),
                p.get("cancion", {}).get("titulo_cancion"),
                p.get("artista", {}).get("nombre_artistico"),
                p.get("duracion_escuchada")
            ])
            
    elif report_id == '6':
        report_title = "Albumes Guardados por Usuario"
        cols = ["Album", "Artista", "Fecha Guardado"]
        if not param_usuario:
            raise Exception("Debe seleccionar un usuario.")
        id_usr = int(param_usuario)
        usr = db.usuarios.find_one({"id_usuario": id_usr})
        if usr:
            for alb in usr.get("albumes_guardados", []):
                rows.append([
                    alb.get("titulo_album"),
                    alb.get("nombre_artistico"),
                    alb.get("fecha_guardado")
                ])
                
    return report_title, cols, rows

def crear_artista_sp(nombre_artistico, email, pais, genero_musical=None, biografia=None):
    db = get_mongo_db()
    max_art = db.artistas.find_one({"id_artista": {"$exists": True}}, sort=[("id_artista", -1)])
    next_id = (max_art["id_artista"] + 1) if max_art else 1
    db.artistas.insert_one({
        "id_artista": next_id,
        "nombre_artistico": nombre_artistico,
        "email_contacto": email,
        "pais": pais,
        "genero_musical": genero_musical,
        "biografia": biografia,
        "fecha_debut": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "imagen_perfil": "img/default_perfil.png",
        "albumes": []
    })

def actualizar_artista_sp(id_artista, nombre_artistico, pais, genero_musical=None, biografia=None, estado=None):
    db = get_mongo_db()
    id_art = int(id_artista)
    old_artist = db.artistas.find_one({"id_artista": id_art})
    if not old_artist:
        return
    update_fields = {
        "nombre_artistico": nombre_artistico,
        "pais": pais
    }
    if genero_musical is not None:
        update_fields["genero_musical"] = genero_musical
    if biografia is not None:
        update_fields["biografia"] = biografia
    db.artistas.update_one({"id_artista": id_art}, {"$set": update_fields})
    old_name = old_artist.get("nombre_artistico")
    if old_name != nombre_artistico:
        db.canciones.update_many(
            {"artista.id_artista": id_art},
            {"$set": {"artista.nombre_artistico": nombre_artistico}}
        )
        db.playlists.update_many(
            {"canciones.id_artista": id_art},
            {"$set": {"canciones.$[elem].nombre_artistico": nombre_artistico}},
            array_filters=[{"elem.id_artista": id_art}]
        )
        db.reproducciones.update_many(
            {"artista.id_artista": id_art},
            {"$set": {"artista.nombre_artistico": nombre_artistico}}
        )

def eliminar_artista_sp(id_artista):
    db = get_mongo_db()
    id_art = int(id_artista)
    db.artistas.delete_one({"id_artista": id_art})
    db.canciones.delete_many({"artista.id_artista": id_art})
    db.playlists.update_many({}, {"$pull": {"canciones": {"id_artista": id_art}}})

def crear_album_sp(id_artista, titulo_album, fecha_lanzamiento=None, descripcion=None):
    db = get_mongo_db()
    id_art = int(id_artista)
    pipeline = [
        {"$unwind": "$albumes"},
        {"$group": {"_id": None, "max_id": {"$max": "$albumes.id_album"}}}
    ]
    res = list(db.artistas.aggregate(pipeline))
    max_id = res[0]["max_id"] if res else 0
    next_id = max_id + 1
    fecha_str = fecha_lanzamiento if fecha_lanzamiento else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_album = {
        "id_album": next_id,
        "titulo_album": titulo_album,
        "fecha_lanzamiento": fecha_str,
        "descripcion": descripcion if descripcion else "",
        "canciones": []
    }
    db.artistas.update_one(
        {"id_artista": id_art},
        {"$push": {"albumes": new_album}}
    )

def actualizar_album_sp(id_album, titulo_album, fecha_lanzamiento=None, descripcion=None):
    db = get_mongo_db()
    id_alb = int(id_album)
    update_query = {
        "albumes.$.titulo_album": titulo_album
    }
    if fecha_lanzamiento is not None:
        update_query["albumes.$.fecha_lanzamiento"] = fecha_lanzamiento
    if descripcion is not None:
        update_query["albumes.$.descripcion"] = descripcion
    db.artistas.update_one(
        {"albumes.id_album": id_alb},
        {"$set": update_query}
    )
    db.canciones.update_many(
        {"album.id_album": id_alb},
        {"$set": {"album.titulo_album": titulo_album}}
    )
    db.playlists.update_many(
        {"canciones.id_album": id_alb},
        {"$set": {"canciones.$[elem].titulo_album": titulo_album}},
        array_filters=[{"elem.id_album": id_alb}]
    )

def eliminar_album_sp(id_album):
    db = get_mongo_db()
    id_alb = int(id_album)
    db.artistas.update_one(
        {"albumes.id_album": id_alb},
        {"$pull": {"albumes": {"id_album": id_alb}}}
    )
    db.canciones.delete_many({"album.id_album": id_alb})
    db.playlists.update_many({}, {"$pull": {"canciones": {"id_album": id_alb}}})

def crear_cancion_sp(id_album, titulo_cancion, duracion_seg, genero_musical=None):
    db = get_mongo_db()
    id_alb = int(id_album)
    artist = db.artistas.find_one({"albumes.id_album": id_alb})
    if not artist:
        return
    id_artista = artist["id_artista"]
    nombre_artistico = artist["nombre_artistico"]
    pais = artist.get("pais", "Ecuador")
    titulo_album = ""
    for alb in artist.get("albumes", []):
        if alb.get("id_album") == id_alb:
            titulo_album = alb.get("titulo_album", "")
            break
    max_song = db.canciones.find_one({"id_cancion": {"$exists": True}}, sort=[("id_cancion", -1)])
    next_id = (max_song["id_cancion"] + 1) if max_song else 1
    new_song = {
        "id_cancion": next_id,
        "titulo_cancion": titulo_cancion,
        "duracion_seg": int(duracion_seg),
        "url_audio": f"/audio/{next_id:03d}.mp3",
        "num_reproducciones": 0,
        "fecha_publicacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "estado": "Activo",
        "artista": {
            "id_artista": id_artista,
            "nombre_artistico": nombre_artistico,
            "pais": pais
        },
        "album": {
            "id_album": id_alb,
            "titulo_album": titulo_album
        },
        "generos": [genero_musical] if genero_musical else ["Pop"]
    }
    db.canciones.insert_one(new_song)
    db.artistas.update_one(
        {"albumes.id_album": id_alb},
        {"$push": {"albumes.$.canciones": {
            "id_cancion": next_id,
            "titulo_cancion": titulo_cancion,
            "duracion_seg": int(duracion_seg),
            "num_reproducciones": 0,
            "url_audio": f"/audio/{next_id:03d}.mp3",
            "fecha_publicacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }}}
    )

def actualizar_cancion_sp(id_cancion, titulo_cancion, duracion_seg, genero_musical=None):
    db = get_mongo_db()
    id_canc = int(id_cancion)
    update_fields = {
        "titulo_cancion": titulo_cancion,
        "duracion_seg": int(duracion_seg)
    }
    if genero_musical is not None:
        update_fields["generos"] = [genero_musical]
    db.canciones.update_one({"id_cancion": id_canc}, {"$set": update_fields})
    db.artistas.update_one(
        {"albumes.canciones.id_cancion": id_canc},
        {"$set": {
            "albumes.$[alb].canciones.$[song].titulo_cancion": titulo_cancion,
            "albumes.$[alb].canciones.$[song].duracion_seg": int(duracion_seg)
        }},
        array_filters=[
            {"alb.canciones.id_cancion": id_canc},
            {"song.id_cancion": id_canc}
        ]
    )
    db.playlists.update_many(
        {"canciones.id_cancion": id_canc},
        {"$set": {
            "canciones.$[elem].titulo_cancion": titulo_cancion,
            "canciones.$[elem].duracion_seg": int(duracion_seg)
        }},
        array_filters=[{"elem.id_cancion": id_canc}]
    )

def eliminar_cancion_sp(id_cancion):
    db = get_mongo_db()
    id_canc = int(id_cancion)
    db.canciones.delete_one({"id_cancion": id_canc})
    db.artistas.update_one(
        {"albumes.canciones.id_cancion": id_canc},
        {"$pull": {"albumes.$[alb].canciones": {"id_cancion": id_canc}}},
        array_filters=[{"alb.canciones.id_cancion": id_canc}]
    )
    db.playlists.update_many(
        {"canciones.id_cancion": id_canc},
        {"$pull": {"canciones": {"id_cancion": id_canc}}}
    )

def validar_credenciales_mongo(email, contrasena):
    db = get_mongo_db()
    user = db.usuarios.find_one({"email_usuario": email, "estado": "Activo"})
    if not user:
        return None
    db_contrasena = user.get("contrasena")
    if contrasena == db_contrasena or f"hash_{contrasena}" == db_contrasena:
        sub_activa = user.get("suscripcion_activa")
        plan_activo = "Gratuito"
        if sub_activa and sub_activa.get("estado") == "Activa":
            plan_activo = sub_activa.get("tipo_plan", "Premium")
        return {
            "id_usuario": user.get("id_usuario"),
            "nombre_usuario": user.get("nombre_usuario"),
            "rol": user.get("rol"),
            "plan": plan_activo
        }
    return None

def obtener_perfil_usuario_mongo(id_usuario):
    db = get_mongo_db()
    user = db.usuarios.find_one({"id_usuario": int(id_usuario)})
    if not user:
        return None
    sub_activa = user.get("suscripcion_activa")
    plan_activo = "Gratuito"
    if sub_activa and sub_activa.get("estado") == "Activa":
        plan_activo = sub_activa.get("tipo_plan", "Premium")
    return {
        "nombre_usuario": user.get("nombre_usuario"),
        "rol": user.get("rol"),
        "plan": plan_activo,
        "email_usuario": user.get("email_usuario")
    }

def agregar_album_guardado(id_usuario, id_album):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    id_alb = int(id_album)
    album = db.artistas.find_one(
        {"albumes.id_album": id_alb},
        {"albumes.$": 1}
    )
    if not album:
        raise Exception("Álbum no encontrado")
    album_info = album["albumes"][0]
    artista = db.artistas.find_one({"albumes.id_album": id_alb}, {"nombre_artistico": 1})
    db.usuarios.update_one(
        {"id_usuario": id_usr, "albumes_guardados.id_album": {"$ne": id_alb}},
        {"$push": {"albumes_guardados": {
            "id_album": id_alb,
            "titulo_album": album_info["titulo_album"],
            "nombre_artistico": artista["nombre_artistico"],
            "fecha_guardado": datetime.now()
        }}}
    )

def quitar_album_guardado(id_usuario, id_album):
    db = get_mongo_db()
    id_usr = int(id_usuario)
    id_alb = int(id_album)
    db.usuarios.update_one(
        {"id_usuario": id_usr},
        {"$pull": {"albumes_guardados": {"id_album": id_alb}}}
    )

