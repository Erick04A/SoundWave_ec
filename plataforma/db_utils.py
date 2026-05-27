import os
import pyodbc
from contextlib import contextmanager
from typing import List, Dict, Any, Union
from django.conf import settings

@contextmanager
def get_db_connection():
    db_config = settings.DATABASES.get('default', {})
    
    if db_config.get('ENGINE') == 'mssql' or os.environ.get('USE_SQL_SERVER', 'False').lower() == 'true':
        server = db_config.get('HOST', os.environ.get('DB_HOST', 'localhost'))
        database = db_config.get('NAME', os.environ.get('DB_NAME', 'SoundWaveDB'))
        username = db_config.get('USER', os.environ.get('DB_USER', 'sa'))
        password = db_config.get('PASSWORD', os.environ.get('DB_PASSWORD', ''))
        port = db_config.get('PORT', os.environ.get('DB_PORT', '1433'))
        driver = db_config.get('OPTIONS', {}).get('driver', os.environ.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server'))
        
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
    else:
        server = os.environ.get('DB_HOST', 'localhost')
        database = os.environ.get('DB_NAME', 'SoundWaveDB')
        username = os.environ.get('DB_USER', 'sa')
        password = os.environ.get('DB_PASSWORD', '')
        port = os.environ.get('DB_PORT', '1433')
        driver = os.environ.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
        
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )

    conn = None
    try:
        conn = pyodbc.connect(conn_str)
        yield conn
    except pyodbc.Error as e:
        print(f"[SoundWave DB Error] Error de conexión pyodbc: {e}")
        raise e
    finally:
        if conn:
            conn.close()


def execute_stored_procedure(sp_name: str, params: List[Any] = None) -> List[Dict[str, Any]]:
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


def execute_non_query(query: str, params: List[Any] = None) -> int:
    if params is None:
        params = []
        
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount


def execute_scalar(query: str, params: List[Any] = None) -> Any:
    if params is None:
        params = []
        
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else None
