"""
Base de datos SQLite para la App de Torneos de Basket.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "torneos.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabla de torneos (antes de equipos por FK)
    c.execute("""
        CREATE TABLE IF NOT EXISTS torneos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            activo INTEGER DEFAULT 1
        )
    """)
    # Tabla de categorías dinámicas
    c.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)
    # Insertar categorías por defecto si la tabla está vacía
    cats_exist = c.execute("SELECT COUNT(*) as n FROM categorias").fetchone()
    if cats_exist['n'] == 0:
        for cat in ['U13', 'U15', 'U17', 'Primera']:
            c.execute("INSERT INTO categorias (nombre) VALUES (?)", (cat,))
    c.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            rama TEXT NOT NULL CHECK(rama IN ('Masculino','Femenino')),
            categoria TEXT NOT NULL,
            logo_url TEXT,
            torneo_id INTEGER,
            FOREIGN KEY (torneo_id) REFERENCES torneos(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            dorsal INTEGER NOT NULL,
            equipo_id INTEGER NOT NULL,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id) ON DELETE CASCADE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_local_id INTEGER NOT NULL,
            equipo_visitante_id INTEGER NOT NULL,
            fecha TEXT,
            estado TEXT NOT NULL DEFAULT 'Pendiente'
                CHECK(estado IN ('Pendiente','En curso','Finalizado')),
            FOREIGN KEY (equipo_local_id) REFERENCES equipos(id),
            FOREIGN KEY (equipo_visitante_id) REFERENCES equipos(id)
        )
    """)
    # Tablas para estadísticas (Fase 2+)
    c.execute("""
        CREATE TABLE IF NOT EXISTS estadisticas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER NOT NULL,
            jugador_id INTEGER NOT NULL,
            pts INTEGER DEFAULT 0,
            reb_of INTEGER DEFAULT 0,
            reb_def INTEGER DEFAULT 0,
            asistencias INTEGER DEFAULT 0,
            recuperos INTEGER DEFAULT 0,
            perdidas INTEGER DEFAULT 0,
            faltas INTEGER DEFAULT 0,
            FOREIGN KEY (partido_id) REFERENCES partidos(id),
            FOREIGN KEY (jugador_id) REFERENCES jugadores(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER NOT NULL,
            jugador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor INTEGER DEFAULT 0,
            cuarto INTEGER DEFAULT 1,
            timestamp TEXT,
            FOREIGN KEY (partido_id) REFERENCES partidos(id),
            FOREIGN KEY (jugador_id) REFERENCES jugadores(id)
        )
    """)
    # Tabla de puntaje por cuartos
    c.execute("""
        CREATE TABLE IF NOT EXISTS puntaje_cuartos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER NOT NULL,
            equipo_id INTEGER NOT NULL,
            cuarto INTEGER NOT NULL,
            puntos INTEGER DEFAULT 0,
            FOREIGN KEY (partido_id) REFERENCES partidos(id),
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
    """)
    # Tabla de tiempo de juego por jugador por partido
    c.execute("""
        CREATE TABLE IF NOT EXISTS tiempo_juego (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER NOT NULL,
            jugador_id INTEGER NOT NULL,
            ingreso_timestamp REAL,
            egreso_timestamp REAL,
            segundos_jugados REAL DEFAULT 0,
            en_cancha INTEGER DEFAULT 0,
            FOREIGN KEY (partido_id) REFERENCES partidos(id),
            FOREIGN KEY (jugador_id) REFERENCES jugadores(id)
        )
    """)
    # Tabla de usuarios
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'mesero'
                CHECK(rol IN ('admin','mesero'))
        )
    """)
    # Insertar admin por defecto si no existe
    admin_exists = c.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
    if not admin_exists:
        import hashlib
        pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO usuarios (username, password, nombre, rol) VALUES (?,?,?,?)",
                  ("admin", pwd_hash, "Administrador", "admin"))
    conn.commit()
    conn.close()


# --- TIEMPO DE JUEGO ---
def ingresar_jugador_cancha(partido_id, jugador_id, timestamp):
    """Marca un jugador como en cancha."""
    conn = get_connection()
    # Si ya está en cancha, no hacer nada
    existing = conn.execute(
        "SELECT id FROM tiempo_juego WHERE partido_id=? AND jugador_id=? AND en_cancha=1",
        (partido_id, jugador_id)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO tiempo_juego (partido_id, jugador_id, ingreso_timestamp, en_cancha) VALUES (?,?,?,1)",
            (partido_id, jugador_id, timestamp)
        )
        conn.commit()
    conn.close()


def sacar_jugador_cancha(partido_id, jugador_id, timestamp):
    """Saca un jugador de cancha y registra el tiempo jugado."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, ingreso_timestamp FROM tiempo_juego WHERE partido_id=? AND jugador_id=? AND en_cancha=1",
        (partido_id, jugador_id)
    ).fetchone()
    if row:
        segundos = timestamp - row['ingreso_timestamp']
        conn.execute(
            "UPDATE tiempo_juego SET en_cancha=0, egreso_timestamp=?, segundos_jugados=? WHERE id=?",
            (timestamp, segundos, row['id'])
        )
        conn.commit()
    conn.close()


def obtener_en_cancha(partido_id, equipo_id):
    """Devuelve los IDs de jugadores en cancha para un equipo."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT tj.jugador_id FROM tiempo_juego tj
        JOIN jugadores j ON tj.jugador_id = j.id
        WHERE tj.partido_id=? AND j.equipo_id=? AND tj.en_cancha=1
    """, (partido_id, equipo_id)).fetchall()
    conn.close()
    return [r['jugador_id'] for r in rows]


def obtener_tiempo_total(partido_id, jugador_id):
    """Tiempo total jugado en segundos (suma de todos los períodos)."""
    conn = get_connection()
    # Tiempo de períodos cerrados
    row = conn.execute(
        "SELECT COALESCE(SUM(segundos_jugados), 0) as total FROM tiempo_juego WHERE partido_id=? AND jugador_id=? AND en_cancha=0",
        (partido_id, jugador_id)
    ).fetchone()
    total = row['total']
    # Si está en cancha ahora, sumar desde ingreso
    activo = conn.execute(
        "SELECT ingreso_timestamp FROM tiempo_juego WHERE partido_id=? AND jugador_id=? AND en_cancha=1",
        (partido_id, jugador_id)
    ).fetchone()
    conn.close()
    if activo:
        import time as _time
        total += _time.time() - activo['ingreso_timestamp']
    return total


def sacar_todos_de_cancha(partido_id, timestamp):
    """Saca a todos los jugadores de cancha (al finalizar partido)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, jugador_id, ingreso_timestamp FROM tiempo_juego WHERE partido_id=? AND en_cancha=1",
        (partido_id,)
    ).fetchall()
    for r in rows:
        segundos = timestamp - r['ingreso_timestamp']
        conn.execute(
            "UPDATE tiempo_juego SET en_cancha=0, egreso_timestamp=?, segundos_jugados=? WHERE id=?",
            (timestamp, segundos, r['id'])
        )
    conn.commit()
    conn.close()


def obtener_cuartos_jugados(partido_id, jugador_id):
    """Devuelve la cantidad de cuartos distintos en los que el jugador registró eventos."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(DISTINCT cuarto) as total FROM eventos WHERE partido_id=? AND jugador_id=?",
        (partido_id, jugador_id)
    ).fetchone()
    conn.close()
    return row['total'] if row else 0


# --- EQUIPOS ---
def agregar_equipo(nombre, rama, categoria, logo_url=None, torneo_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO equipos (nombre, rama, categoria, logo_url, torneo_id) VALUES (?,?,?,?,?)",
        (nombre, rama, categoria, logo_url, torneo_id),
    )
    conn.commit()
    equipo_id = c.lastrowid
    conn.close()
    return equipo_id


def listar_equipos(rama=None, categoria=None, torneo_id=None):
    conn = get_connection()
    query = """
        SELECT e.*, COALESCE(t.nombre, 'Sin torneo') as torneo_nombre
        FROM equipos e
        LEFT JOIN torneos t ON e.torneo_id = t.id
        WHERE 1=1
    """
    params = []
    if rama:
        query += " AND e.rama = ?"
        params.append(rama)
    if categoria:
        query += " AND e.categoria = ?"
        params.append(categoria)
    if torneo_id:
        query += " AND e.torneo_id = ?"
        params.append(torneo_id)
    query += " ORDER BY e.nombre"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_equipo(equipo_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def eliminar_equipo(equipo_id):
    conn = get_connection()
    conn.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    conn.commit()
    conn.close()


# --- JUGADORES ---
def agregar_jugador(nombre, dorsal, equipo_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO jugadores (nombre, dorsal, equipo_id) VALUES (?,?,?)",
        (nombre, dorsal, equipo_id),
    )
    conn.commit()
    jug_id = c.lastrowid
    conn.close()
    return jug_id


def listar_jugadores(equipo_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jugadores WHERE equipo_id = ? ORDER BY dorsal", (equipo_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def eliminar_jugador(jugador_id):
    conn = get_connection()
    conn.execute("DELETE FROM jugadores WHERE id = ?", (jugador_id,))
    conn.commit()
    conn.close()


# --- PARTIDOS ---
def crear_partido(local_id, visitante_id, fecha):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO partidos (equipo_local_id, equipo_visitante_id, fecha) VALUES (?,?,?)",
        (local_id, visitante_id, fecha),
    )
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return pid


def listar_partidos(estado=None):
    conn = get_connection()
    query = """
        SELECT p.*, el.nombre as local_nombre, ev.nombre as visitante_nombre,
               el.rama, el.categoria
        FROM partidos p
        JOIN equipos el ON p.equipo_local_id = el.id
        JOIN equipos ev ON p.equipo_visitante_id = ev.id
    """
    params = []
    if estado:
        query += " WHERE p.estado = ?"
        params.append(estado)
    query += " ORDER BY p.fecha DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_partido(partido_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT p.*, el.nombre as local_nombre, ev.nombre as visitante_nombre,
               el.rama, el.categoria, el.logo_url as local_logo, ev.logo_url as visitante_logo
        FROM partidos p
        JOIN equipos el ON p.equipo_local_id = el.id
        JOIN equipos ev ON p.equipo_visitante_id = ev.id
        WHERE p.id = ?
    """, (partido_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_estado_partido(partido_id, estado):
    conn = get_connection()
    conn.execute("UPDATE partidos SET estado = ? WHERE id = ?", (estado, partido_id))
    conn.commit()
    conn.close()


# --- EVENTOS ---
def registrar_evento(partido_id, jugador_id, tipo, valor=0, cuarto=1):
    import datetime
    conn = get_connection()
    conn.execute(
        "INSERT INTO eventos (partido_id, jugador_id, tipo, valor, cuarto, timestamp) VALUES (?,?,?,?,?,?)",
        (partido_id, jugador_id, tipo, valor, cuarto, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def obtener_ultimos_eventos(partido_id, limit=5):
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.*, j.nombre as jugador_nombre, j.dorsal,
               eq.nombre as equipo_nombre
        FROM eventos e
        JOIN jugadores j ON e.jugador_id = j.id
        JOIN equipos eq ON j.equipo_id = eq.id
        WHERE e.partido_id = ?
        ORDER BY e.id DESC LIMIT ?
    """, (partido_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def borrar_ultimo_evento(partido_id):
    conn = get_connection()
    last = conn.execute(
        "SELECT id FROM eventos WHERE partido_id = ? ORDER BY id DESC LIMIT 1",
        (partido_id,)
    ).fetchone()
    if last:
        conn.execute("DELETE FROM eventos WHERE id = ?", (last["id"],))
        conn.commit()
    conn.close()


# --- ESTADÍSTICAS AGREGADAS ---
def obtener_stats_partido(partido_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT j.id as jugador_id, j.nombre, j.dorsal, j.equipo_id,
            COALESCE(SUM(CASE WHEN e.tipo IN ('+1','+2','+3') THEN e.valor ELSE 0 END), 0) as pts,
            COALESCE(SUM(CASE WHEN e.tipo = 'Rebote Ofensivo' THEN 1 ELSE 0 END), 0) as reb_of,
            COALESCE(SUM(CASE WHEN e.tipo = 'Rebote Defensivo' THEN 1 ELSE 0 END), 0) as reb_def,
            COALESCE(SUM(CASE WHEN e.tipo = 'Asistencia' THEN 1 ELSE 0 END), 0) as asistencias,
            COALESCE(SUM(CASE WHEN e.tipo = 'Recupero' THEN 1 ELSE 0 END), 0) as recuperos,
            COALESCE(SUM(CASE WHEN e.tipo = 'Pérdida' THEN 1 ELSE 0 END), 0) as perdidas,
            COALESCE(SUM(CASE WHEN e.tipo = 'Falta' THEN 1 ELSE 0 END), 0) as faltas
        FROM jugadores j
        LEFT JOIN eventos e ON j.id = e.jugador_id AND e.partido_id = ?
        WHERE j.equipo_id IN (
            SELECT equipo_local_id FROM partidos WHERE id = ?
            UNION
            SELECT equipo_visitante_id FROM partidos WHERE id = ?
        )
        GROUP BY j.id
        ORDER BY j.equipo_id, j.dorsal
    """, (partido_id, partido_id, partido_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_puntos_equipo(partido_id, equipo_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(e.valor), 0) as total
        FROM eventos e
        JOIN jugadores j ON e.jugador_id = j.id
        WHERE e.partido_id = ? AND j.equipo_id = ? AND e.tipo IN ('+1','+2','+3')
    """, (partido_id, equipo_id)).fetchone()
    conn.close()
    return row["total"] if row else 0


# --- PUNTAJE POR CUARTOS ---
def guardar_puntaje_cuarto(partido_id, equipo_id, cuarto, puntos):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM puntaje_cuartos WHERE partido_id=? AND equipo_id=? AND cuarto=?",
        (partido_id, equipo_id, cuarto)
    ).fetchone()
    if existing:
        conn.execute("UPDATE puntaje_cuartos SET puntos=? WHERE id=?", (puntos, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO puntaje_cuartos (partido_id, equipo_id, cuarto, puntos) VALUES (?,?,?,?)",
            (partido_id, equipo_id, cuarto, puntos)
        )
    conn.commit()
    conn.close()


def obtener_puntaje_cuartos(partido_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM puntaje_cuartos WHERE partido_id = ? ORDER BY equipo_id, cuarto",
        (partido_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- USUARIOS ---
def verificar_usuario(username, password):
    import hashlib
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE username=? AND password=?",
        (username, pwd_hash)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def crear_usuario(username, password, nombre, rol='mesero'):
    import hashlib
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?,?,?,?)",
            (username, pwd_hash, nombre, rol)
        )
        conn.commit()
        uid = c.lastrowid
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None


def listar_usuarios():
    conn = get_connection()
    rows = conn.execute("SELECT id, username, nombre, rol FROM usuarios ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def eliminar_usuario(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM usuarios WHERE id = ? AND username != 'admin'", (user_id,))
    conn.commit()
    conn.close()


# --- TORNEOS ---
def crear_torneo(nombre, fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO torneos (nombre, fecha_inicio, fecha_fin) VALUES (?,?,?)",
        (nombre, fecha_inicio, fecha_fin)
    )
    conn.commit()
    tid = c.lastrowid
    conn.close()
    return tid


def listar_torneos(solo_activos=False):
    conn = get_connection()
    query = "SELECT * FROM torneos"
    if solo_activos:
        query += " WHERE activo = 1"
    query += " ORDER BY id DESC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def activar_desactivar_torneo(torneo_id, activo):
    conn = get_connection()
    conn.execute("UPDATE torneos SET activo=? WHERE id=?", (activo, torneo_id))
    conn.commit()
    conn.close()


def eliminar_torneo(torneo_id):
    conn = get_connection()
    conn.execute("DELETE FROM torneos WHERE id = ?", (torneo_id,))
    conn.commit()
    conn.close()


# --- CATEGORÍAS DINÁMICAS ---
def listar_categorias():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def agregar_categoria(nombre):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre.strip(),))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def eliminar_categoria(cat_id):
    conn = get_connection()
    conn.execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
