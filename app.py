"""
🏀 Torneos de Basket - App de Gestión Completa
"""
import streamlit as st
import os
import time
import datetime
import pandas as pd
from urllib.parse import quote
from db import (
    init_db, agregar_equipo, listar_equipos, obtener_equipo, eliminar_equipo,
    agregar_jugador, listar_jugadores, eliminar_jugador,
    crear_partido, listar_partidos, obtener_partido, actualizar_estado_partido,
    registrar_evento, obtener_ultimos_eventos, borrar_ultimo_evento,
    obtener_stats_partido, obtener_puntos_equipo,
    guardar_puntaje_cuarto, obtener_puntaje_cuartos,
    ingresar_jugador_cancha, sacar_jugador_cancha, obtener_en_cancha,
    obtener_tiempo_total, sacar_todos_de_cancha, obtener_cuartos_jugados,
    verificar_usuario, crear_usuario, listar_usuarios, eliminar_usuario,
    crear_torneo, listar_torneos, activar_desactivar_torneo, eliminar_torneo,
    listar_categorias, agregar_categoria, eliminar_categoria,
)

st.set_page_config(page_title="Torneos de Basket", page_icon="🏀", layout="wide")

# Inicializar BD
init_db()

LOGOS_DIR = os.path.join(os.path.dirname(__file__), "logos")
os.makedirs(LOGOS_DIR, exist_ok=True)

RAMAS = ["Masculino", "Femenino"]

# Categorías dinámicas desde la BD
def obtener_categorias_nombres():
    cats = listar_categorias()
    return [c['nombre'] for c in cats] if cats else ["U13", "U15", "U17", "Primera"]

CATEGORIAS = obtener_categorias_nombres()

# ─── SISTEMA DE LOGIN ───
if "usuario_logueado" not in st.session_state:
    st.session_state.usuario_logueado = None

if st.session_state.usuario_logueado is None:
    st.title("🏀 Torneos de Basket")
    st.subheader("Iniciar Sesión")
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", type="primary"):
            user = verificar_usuario(username, password)
            if user:
                st.session_state.usuario_logueado = user
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.caption("Usuario por defecto: **admin** / Contraseña: **admin123**")
    st.stop()

# Usuario logueado
usuario = st.session_state.usuario_logueado
es_admin = usuario['rol'] == 'admin'

# ─── SIDEBAR NAV ───
st.sidebar.title("🏀 Torneos de Basket")
st.sidebar.markdown(f"👤 **{usuario['nombre']}** ({usuario['rol']})")
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.usuario_logueado = None
    st.rerun()

# Menú según rol
paginas_disponibles = ["📋 Inscripción", "🏟️ Partidos", "🎮 Mesa de Control", "📊 Resultados y Posiciones", "📄 Exportar"]
if es_admin:
    paginas_disponibles.insert(0, "🏠 Dashboard")

pagina = st.sidebar.radio(
    "Navegación",
    paginas_disponibles
)


# ═══════════════════════════════════════════════════════════
# PÁGINA 0: DASHBOARD (solo admin)
# ═══════════════════════════════════════════════════════════
if pagina == "🏠 Dashboard":
    st.title("🏠 Dashboard de Administración")

    tab_torneos, tab_categorias, tab_usuarios = st.tabs(["🏆 Torneos", "📂 Categorías", "👥 Usuarios"])

    # --- Tab: Torneos ---
    with tab_torneos:
        st.subheader("Gestión de Torneos")
        with st.form("form_torneo", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                t_nombre = st.text_input("Nombre del torneo")
            with col2:
                t_inicio = st.date_input("Fecha inicio", value=datetime.date.today())
            with col3:
                t_fin = st.date_input("Fecha fin", value=datetime.date.today() + datetime.timedelta(days=7))
            if st.form_submit_button("Crear Torneo", type="primary"):
                if t_nombre.strip():
                    tid = crear_torneo(t_nombre.strip(), t_inicio.isoformat(), t_fin.isoformat())
                    st.success(f"✅ Torneo '{t_nombre}' creado (ID: {tid})")
                else:
                    st.error("El nombre es obligatorio.")

        torneos = listar_torneos()
        if torneos:
            st.markdown("### Torneos existentes")
            for t in torneos:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                estado = "🟢 Activo" if t['activo'] else "🔴 Inactivo"
                col1.write(f"**{t['nombre']}**")
                col2.write(f"{t.get('fecha_inicio', '')} → {t.get('fecha_fin', '')} — {estado}")
                with col3:
                    if t['activo']:
                        if st.button("⏸️", key=f"desact_t_{t['id']}", help="Desactivar"):
                            activar_desactivar_torneo(t['id'], 0)
                            st.rerun()
                    else:
                        if st.button("▶️", key=f"act_t_{t['id']}", help="Activar"):
                            activar_desactivar_torneo(t['id'], 1)
                            st.rerun()
                with col4:
                    if st.button("🗑️", key=f"del_t_{t['id']}", help="Eliminar"):
                        eliminar_torneo(t['id'])
                        st.rerun()
        else:
            st.info("No hay torneos creados.")

    # --- Tab: Categorías ---
    with tab_categorias:
        st.subheader("Gestión de Categorías")
        st.caption("Agregá o eliminá categorías para los equipos.")
        with st.form("form_categoria", clear_on_submit=True):
            nueva_cat = st.text_input("Nombre de la nueva categoría")
            if st.form_submit_button("Agregar Categoría", type="primary"):
                if nueva_cat.strip():
                    ok = agregar_categoria(nueva_cat.strip())
                    if ok:
                        st.success(f"✅ Categoría '{nueva_cat}' agregada")
                    else:
                        st.error("Ya existe una categoría con ese nombre.")
                else:
                    st.error("El nombre es obligatorio.")

        cats = listar_categorias()
        if cats:
            st.markdown("### Categorías actuales")
            for cat in cats:
                col1, col2 = st.columns([4, 1])
                col1.write(f"📂 **{cat['nombre']}**")
                with col2:
                    if st.button("🗑️", key=f"del_cat_{cat['id']}", help="Eliminar"):
                        eliminar_categoria(cat['id'])
                        st.rerun()

    # --- Tab: Usuarios ---
    with tab_usuarios:
        st.subheader("Gestión de Usuarios")
        with st.form("form_usuario", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                u_nombre = st.text_input("Nombre completo")
            with col2:
                u_username = st.text_input("Usuario")
            with col3:
                u_password = st.text_input("Contraseña", type="password")
            with col4:
                u_rol = st.selectbox("Rol", ["mesero", "admin"])
            if st.form_submit_button("Crear Usuario", type="primary"):
                if u_nombre.strip() and u_username.strip() and u_password:
                    uid = crear_usuario(u_username.strip(), u_password, u_nombre.strip(), u_rol)
                    if uid:
                        st.success(f"✅ Usuario '{u_username}' creado")
                    else:
                        st.error("Ya existe un usuario con ese nombre de usuario.")
                else:
                    st.error("Completá todos los campos.")

        usuarios = listar_usuarios()
        if usuarios:
            st.markdown("### Usuarios registrados")
            for u in usuarios:
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"👤 **{u['nombre']}** ({u['username']})")
                col2.write(f"Rol: {u['rol']}")
                with col3:
                    if u['username'] != 'admin':
                        if st.button("🗑️", key=f"del_u_{u['id']}", help="Eliminar"):
                            eliminar_usuario(u['id'])
                            st.rerun()
                    else:
                        st.write("🔒")


# ═══════════════════════════════════════════════════════════
# PÁGINA 1: INSCRIPCIÓN
# ═══════════════════════════════════════════════════════════
elif pagina == "📋 Inscripción":
    st.title("📋 Inscripción de Equipos")

    tab_equipo, tab_jugadores, tab_listado = st.tabs(["Nuevo Equipo", "Agregar Jugadores", "Equipos Inscriptos"])

    # --- Tab: Nuevo Equipo ---
    with tab_equipo:
        st.subheader("Registrar Equipo")
        with st.form("form_equipo", clear_on_submit=True):
            nombre = st.text_input("Nombre del equipo")
            col1, col2 = st.columns(2)
            with col1:
                rama = st.selectbox("Rama", RAMAS)
            with col2:
                categoria = st.selectbox("Categoría", CATEGORIAS)
            logo_file = st.file_uploader("Logo del equipo", type=["png", "jpg", "jpeg", "webp"])
            submitted = st.form_submit_button("Inscribir Equipo", type="primary")

            if submitted:
                if not nombre.strip():
                    st.error("El nombre del equipo es obligatorio.")
                else:
                    logo_url = None
                    if logo_file:
                        ext = logo_file.name.split(".")[-1]
                        fname = f"{nombre.strip().replace(' ', '_')}_{rama}_{categoria}.{ext}"
                        path = os.path.join(LOGOS_DIR, fname)
                        with open(path, "wb") as f:
                            f.write(logo_file.getbuffer())
                        logo_url = path
                    eid = agregar_equipo(nombre.strip(), rama, categoria, logo_url)
                    st.success(f"✅ Equipo '{nombre}' inscripto en {rama} - {categoria} (ID: {eid})")

    # --- Tab: Agregar Jugadores ---
    with tab_jugadores:
        st.subheader("Agregar Jugadores a un Equipo")
        equipos = listar_equipos()
        if not equipos:
            st.info("Primero inscribí al menos un equipo.")
        else:
            opciones = {f"{e['nombre']} ({e['rama']} - {e['categoria']})": e['id'] for e in equipos}
            seleccion = st.selectbox("Equipo", list(opciones.keys()))
            equipo_id = opciones[seleccion]

            with st.form("form_jugador", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    jug_nombre = st.text_input("Nombre del jugador")
                with col2:
                    dorsal = st.number_input("Dorsal", min_value=0, max_value=99, step=1)
                if st.form_submit_button("Agregar Jugador", type="primary"):
                    if jug_nombre.strip():
                        agregar_jugador(jug_nombre.strip(), int(dorsal), equipo_id)
                        st.success(f"✅ {jug_nombre} (#{dorsal}) agregado")
                    else:
                        st.error("El nombre es obligatorio.")

            # --- Carga masiva por Excel ---
            st.markdown("---")
            st.markdown("**📥 Carga masiva desde Excel**")
            st.caption("El archivo debe tener columnas: `nombre` y `dorsal`")
            excel_file = st.file_uploader("Subir Excel (.xlsx)", type=["xlsx"], key=f"excel_{equipo_id}")
            if excel_file:
                try:
                    df_excel = pd.read_excel(excel_file, engine="openpyxl")
                    # Normalizar nombres de columnas
                    df_excel.columns = [c.strip().lower() for c in df_excel.columns]
                    if 'nombre' not in df_excel.columns or 'dorsal' not in df_excel.columns:
                        st.error("El Excel debe tener columnas 'nombre' y 'dorsal'.")
                    else:
                        df_excel = df_excel.dropna(subset=['nombre', 'dorsal'])
                        st.dataframe(df_excel[['nombre', 'dorsal']], hide_index=True)
                        if st.button("✅ Importar jugadores", key=f"import_{equipo_id}"):
                            count = 0
                            for _, row in df_excel.iterrows():
                                agregar_jugador(str(row['nombre']).strip(), int(row['dorsal']), equipo_id)
                                count += 1
                            st.success(f"✅ {count} jugadores importados correctamente")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error al leer el Excel: {e}")

            # Mostrar roster actual
            jugadores = listar_jugadores(equipo_id)
            if jugadores:
                st.markdown("**Roster actual:**")
                for j in jugadores:
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"#{j['dorsal']} - {j['nombre']}")
                    if col2.button("❌", key=f"del_jug_{j['id']}"):
                        eliminar_jugador(j['id'])
                        st.rerun()

    # --- Tab: Listado ---
    with tab_listado:
        st.subheader("Equipos Inscriptos")
        col1, col2 = st.columns(2)
        with col1:
            filtro_rama = st.selectbox("Filtrar por Rama", ["Todas"] + RAMAS, key="filtro_rama")
        with col2:
            filtro_cat = st.selectbox("Filtrar por Categoría", ["Todas"] + CATEGORIAS, key="filtro_cat")

        r = filtro_rama if filtro_rama != "Todas" else None
        c = filtro_cat if filtro_cat != "Todas" else None
        equipos = listar_equipos(rama=r, categoria=c)

        if not equipos:
            st.info("No hay equipos inscriptos con esos filtros.")
        else:
            for eq in equipos:
                with st.expander(f"🏀 {eq['nombre']} — {eq['rama']} / {eq['categoria']}"):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if eq['logo_url'] and os.path.exists(eq['logo_url']):
                            st.image(eq['logo_url'], width=100)
                        else:
                            st.write("Sin logo")
                    with col2:
                        jugadores = listar_jugadores(eq['id'])
                        if jugadores:
                            df = pd.DataFrame(jugadores)[['dorsal', 'nombre']]
                            df.columns = ['#', 'Jugador']
                            st.dataframe(df, hide_index=True, use_container_width=True)
                        else:
                            st.write("Sin jugadores cargados")
                    if st.button(f"🗑️ Eliminar equipo", key=f"del_eq_{eq['id']}"):
                        eliminar_equipo(eq['id'])
                        st.rerun()


# ═══════════════════════════════════════════════════════════
# PÁGINA 2: PARTIDOS
# ═══════════════════════════════════════════════════════════
elif pagina == "🏟️ Partidos":
    st.title("🏟️ Gestión de Partidos")

    tab_crear, tab_listar = st.tabs(["Crear Partido", "Partidos Programados"])

    with tab_crear:
        st.subheader("Programar Partido")
        col1, col2 = st.columns(2)
        with col1:
            rama_p = st.selectbox("Rama", RAMAS, key="rama_partido")
        with col2:
            cat_p = st.selectbox("Categoría", CATEGORIAS, key="cat_partido")

        equipos_filtrados = listar_equipos(rama=rama_p, categoria=cat_p)

        if len(equipos_filtrados) < 2:
            st.warning(f"Se necesitan al menos 2 equipos inscriptos en {rama_p} - {cat_p}.")
        else:
            opciones = {e['nombre']: e['id'] for e in equipos_filtrados}
            nombres = list(opciones.keys())
            col1, col2 = st.columns(2)
            with col1:
                local = st.selectbox("Equipo Local", nombres, key="local")
            with col2:
                visitante = st.selectbox("Equipo Visitante", nombres, key="visitante")
            fecha = st.date_input("Fecha", value=datetime.date.today())

            if local == visitante:
                st.error("Los equipos deben ser diferentes.")
            elif st.button("Crear Partido", type="primary"):
                pid = crear_partido(opciones[local], opciones[visitante], fecha.isoformat())
                st.success(f"✅ Partido creado: {local} vs {visitante} (ID: {pid})")

    with tab_listar:
        st.subheader("Partidos")
        partidos = listar_partidos()
        if not partidos:
            st.info("No hay partidos programados.")
        else:
            for p in partidos:
                estado_emoji = {"Pendiente": "⏳", "En curso": "🔴", "Finalizado": "✅"}.get(p['estado'], "")
                st.write(f"{estado_emoji} **{p['local_nombre']}** vs **{p['visitante_nombre']}** — {p['rama']}/{p['categoria']} — {p['fecha']} — *{p['estado']}*")


# ═══════════════════════════════════════════════════════════
# PÁGINA 3: MESA DE CONTROL
# ═══════════════════════════════════════════════════════════
elif pagina == "🎮 Mesa de Control":
    st.title("🎮 Mesa de Control")

    partidos = listar_partidos()
    partidos_activos = [p for p in partidos if p['estado'] in ('Pendiente', 'En curso')]

    if not partidos_activos:
        st.info("No hay partidos pendientes o en curso.")
    else:
        opciones_p = {
            f"{p['local_nombre']} vs {p['visitante_nombre']} ({p['rama']}/{p['categoria']}) - {p['estado']}": p['id']
            for p in partidos_activos
        }
        sel_partido = st.selectbox("Seleccionar Partido", list(opciones_p.keys()))
        partido_id = opciones_p[sel_partido]
        partido = obtener_partido(partido_id)

        # Estado del partido
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            if partido['estado'] == 'Pendiente':
                if st.button("▶️ Iniciar Partido", type="primary"):
                    actualizar_estado_partido(partido_id, "En curso")
                    st.rerun()
        with col_ctrl2:
            if partido['estado'] == 'En curso':
                if st.button("⏹️ Finalizar Partido", type="secondary"):
                    sacar_todos_de_cancha(partido_id, time.time())
                    actualizar_estado_partido(partido_id, "Finalizado")
                    st.rerun()
        with col_ctrl3:
            # Selector de cuarto
            if "cuarto_actual" not in st.session_state:
                st.session_state.cuarto_actual = 1
            cuarto = st.selectbox("Cuarto", [1, 2, 3, 4], index=st.session_state.cuarto_actual - 1, key="sel_cuarto")
            st.session_state.cuarto_actual = cuarto

        # Cronómetro (simple, basado en session_state)
        st.markdown("---")
        if "crono_start" not in st.session_state:
            st.session_state.crono_start = None
            st.session_state.crono_elapsed = 0
            st.session_state.crono_running = False

        col_t1, col_t2, col_t3, col_t4 = st.columns([2, 1, 1, 1])
        with col_t1:
            if st.session_state.crono_running and st.session_state.crono_start:
                elapsed = st.session_state.crono_elapsed + (time.time() - st.session_state.crono_start)
            else:
                elapsed = st.session_state.crono_elapsed
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            st.markdown(f"### ⏱️ {mins:02d}:{secs:02d}")
        with col_t2:
            if st.button("▶️ Play"):
                if not st.session_state.crono_running:
                    st.session_state.crono_start = time.time()
                    st.session_state.crono_running = True
                    st.rerun()
        with col_t3:
            if st.button("⏸️ Pausa"):
                if st.session_state.crono_running:
                    st.session_state.crono_elapsed += time.time() - st.session_state.crono_start
                    st.session_state.crono_running = False
                    st.rerun()
        with col_t4:
            if st.button("🔄 Reset"):
                st.session_state.crono_start = None
                st.session_state.crono_elapsed = 0
                st.session_state.crono_running = False
                st.rerun()

        # Marcador
        st.markdown("---")
        pts_local = obtener_puntos_equipo(partido_id, partido['equipo_local_id'])
        pts_visit = obtener_puntos_equipo(partido_id, partido['equipo_visitante_id'])

        col_score = st.columns([2, 1, 2])
        with col_score[0]:
            if partido['local_logo'] and os.path.exists(partido['local_logo']):
                st.image(partido['local_logo'], width=60)
            st.markdown(f"### {partido['local_nombre']}")
        with col_score[1]:
            st.markdown(f"## {pts_local} - {pts_visit}")
        with col_score[2]:
            if partido['visitante_logo'] and os.path.exists(partido['visitante_logo']):
                st.image(partido['visitante_logo'], width=60)
            st.markdown(f"### {partido['visitante_nombre']}")

        # --- Tableros de los dos equipos ---
        if partido['estado'] == 'En curso':
            ACCIONES = [
                ("+1", "+1", 1), ("+2", "+2", 2), ("+3", "+3", 3),
                ("RO", "Reb.Of", 0), ("RD", "Reb.Def", 0),
                ("AST", "Asistencia", 0), ("REC", "Recupero", 0),
                ("PER", "Pérdida", 0), ("FLT", "Falta", 0),
            ]

            # Obtener jugadores en cancha de ambos equipos
            local_id = partido['equipo_local_id']
            visit_id = partido['equipo_visitante_id']
            en_cancha_local = obtener_en_cancha(partido_id, local_id)
            en_cancha_visit = obtener_en_cancha(partido_id, visit_id)
            jug_local = listar_jugadores(local_id)
            jug_visit = listar_jugadores(visit_id)
            jug_local_cancha = [j for j in jug_local if j['id'] in en_cancha_local]
            jug_visit_cancha = [j for j in jug_visit if j['id'] in en_cancha_visit]

            # Inicializar jugador seleccionado en session_state
            if "jug_seleccionado" not in st.session_state:
                st.session_state.jug_seleccionado = None

            # ═══ LAYOUT: LOCAL | STATS | VISITANTE ═══
            col_izq, col_centro, col_der = st.columns([2, 3, 2])

            # --- COLUMNA IZQUIERDA: Jugadores LOCAL ---
            with col_izq:
                st.markdown(f"**{partido['local_nombre']}**")
                if not jug_local_cancha:
                    st.info("Sin jugadores en cancha")
                for j in jug_local_cancha:
                    is_selected = st.session_state.jug_seleccionado == j['id']
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(f"#{j['dorsal']} {j['nombre']}", key=f"sel_loc_{partido_id}_{j['id']}",
                                 use_container_width=True, type=btn_type):
                        st.session_state.jug_seleccionado = j['id']
                        st.rerun()

            # --- COLUMNA DERECHA: Jugadores VISITANTE ---
            with col_der:
                st.markdown(f"**{partido['visitante_nombre']}**")
                if not jug_visit_cancha:
                    st.info("Sin jugadores en cancha")
                for j in jug_visit_cancha:
                    is_selected = st.session_state.jug_seleccionado == j['id']
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(f"#{j['dorsal']} {j['nombre']}", key=f"sel_vis_{partido_id}_{j['id']}",
                                 use_container_width=True, type=btn_type):
                        st.session_state.jug_seleccionado = j['id']
                        st.rerun()

            # --- COLUMNA CENTRO: Botones de estadísticas ---
            with col_centro:
                jug_sel = st.session_state.jug_seleccionado
                if jug_sel:
                    # Buscar nombre del jugador seleccionado
                    nombre_sel = ""
                    for j in jug_local_cancha + jug_visit_cancha:
                        if j['id'] == jug_sel:
                            nombre_sel = f"#{j['dorsal']} {j['nombre']}"
                            break
                    if nombre_sel:
                        st.markdown(f"#### 📊 {nombre_sel}")
                    else:
                        st.warning("Jugador no está en cancha. Seleccioná otro.")
                        st.session_state.jug_seleccionado = None
                        jug_sel = None

                if jug_sel:
                    # Fila 1: Puntos
                    row1 = st.columns(3)
                    for i, (label, tipo, valor) in enumerate(ACCIONES[:3]):
                        with row1[i]:
                            if st.button(f"🏀 {label}", key=f"stat_{partido_id}_{jug_sel}_{tipo}",
                                         use_container_width=True):
                                registrar_evento(partido_id, jug_sel, tipo, valor, st.session_state.cuarto_actual)
                                st.rerun()
                    # Fila 2: Rebotes + Asistencia
                    row2 = st.columns(3)
                    for i, (label, tipo, valor) in enumerate(ACCIONES[3:6]):
                        with row2[i]:
                            if st.button(f"📊 {label}", key=f"stat_{partido_id}_{jug_sel}_{tipo}",
                                         use_container_width=True):
                                registrar_evento(partido_id, jug_sel, tipo, valor, st.session_state.cuarto_actual)
                                st.rerun()
                    # Fila 3: Recupero, Pérdida, Falta
                    row3 = st.columns(3)
                    for i, (label, tipo, valor) in enumerate(ACCIONES[6:9]):
                        with row3[i]:
                            if st.button(f"⚠️ {label}", key=f"stat_{partido_id}_{jug_sel}_{tipo}",
                                         use_container_width=True):
                                registrar_evento(partido_id, jug_sel, tipo, valor, st.session_state.cuarto_actual)
                                st.rerun()
                else:
                    st.markdown("#### 📊 Estadísticas")
                    st.info("👈 Seleccioná un jugador para registrar estadísticas 👉")

            # ═══ GESTIÓN DE CANCHA + TABLAS (abajo) ═══
            st.markdown("---")
            col_tabla_loc, col_tabla_vis = st.columns(2)

            for col_tabla, (equipo_id, equipo_nombre, jug_equipo, en_cancha_ids) in zip(
                [col_tabla_loc, col_tabla_vis],
                [(local_id, partido['local_nombre'], jug_local, en_cancha_local),
                 (visit_id, partido['visitante_nombre'], jug_visit, en_cancha_visit)]
            ):
                with col_tabla:
                    jugadores_dentro = [j for j in jug_equipo if j['id'] in en_cancha_ids]

                    with st.expander(f"🔄 {equipo_nombre} — Cancha ({len(jugadores_dentro)}/5)", expanded=len(jugadores_dentro) == 0):
                        for jug in jug_equipo:
                            c1, c2 = st.columns([3, 1])
                            c1.write(f"#{jug['dorsal']} {jug['nombre']}")
                            if jug['id'] in en_cancha_ids:
                                if c2.button("⬇️", key=f"out_{partido_id}_{equipo_id}_{jug['id']}", help="Sacar"):
                                    sacar_jugador_cancha(partido_id, jug['id'], time.time())
                                    st.rerun()
                            else:
                                if len(en_cancha_ids) < 5:
                                    if c2.button("⬆️", key=f"in_{partido_id}_{equipo_id}_{jug['id']}", help="Meter"):
                                        ingresar_jugador_cancha(partido_id, jug['id'], time.time())
                                        st.rerun()

                    # Tabla de stats
                    stats = obtener_stats_partido(partido_id)
                    stats_dict = {s['jugador_id']: s for s in stats}
                    tabla_data = []
                    for jug in jug_equipo:
                        s = stats_dict.get(jug['id'], {})
                        faltas = s.get('faltas', 0) if isinstance(s, dict) else 0
                        tiempo_seg = obtener_tiempo_total(partido_id, jug['id'])
                        t_min = int(tiempo_seg // 60)
                        t_sec = int(tiempo_seg % 60)
                        en = "🟢" if jug['id'] in en_cancha_ids else "⚪"
                        tabla_data.append({
                            '': en,
                            '#': jug['dorsal'],
                            'Jugador': jug['nombre'],
                            'PTS': s.get('pts', 0) if isinstance(s, dict) else 0,
                            'RO': s.get('reb_of', 0) if isinstance(s, dict) else 0,
                            'RD': s.get('reb_def', 0) if isinstance(s, dict) else 0,
                            'AST': s.get('asistencias', 0) if isinstance(s, dict) else 0,
                            'REC': s.get('recuperos', 0) if isinstance(s, dict) else 0,
                            'PER': s.get('perdidas', 0) if isinstance(s, dict) else 0,
                            'FLT': f"{'🔴' if faltas >= 5 else ''}{faltas}",
                            'CJ': obtener_cuartos_jugados(partido_id, jug['id']),
                            '⏱️': f"{t_min:02d}:{t_sec:02d}",
                        })
                    st.dataframe(pd.DataFrame(tabla_data), hide_index=True, use_container_width=True, height=250)

        # --- Log de Eventos ---
        st.subheader("📝 Log de Eventos (últimos 5)")
        eventos = obtener_ultimos_eventos(partido_id, 5)
        if eventos:
            for ev in eventos:
                st.write(f"🔹 **{ev['equipo_nombre']}** — #{ev['dorsal']} {ev['jugador_nombre']} — {ev['tipo']} (Q{ev['cuarto']})")
            if st.button("↩️ Deshacer última acción"):
                borrar_ultimo_evento(partido_id)
                st.rerun()
        else:
            st.info("Sin eventos registrados.")


# ═══════════════════════════════════════════════════════════
# PÁGINA 4: RESULTADOS Y POSICIONES
# ═══════════════════════════════════════════════════════════
elif pagina == "📊 Resultados y Posiciones":
    st.title("📊 Resultados y Tabla de Posiciones")

    col1, col2 = st.columns(2)
    with col1:
        rama_sel = st.selectbox("Rama", RAMAS, key="pos_rama")
    with col2:
        cat_sel = st.selectbox("Categoría", CATEGORIAS, key="pos_cat")

    # Resultados
    st.subheader("Resultados")
    partidos = listar_partidos(estado="Finalizado")
    partidos_filtrados = [p for p in partidos if p['rama'] == rama_sel and p['categoria'] == cat_sel]

    if not partidos_filtrados:
        st.info("No hay partidos finalizados en esta rama/categoría.")
    else:
        for p in partidos_filtrados:
            pts_l = obtener_puntos_equipo(p['id'], p['equipo_local_id'])
            pts_v = obtener_puntos_equipo(p['id'], p['equipo_visitante_id'])
            st.write(f"✅ **{p['local_nombre']}** {pts_l} - {pts_v} **{p['visitante_nombre']}** ({p['fecha']})")

    # Tabla de posiciones (reglas FIBA: 2 pts ganar, 1 pt perder)
    st.subheader("Tabla de Posiciones")
    equipos = listar_equipos(rama=rama_sel, categoria=cat_sel)

    if equipos and partidos_filtrados:
        tabla = {}
        for eq in equipos:
            tabla[eq['id']] = {
                'Equipo': eq['nombre'],
                'PJ': 0, 'PG': 0, 'PP': 0,
                'PF': 0, 'PC': 0, 'DIF': 0, 'PTS': 0
            }

        for p in partidos_filtrados:
            lid = p['equipo_local_id']
            vid = p['equipo_visitante_id']
            pts_l = obtener_puntos_equipo(p['id'], lid)
            pts_v = obtener_puntos_equipo(p['id'], vid)

            if lid in tabla:
                tabla[lid]['PJ'] += 1
                tabla[lid]['PF'] += pts_l
                tabla[lid]['PC'] += pts_v
                if pts_l > pts_v:
                    tabla[lid]['PG'] += 1
                    tabla[lid]['PTS'] += 2
                else:
                    tabla[lid]['PP'] += 1
                    tabla[lid]['PTS'] += 1

            if vid in tabla:
                tabla[vid]['PJ'] += 1
                tabla[vid]['PF'] += pts_v
                tabla[vid]['PC'] += pts_l
                if pts_v > pts_l:
                    tabla[vid]['PG'] += 1
                    tabla[vid]['PTS'] += 2
                else:
                    tabla[vid]['PP'] += 1
                    tabla[vid]['PTS'] += 1

        for eid in tabla:
            tabla[eid]['DIF'] = tabla[eid]['PF'] - tabla[eid]['PC']

        df_tabla = pd.DataFrame(tabla.values())
        df_tabla = df_tabla.sort_values(by=['PTS', 'DIF', 'PF'], ascending=False).reset_index(drop=True)
        df_tabla.index += 1
        df_tabla.index.name = "Pos"
        st.dataframe(df_tabla, use_container_width=True)
    else:
        st.info("No hay datos suficientes para armar la tabla.")


# ═══════════════════════════════════════════════════════════
# PÁGINA 5: EXPORTAR (PDF + WHATSAPP)
# ═══════════════════════════════════════════════════════════
elif pagina == "📄 Exportar":
    st.title("📄 Exportar Resultados")

    partidos = listar_partidos(estado="Finalizado")
    if not partidos:
        st.info("No hay partidos finalizados para exportar.")
    else:
        opciones_exp = {
            f"{p['local_nombre']} vs {p['visitante_nombre']} ({p['rama']}/{p['categoria']}) - {p['fecha']}": p['id']
            for p in partidos
        }
        sel = st.selectbox("Seleccionar Partido", list(opciones_exp.keys()))
        partido_id = opciones_exp[sel]
        partido = obtener_partido(partido_id)
        stats = obtener_stats_partido(partido_id)
        pts_local = obtener_puntos_equipo(partido_id, partido['equipo_local_id'])
        pts_visit = obtener_puntos_equipo(partido_id, partido['equipo_visitante_id'])

        st.subheader(f"{partido['local_nombre']} {pts_local} - {pts_visit} {partido['visitante_nombre']}")

        # Box Score
        st.markdown("### Box Score")
        for equipo_id, equipo_nombre in [
            (partido['equipo_local_id'], partido['local_nombre']),
            (partido['equipo_visitante_id'], partido['visitante_nombre'])
        ]:
            st.markdown(f"**{equipo_nombre}**")
            equipo_stats = [s for s in stats if s['equipo_id'] == equipo_id]
            if equipo_stats:
                df = pd.DataFrame(equipo_stats)
                df['cj'] = df['jugador_id'].apply(lambda jid: obtener_cuartos_jugados(partido_id, jid))
                df = df[['dorsal', 'nombre', 'pts', 'reb_of', 'reb_def', 'asistencias', 'recuperos', 'perdidas', 'faltas', 'cj']]
                df.columns = ['#', 'Jugador', 'PTS', 'RO', 'RD', 'AST', 'REC', 'PER', 'FLT', 'CJ']
                st.dataframe(df, hide_index=True, use_container_width=True)

        # Botón PDF
        st.markdown("---")
        if st.button("📥 Descargar Acta PDF", type="primary"):
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "ACTA DE PARTIDO", ln=True, align="C")
            pdf.ln(5)

            # Logos
            y_logos = pdf.get_y()
            if partido['local_logo'] and os.path.exists(partido['local_logo']):
                try:
                    pdf.image(partido['local_logo'], x=20, y=y_logos, w=25)
                except Exception:
                    pass
            if partido['visitante_logo'] and os.path.exists(partido['visitante_logo']):
                try:
                    pdf.image(partido['visitante_logo'], x=165, y=y_logos, w=25)
                except Exception:
                    pass

            pdf.set_y(y_logos)
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, f"{partido['local_nombre']}  {pts_local} - {pts_visit}  {partido['visitante_nombre']}", ln=True, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 8, f"{partido['rama']} - {partido['categoria']}  |  {partido['fecha']}", ln=True, align="C")
            pdf.ln(10)

            # Puntaje por cuartos
            cuartos = obtener_puntaje_cuartos(partido_id)
            if cuartos:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, "Puntaje por Cuartos", ln=True)
                pdf.set_font("Helvetica", "", 9)
                header = ["Equipo", "Q1", "Q2", "Q3", "Q4", "Total"]
                col_w = [50, 20, 20, 20, 20, 20]
                for i, h in enumerate(header):
                    pdf.cell(col_w[i], 7, h, 1, 0, "C")
                pdf.ln()
                for eid, ename in [(partido['equipo_local_id'], partido['local_nombre']),
                                    (partido['equipo_visitante_id'], partido['visitante_nombre'])]:
                    eq_cuartos = {c['cuarto']: c['puntos'] for c in cuartos if c['equipo_id'] == eid}
                    total = sum(eq_cuartos.values())
                    pdf.cell(col_w[0], 7, ename[:20], 1, 0)
                    for q in range(1, 5):
                        pdf.cell(col_w[q], 7, str(eq_cuartos.get(q, 0)), 1, 0, "C")
                    pdf.cell(col_w[5], 7, str(total), 1, 0, "C")
                    pdf.ln()
                pdf.ln(5)

            # Box Score en PDF
            for equipo_id, equipo_nombre in [
                (partido['equipo_local_id'], partido['local_nombre']),
                (partido['equipo_visitante_id'], partido['visitante_nombre'])
            ]:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, equipo_nombre, ln=True)
                pdf.set_font("Helvetica", "", 8)
                headers = ["#", "Jugador", "PTS", "RO", "RD", "AST", "REC", "PER", "FLT", "CJ"]
                widths = [10, 35, 14, 14, 14, 14, 14, 14, 14, 12]
                for i, h in enumerate(headers):
                    pdf.cell(widths[i], 6, h, 1, 0, "C")
                pdf.ln()
                equipo_stats = [s for s in stats if s['equipo_id'] == equipo_id]
                for s in equipo_stats:
                    cj = obtener_cuartos_jugados(partido_id, s['jugador_id'])
                    vals = [str(s['dorsal']), s['nombre'][:16], str(s['pts']),
                            str(s['reb_of']), str(s['reb_def']), str(s['asistencias']),
                            str(s['recuperos']), str(s['perdidas']), str(s['faltas']), str(cj)]
                    for i, v in enumerate(vals):
                        pdf.cell(widths[i], 6, v, 1, 0, "C" if i != 1 else "L")
                    pdf.ln()
                pdf.ln(5)

            pdf_bytes = bytes(pdf.output())
            st.download_button(
                "⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"acta_{partido['local_nombre']}_vs_{partido['visitante_nombre']}.pdf",
                mime="application/pdf"
            )

        # Botón WhatsApp
        st.markdown("---")
        msg = (
            f"🏀 *{partido['rama']} - {partido['categoria']}*\n"
            f"*{partido['local_nombre']}* {pts_local} - {pts_visit} *{partido['visitante_nombre']}*\n"
            f"📅 {partido['fecha']}"
        )
        wa_url = f"https://wa.me/?text={quote(msg)}"
        st.markdown(f"[📱 Enviar resultado por WhatsApp]({wa_url})")
