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
)

st.set_page_config(page_title="Torneos de Basket", page_icon="🏀", layout="wide")

# Inicializar BD
init_db()

LOGOS_DIR = os.path.join(os.path.dirname(__file__), "logos")
os.makedirs(LOGOS_DIR, exist_ok=True)

RAMAS = ["Masculino", "Femenino"]
CATEGORIAS = ["U13", "U15", "U17", "Primera"]

# ─── SIDEBAR NAV ───
st.sidebar.title("🏀 Torneos de Basket")
pagina = st.sidebar.radio(
    "Navegación",
    ["📋 Inscripción", "🏟️ Partidos", "🎮 Mesa de Control", "📊 Resultados y Posiciones", "📄 Exportar"]
)


# ═══════════════════════════════════════════════════════════
# PÁGINA 1: INSCRIPCIÓN
# ═══════════════════════════════════════════════════════════
if pagina == "📋 Inscripción":
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
                ("RO", "Rebote Ofensivo", 0), ("RD", "Rebote Defensivo", 0),
                ("AST", "Asistencia", 0), ("REC", "Recupero", 0),
                ("PER", "Pérdida", 0), ("FLT", "Falta", 0),
            ]

            for equipo_id, equipo_nombre in [
                (partido['equipo_local_id'], partido['local_nombre']),
                (partido['equipo_visitante_id'], partido['visitante_nombre'])
            ]:
                st.markdown(f"### 📋 {equipo_nombre}")
                jugadores = listar_jugadores(equipo_id)
                if not jugadores:
                    st.warning("Sin jugadores cargados.")
                    continue

                # Obtener stats actuales para mostrar faltas
                stats = obtener_stats_partido(partido_id)
                stats_dict = {s['jugador_id']: s for s in stats}

                for jug in jugadores:
                    jug_stats = stats_dict.get(jug['id'], {})
                    faltas = jug_stats.get('faltas', 0) if isinstance(jug_stats, dict) else 0
                    pts = jug_stats.get('pts', 0) if isinstance(jug_stats, dict) else 0

                    falta_color = "🔴" if faltas >= 5 else ""
                    st.markdown(f"**#{jug['dorsal']} {jug['nombre']}** — {pts} pts — Faltas: {faltas} {falta_color}")

                    cols = st.columns(len(ACCIONES))
                    for i, (label, tipo, valor) in enumerate(ACCIONES):
                        with cols[i]:
                            if st.button(label, key=f"act_{partido_id}_{jug['id']}_{tipo}"):
                                registrar_evento(partido_id, jug['id'], tipo, valor, st.session_state.cuarto_actual)
                                st.rerun()
                st.markdown("---")

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
                df = df[['dorsal', 'nombre', 'pts', 'reb_of', 'reb_def', 'asistencias', 'recuperos', 'perdidas', 'faltas']]
                df.columns = ['#', 'Jugador', 'PTS', 'RO', 'RD', 'AST', 'REC', 'PER', 'FLT']
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
                headers = ["#", "Jugador", "PTS", "RO", "RD", "AST", "REC", "PER", "FLT"]
                widths = [10, 40, 15, 15, 15, 15, 15, 15, 15]
                for i, h in enumerate(headers):
                    pdf.cell(widths[i], 6, h, 1, 0, "C")
                pdf.ln()
                equipo_stats = [s for s in stats if s['equipo_id'] == equipo_id]
                for s in equipo_stats:
                    vals = [str(s['dorsal']), s['nombre'][:18], str(s['pts']),
                            str(s['reb_of']), str(s['reb_def']), str(s['asistencias']),
                            str(s['recuperos']), str(s['perdidas']), str(s['faltas'])]
                    for i, v in enumerate(vals):
                        pdf.cell(widths[i], 6, v, 1, 0, "C" if i != 1 else "L")
                    pdf.ln()
                pdf.ln(5)

            pdf_bytes = pdf.output()
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
