"""
🏀 Estadísticas Públicas - Torneos de Basket
Página pública para ver tablas de posiciones y estadísticas de partidos.
"""
import streamlit as st
import pandas as pd
from db import (
    init_db, listar_torneos, listar_equipos, listar_partidos, obtener_partido,
    obtener_stats_partido, obtener_puntos_equipo, obtener_cuartos_jugados,
    listar_jugadores, obtener_puntaje_cuartos, listar_categorias,
)

st.set_page_config(page_title="Torneos de Basket", page_icon="🏀", layout="wide")

# Inicializar BD
init_db()

# CSS para mejorar la presentación
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .stat-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    .highlight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .team-local { color: #1f77b4; font-weight: bold; }
    .team-visit { color: #ff7f0e; font-weight: bold; }
    .admin-link {
        position: fixed;
        top: 10px;
        right: 10px;
        background: #1f77b4;
        color: white;
        padding: 8px 15px;
        border-radius: 5px;
        text-decoration: none;
        font-size: 0.9rem;
        z-index: 1000;
    }
    .admin-link:hover {
        background: #145a8a;
    }
</style>
""", unsafe_allow_html=True)

# Link al panel de admin (centrado arriba)
st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <a href="/admin" target="_self" 
       style="background: #1f77b4; color: white; padding: 10px 25px; 
              border-radius: 8px; text-decoration: none; font-size: 1rem;
              display: inline-block;">
        🔐 Panel de Administración
    </a>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🏀 Torneos de Basket</p>', unsafe_allow_html=True)

# ═══ SELECTOR DE TORNEO ═══
torneos = listar_torneos(solo_activos=True)
if not torneos:
    st.warning("No hay torneos activos en este momento.")
    st.stop()

torneo_opts = {t['nombre']: t['id'] for t in torneos}
torneo_sel = st.selectbox("Seleccioná un Torneo", list(torneo_opts.keys()))
torneo_id = torneo_opts[torneo_sel]

# Tabs principales
tab_posiciones, tab_partidos = st.tabs(["📊 Tabla de Posiciones", "🏀 Partidos y Estadísticas"])

# ═══════════════════════════════════════════════════════════
# TAB 1: TABLA DE POSICIONES
# ═══════════════════════════════════════════════════════════
with tab_posiciones:
    st.markdown(f'<p class="sub-header">📊 Tabla de Posiciones — {torneo_sel}</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        rama_sel = st.selectbox("Rama", ["Masculino", "Femenino"], key="pos_rama")
    with col2:
        # Categorías dinámicas
        cats = listar_categorias()
        cat_nombres = [c['nombre'] for c in cats] if cats else ["U13", "U15", "U17", "Primera"]
        cat_sel = st.selectbox("Categoría", cat_nombres, key="pos_cat")
    
    # Obtener equipos del torneo filtrados
    equipos = listar_equipos(rama=rama_sel, categoria=cat_sel, torneo_id=torneo_id)
    partidos = listar_partidos()
    
    # Filtrar partidos del torneo
    partidos_torneo = []
    equipos_ids = {e['id'] for e in equipos}
    for p in partidos:
        if p['estado'] == 'Finalizado' and (p['equipo_local_id'] in equipos_ids or p['equipo_visitante_id'] in equipos_ids):
            partidos_torneo.append(p)
    
    if not equipos:
        st.info("No hay equipos inscriptos en esta categoría.")
    elif not partidos_torneo:
        st.info("No hay partidos finalizados aún.")
    else:
        # Calcular tabla de posiciones
        tabla = {}
        for eq in equipos:
            tabla[eq['id']] = {
                'Equipo': eq['nombre'],
                'PJ': 0, 'PG': 0, 'PP': 0,
                'PF': 0, 'PC': 0, 'DIF': 0, 'PTS': 0
            }
        
        for p in partidos_torneo:
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
        
        # Destacar los primeros 4
        def highlight_top4(row):
            if row.name <= 4:
                return ['background-color: #d4edda'] * len(row)
            return [''] * len(row)
        
        st.dataframe(df_tabla.style.apply(highlight_top4, axis=1), use_container_width=True)
        
        # Stats del torneo
        st.markdown("---")
        st.markdown('<p class="sub-header">📈 Estadísticas del Torneo</p>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Partidos Jugados", len(partidos_torneo))
        with col2:
            total_pts = sum(p['PF'] for p in tabla.values())
            st.metric("Puntos Anotados", total_pts)
        with col3:
            avg_pts = round(total_pts / len(partidos_torneo) / 2, 1) if partidos_torneo else 0
            st.metric("Promedio por Partido", avg_pts)
        with col4:
            st.metric("Equipos", len(equipos))

# ═══════════════════════════════════════════════════════════
# TAB 2: PARTIDOS Y ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════
with tab_partidos:
    st.markdown('<p class="sub-header">🏀 Partidos y Estadísticas</p>', unsafe_allow_html=True)
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        rama_part = st.selectbox("Rama", ["Masculino", "Femenino"], key="part_rama")
    with col2:
        cats = listar_categorias()
        cat_nombres = [c['nombre'] for c in cats] if cats else ["U13", "U15", "U17", "Primera"]
        cat_part = st.selectbox("Categoría", cat_nombres, key="part_cat")
    
    # Obtener partidos del torneo
    equipos_filtrados = listar_equipos(rama=rama_part, categoria=cat_part, torneo_id=torneo_id)
    equipos_f_ids = {e['id'] for e in equipos_filtrados}
    
    partidos_all = listar_partidos()
    partidos_disp = [p for p in partidos_all 
                     if p['equipo_local_id'] in equipos_f_ids or p['equipo_visitante_id'] in equipos_f_ids]
    
    if not partidos_disp:
        st.info("No hay partidos en esta categoría.")
    else:
        # Selector de partido
        part_opts = {}
        for p in partidos_disp:
            estado_emoji = {"Pendiente": "⏳", "En curso": "🔴", "Finalizado": "✅"}.get(p['estado'], "")
            label = f"{estado_emoji} {p['local_nombre']} vs {p['visitante_nombre']} — {p['fecha']} ({p['estado']})"
            part_opts[label] = p['id']
        
        part_sel = st.selectbox("Seleccioná un partido", list(part_opts.keys()))
        partido_id = part_opts[part_sel]
        partido = obtener_partido(partido_id)
        
        # Marcador
        pts_local = obtener_puntos_equipo(partido_id, partido['equipo_local_id'])
        pts_visit = obtener_puntos_equipo(partido_id, partido['equipo_visitante_id'])
        
        st.markdown("---")
        col_marc1, col_marc2, col_marc3 = st.columns([2, 1, 2])
        with col_marc1:
            st.markdown(f"<h2 class='team-local'>{partido['local_nombre']}</h2>", unsafe_allow_html=True)
        with col_marc2:
            st.markdown(f"<h1 style='text-align:center;'>{pts_local} - {pts_visit}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center;'>{partido['rama']} | {partido['categoria']}<br>{partido['fecha']}</p>", unsafe_allow_html=True)
        with col_marc3:
            st.markdown(f"<h2 class='team-visit'>{partido['visitante_nombre']}</h2>", unsafe_allow_html=True)
        
        # Si está finalizado, mostrar estadísticas completas
        if partido['estado'] == 'Finalizado':
            st.markdown("---")
            st.markdown('<p class="sub-header">⭐ Highlights del Partido</p>', unsafe_allow_html=True)
            
            stats = obtener_stats_partido(partido_id)
            
            if stats:
                # Encontrar máximos
                max_pts = max(stats, key=lambda x: x.get('pts', 0))
                max_ast = max(stats, key=lambda x: x.get('asistencias', 0))
                max_reb = max(stats, key=lambda x: x.get('reb_of', 0) + x.get('reb_def', 0))
                max_rec = max(stats, key=lambda x: x.get('recuperos', 0))
                
                col_h1, col_h2, col_h3, col_h4 = st.columns(4)
                with col_h1:
                    st.markdown(f"""
                    <div class='highlight-box'>
                        <h4>🏆 Máximo Anotador</h4>
                        <h3>#{max_pts['dorsal']} {max_pts['nombre']}</h3>
                        <p>{max_pts['pts']} puntos</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_h2:
                    st.markdown(f"""
                    <div class='highlight-box'>
                        <h4>🎯 Máximo Asistidor</h4>
                        <h3>#{max_ast['dorsal']} {max_ast['nombre']}</h3>
                        <p>{max_ast['asistencias']} asistencias</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_h3:
                    reb_tot = max_reb.get('reb_of', 0) + max_reb.get('reb_def', 0)
                    st.markdown(f"""
                    <div class='highlight-box'>
                        <h4>💪 Máximo Rebotero</h4>
                        <h3>#{max_reb['dorsal']} {max_reb['nombre']}</h3>
                        <p>{reb_tot} rebotes</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_h4:
                    st.markdown(f"""
                    <div class='highlight-box'>
                        <h4>⚡ Más Recuperos</h4>
                        <h3>#{max_rec['dorsal']} {max_rec['nombre']}</h3>
                        <p>{max_rec['recuperos']} recuperos</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Box Score
            st.markdown("---")
            st.markdown('<p class="sub-header">📋 Box Score</p>', unsafe_allow_html=True)
            
            col_box1, col_box2 = st.columns(2)
            
            for col_box, (equipo_id, equipo_nombre, es_local) in zip(
                [col_box1, col_box2],
                [(partido['equipo_local_id'], partido['local_nombre'], True),
                 (partido['equipo_visitante_id'], partido['visitante_nombre'], False)]
            ):
                with col_box:
                    color_class = "team-local" if es_local else "team-visit"
                    st.markdown(f"<h4 class='{color_class}'>{equipo_nombre}</h4>", unsafe_allow_html=True)
                    
                    equipo_stats = [s for s in stats if s.get('equipo_id') == equipo_id]
                    if equipo_stats:
                        df = pd.DataFrame(equipo_stats)
                        df['cj'] = df['jugador_id'].apply(lambda jid: obtener_cuartos_jugados(partido_id, jid))
                        df['reb_tot'] = df['reb_of'] + df['reb_def']
                        df = df[['dorsal', 'nombre', 'pts', 'reb_tot', 'reb_of', 'reb_def', 'asistencias', 'recuperos', 'perdidas', 'faltas', 'cj']]
                        df.columns = ['#', 'Jugador', 'PTS', 'REB', 'RO', 'RD', 'AST', 'REC', 'PER', 'FLT', 'CJ']
                        
                        # Destacar máximo anotador del equipo
                        def highlight_max_pts(row):
                            if row['PTS'] == df['PTS'].max() and row['PTS'] > 0:
                                return ['background-color: #fff3cd'] * len(row)
                            return [''] * len(row)
                        
                        st.dataframe(df.style.apply(highlight_max_pts, axis=1), 
                                   hide_index=True, use_container_width=True, height=350)
                        
                        # Totales del equipo
                        totales = df[['PTS', 'REB', 'RO', 'RD', 'AST', 'REC', 'PER', 'FLT']].sum()
                        st.markdown(f"**Totales:** PTS {totales['PTS']} | REB {totales['REB']} | AST {totales['AST']} | REC {totales['REC']}")
                    else:
                        st.info("Sin estadísticas registradas.")
            
            # Puntaje por cuartos
            cuartos = obtener_puntaje_cuartos(partido_id)
            if cuartos:
                st.markdown("---")
                st.markdown('<p class="sub-header">📊 Puntaje por Cuartos</p>', unsafe_allow_html=True)
                
                data_cuartos = []
                for eid, ename in [(partido['equipo_local_id'], partido['local_nombre']),
                                   (partido['equipo_visitante_id'], partido['visitante_nombre'])]:
                    eq_cuartos = {c['cuarto']: c['puntos'] for c in cuartos if c['equipo_id'] == eid}
                    total = sum(eq_cuartos.values())
                    data_cuartos.append({
                        'Equipo': ename,
                        'Q1': eq_cuartos.get(1, 0),
                        'Q2': eq_cuartos.get(2, 0),
                        'Q3': eq_cuartos.get(3, 0),
                        'Q4': eq_cuartos.get(4, 0),
                        'Total': total
                    })
                
                df_cuartos = pd.DataFrame(data_cuartos)
                st.dataframe(df_cuartos, hide_index=True, use_container_width=True)

# Footer
st.markdown("---")
st.caption("🏀 Estadísticas en vivo | Torneos de Basket")
