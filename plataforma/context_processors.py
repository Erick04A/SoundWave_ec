import urllib.parse
from plataforma.fase7_mongo_db_utils import obtener_perfil_usuario_mongo

def user_profile(request):
    id_usuario = request.session.get('id_usuario')
    if not id_usuario:
        return {}
    try:
        profile = obtener_perfil_usuario_mongo(id_usuario)
        if profile:
            email = profile.get("email_usuario", "").strip()
            nombre = profile.get("nombre_usuario", "").strip()
            plan = profile.get("plan", "Gratuito").strip()
            avatar_url = f"https://api.dicebear.com/7.x/notionists/svg?seed={urllib.parse.quote(email)}"
            return {
                'active_user_email': email,
                'active_user_name': nombre,
                'active_user_plan': plan,
                'active_user_avatar': avatar_url
            }
    except Exception:
        pass
    return {}
