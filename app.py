"""
app.py — Interfaz Streamlit CVRP Puntarenas · Florida Bebidas
Tema: tonos rosados / rose-pink
"""
 
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from solver import (
    solve, CANTONES, DEMAND, DIST, CAPACITY,
    DEMAND_IMPERIAL, DEMAND_PILSEN, DEMAND_TROPICAL,
    JORNADA_MIN, RELOAD_MIN,
)
 
# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="CVRP · Puntarenas",
    page_icon="🌺",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ── CSS: paleta rosada ────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Fondo general */
  [data-testid="stAppViewContainer"] {
      background: linear-gradient(135deg, #fff0f5 0%, #fce4ec 50%, #fdf2f8 100%);
  }
  [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #f8bbd0 0%, #f48fb1 100%);
  }
  [data-testid="stSidebar"] * {
      color: #4a0e2a !important;
  }
 
  /* Header principal */
  .main-header {
      background: linear-gradient(135deg, #e91e63 0%, #ad1457 60%, #880e4f 100%);
      padding: 2rem 2.5rem;
      border-radius: 16px;
      margin-bottom: 1.5rem;
      box-shadow: 0 8px 32px rgba(233,30,99,0.25);
  }
  .main-header h1 {
      color: #fff !important;
      font-size: 2.2rem;
      font-weight: 800;
      margin: 0;
      letter-spacing: -0.5px;
  }
  .main-header p {
      color: #fce4ec !important;
      margin: 0.3rem 0 0;
      font-size: 1rem;
  }
 
  /* Tarjetas KPI */
  .kpi-card {
      background: white;
      border-radius: 14px;
      padding: 1.2rem 1.5rem;
      box-shadow: 0 4px 20px rgba(233,30,99,0.12);
      border-left: 5px solid #e91e63;
      transition: transform 0.2s;
  }
  .kpi-card:hover { transform: translateY(-3px); }
  .kpi-number {
      font-size: 2.4rem;
      font-weight: 800;
      color: #c2185b;
      line-height: 1;
  }
  .kpi-label {
      font-size: 0.82rem;
      color: #ad1457;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      margin-top: 0.3rem;
  }
 
  /* Sección de tablas */
  .section-title {
      font-size: 1.2rem;
      font-weight: 700;
      color: #880e4f;
      border-bottom: 3px solid #f48fb1;
      padding-bottom: 0.4rem;
      margin: 1.5rem 0 0.8rem;
  }
 
  /* Badges */
  .badge-dedicated {
      background: #fce4ec;
      color: #c2185b;
      border: 1px solid #f48fb1;
      border-radius: 20px;
      padding: 2px 10px;
      font-size: 0.75rem;
      font-weight: 700;
  }
  .badge-normal {
      background: #f3e5f5;
      color: #6a1b9a;
      border: 1px solid #ce93d8;
      border-radius: 20px;
      padding: 2px 10px;
      font-size: 0.75rem;
      font-weight: 700;
  }
 
  /* Dataframes */
  .stDataFrame { border-radius: 10px; overflow: hidden; }
 
  /* Botones */
  .stButton > button {
      background: linear-gradient(135deg, #e91e63, #c2185b);
      color: white;
      border: none;
      border-radius: 8px;
      font-weight: 700;
      padding: 0.5rem 1.5rem;
  }
  .stButton > button:hover {
      background: linear-gradient(135deg, #ad1457, #880e4f);
  }
 
  /* Expander */
  .streamlit-expanderHeader {
      background: #fce4ec !important;
      border-radius: 8px !important;
      color: #880e4f !important;
      font-weight: 700 !important;
  }
 
  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
      background: #fce4ec;
      border-radius: 10px;
      padding: 4px;
  }
  .stTabs [data-baseweb="tab"] {
      color: #ad1457;
      font-weight: 600;
  }
  .stTabs [aria-selected="true"] {
      background: #e91e63 !important;
      color: white !important;
      border-radius: 8px;
  }
 
  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-thumb { background: #f48fb1; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)
 
 
# ── Resolver ──────────────────────────────────────────────────────────────────
@st.cache_data
def get_solution():
    return solve()
 
result = get_solution()
trips  = result["trips"]
trucks = result["trucks"]
 
 
# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🌺 CVRP · Provincia de Puntarenas</h1>
  <p>Distribución semanal · Florida Bebidas (FIFCO) · Imperial · Pilsen · Tropical</p>
</div>
""", unsafe_allow_html=True)
 
 
# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
kpis = [
    (sum(DEMAND.values()), "pallets / semana", c1),
    (len(trips),           "trips totales",    c2),
    (len(trucks),          "camiones físicos", c3),
    (f"{result['total_km']:,.0f}", "km totales", c4),
    (sum(1 for tk in trucks if any(t.is_dedicated() for t in tk.trips)),
     "camiones dedicados", c5),
]
for val, label, col in kpis:
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-number">{val}</div>
      <div class="kpi-label">{label}</div>
    </div>""", unsafe_allow_html=True)
 
st.markdown("<br>", unsafe_allow_html=True)
 
 
# ── Coordenadas geográficas de los cantones ───────────────────────────────────
COORDS = {
    0:  (9.9781,  -84.8319),   # CD Puntarenas (ciudad)
    1:  (9.9781,  -84.8319),   # Puntarenas
    2:  (9.9903,  -84.6644),   # Esparza
    3:  (9.1669,  -83.3304),   # Buenos Aires
    4:  (10.0783, -84.6381),   # Montes de Oro
    5:  (9.0794,  -83.4799),   # Osa
    6:  (9.4297,  -84.1629),   # Quepos
    7:  (8.6373,  -83.1818),   # Golfito
    8:  (8.9027,  -82.9609),   # Coto Brus
    9:  (9.5188,  -84.3327),   # Parrita
    10: (8.4735,  -83.0289),   # Corredores
    11: (9.5793,  -84.6475),   # Garabito
    12: (10.2989, -84.8263),   # Monteverde
    13: (8.5338,  -83.3006),   # Puerto Jiménez
}
 
# ── Tabs principales ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Demanda & Cantones",
    "🚛 Trips",
    "🔧 Camiones",
    "📐 Modelo CVRP",
    "🗺️ Mapa de Rutas",
])
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DEMANDA
# ══════════════════════════════════════════════════════════════════════════════
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DEMANDA
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_left, col_right = st.columns([1, 1])
 
    with col_left:
        st.markdown('<div class="section-title">Demanda por cantón (pallets/semana)</div>',
                    unsafe_allow_html=True)
        rows = []
        for nodo, canton in CANTONES.items():
            if nodo == 0:
                continue
            d = DEMAND[nodo]
            rows.append({
                "Nodo": nodo,
                "Cantón": canton,
                "Imperial (50%)": DEMAND_IMPERIAL[nodo],
                "Pilsen (25%)": DEMAND_PILSEN[nodo],
                "Tropical (25%)": DEMAND_TROPICAL[nodo],
                "Total": d,
                "Full-loads (24)": d // CAPACITY,
                "Residuo": d % CAPACITY,
            })
        df_demand = pd.DataFrame(rows)
        st.dataframe(
            df_demand.style
                .background_gradient(subset=["Total"], cmap="RdPu")
                .format({"Total": "{:,}"}),
            use_container_width=True, hide_index=True,
        )
 
    with col_right:
        st.markdown('<div class="section-title">Distribución de demanda</div>',
                    unsafe_allow_html=True)
        fig_bar = px.bar(
            df_demand, x="Cantón", y="Total",
            color="Total",
            color_continuous_scale=["#fce4ec", "#e91e63", "#880e4f"],
            labels={"Total": "Pallets/semana"},
        )
        fig_bar.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_tickangle=-40,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=False,
            font_color="#880e4f",
        )
        st.plotly_chart(fig_bar, use_container_width=True)
 
        # Pie productos
        fig_pie = go.Figure(go.Pie(
            labels=["Imperial 50%", "Pilsen 25%", "Tropical 25%"],
            values=[195, 98, 98],
            hole=0.5,
            marker_colors=["#e91e63", "#f48fb1", "#f8bbd0"],
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            font_color="#880e4f",
            showlegend=True,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRIPS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">Detalle de cada trip</div>',
                unsafe_allow_html=True)
 
    trip_rows = []
    for idx, trip in enumerate(trips, 1):
        ruta_str = " → ".join(
            ["CD"] + [CANTONES[n] for n in trip.route] + ["CD"]
        )
        dedicated = "⚠ Dedicado" if trip.is_dedicated() else "Normal"
        trip_rows.append({
            "Trip": idx,
            "Ruta": ruta_str,
            "Paradas": len(trip.route),
            "Carga (pallets)": trip.load,
            "Dist. (km)": round(trip.distance_km, 1),
            "Duración (min)": round(trip.duration_min, 1),
            "Duración (h)": round(trip.duration_min / 60, 2),
            "Tipo": dedicated,
        })
    df_trips = pd.DataFrame(trip_rows)
 
    def color_tipo(val):
        if "Dedicado" in str(val):
            return "background-color:#fce4ec; color:#c2185b; font-weight:700"
        return "background-color:#f3e5f5; color:#6a1b9a"
 
    st.dataframe(
        df_trips.style
            .applymap(color_tipo, subset=["Tipo"])
            .background_gradient(subset=["Dist. (km)"], cmap="RdPu"),
        use_container_width=True, hide_index=True,
    )
 
    # Gráfico duración de trips
    st.markdown('<div class="section-title">Duración de trips vs límite jornada</div>',
                unsafe_allow_html=True)
    fig_trip_dur = go.Figure()
    colors = ["#e91e63" if t.is_dedicated() else "#f48fb1" for t in trips]
    fig_trip_dur.add_trace(go.Bar(
        x=[f"Trip {i+1}" for i in range(len(trips))],
        y=[round(t.duration_min, 1) for t in trips],
        marker_color=colors,
        name="Duración (min)",
    ))
    fig_trip_dur.add_hline(
        y=JORNADA_MIN, line_dash="dash",
        line_color="#880e4f", line_width=2,
        annotation_text="Límite 8 h (480 min)",
        annotation_font_color="#880e4f",
    )
    fig_trip_dur.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        font_color="#880e4f",
        yaxis_title="Minutos",
    )
    st.plotly_chart(fig_trip_dur, use_container_width=True)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CAMIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">Asignación de trips a camiones (bin-packing 8 h)</div>',
                unsafe_allow_html=True)
 
    truck_rows = []
    for tk in trucks:
        is_ded = any(t.is_dedicated() for t in tk.trips)
        trips_str = " | ".join(
            " → ".join(["CD"] + [CANTONES[n] for n in t.route] + ["CD"])
            for t in tk.trips
        )
        truck_rows.append({
            "Camión": tk.truck_id,
            "# Trips": len(tk.trips),
            "Tiempo total (min)": round(tk.total_time_min(), 1),
            "Tiempo total (h)": round(tk.total_time_min() / 60, 2),
            "% Jornada": f"{tk.total_time_min()/JORNADA_MIN*100:.0f}%",
            "Km totales": round(tk.total_distance_km(), 1),
            "Pallets totales": tk.total_pallets(),
            "Tipo": "⚠ Dedicado" if is_ded else "Multi-trip",
            "Trips (rutas)": trips_str,
        })
    df_trucks = pd.DataFrame(truck_rows)
 
    def color_truck_tipo(val):
        if "Dedicado" in str(val):
            return "background-color:#fce4ec; color:#c2185b; font-weight:700"
        return "background-color:#e8f5e9; color:#2e7d32"
 
    st.dataframe(
        df_trucks.style
            .applymap(color_truck_tipo, subset=["Tipo"])
            .background_gradient(subset=["Km totales"], cmap="RdPu"),
        use_container_width=True, hide_index=True,
    )
 
    # Gantt de camiones
    st.markdown('<div class="section-title">Utilización de jornada por camión</div>',
                unsafe_allow_html=True)
 
    gantt_data = []
    for tk in trucks:
        cursor = 0
        for i, trip in enumerate(tk.trips):
            gantt_data.append({
                "Camión": f"Camión {tk.truck_id}",
                "Inicio": cursor,
                "Fin": cursor + trip.duration_min,
                "Trip": f"Trip {trips.index(trip)+1}",
            })
            cursor += trip.duration_min + RELOAD_MIN
 
    df_gantt = pd.DataFrame(gantt_data)
    if not df_gantt.empty:
        fig_gantt = px.timeline(
            df_gantt,
            x_start="Inicio", x_end="Fin", y="Camión",
            color="Trip",
            color_discrete_sequence=px.colors.sequential.RdPu,
            title="",
        )
        # Convertir a minutos (plotly timeline usa datetime internamente)
        # Usar bar chart horizontal en su lugar
        fig_h = go.Figure()
        palette = px.colors.sequential.RdPu
        for _, row in df_gantt.iterrows():
            fig_h.add_trace(go.Bar(
                y=[row["Camión"]],
                x=[row["Fin"] - row["Inicio"]],
                base=[row["Inicio"]],
                orientation="h",
                name=row["Trip"],
                marker_color=palette[hash(row["Trip"]) % len(palette)],
                text=row["Trip"],
                textposition="inside",
            ))
        fig_h.add_vline(x=JORNADA_MIN, line_dash="dash",
                        line_color="#880e4f", line_width=2)
        fig_h.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            barmode="stack",
            showlegend=False,
            xaxis_title="Minutos",
            font_color="#880e4f",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_h, use_container_width=True)
 
    # Mapa de calor km por camión
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="section-title">Km por camión</div>',
                    unsafe_allow_html=True)
        fig_km = px.bar(
            df_trucks, x="Camión", y="Km totales",
            color="Km totales",
            color_continuous_scale=["#fce4ec", "#e91e63", "#880e4f"],
        )
        fig_km.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            font_color="#880e4f",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_km, use_container_width=True)
 
    with col_b:
        st.markdown('<div class="section-title">Pallets por camión</div>',
                    unsafe_allow_html=True)
        fig_pal = px.bar(
            df_trucks, x="Camión", y="Pallets totales",
            color="Pallets totales",
            color_continuous_scale=["#f3e5f5", "#ce93d8", "#6a1b9a"],
        )
        fig_pal.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            font_color="#880e4f",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_pal, use_container_width=True)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MODELO CVRP
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    col_m1, col_m2 = st.columns([1, 1])
 
    with col_m1:
        st.markdown('<div class="section-title">Variables de decisión</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        | Variable | Tipo | Descripción |
        |---|---|---|
        | `y(i,j)` | Entera ≥ 0 | Camiones que transitan el arco i→j |
        | `f(i,j)` | Continua ≥ 0 | Pallets transportados en el arco i→j |
        """)
 
        st.markdown('<div class="section-title">Función objetivo</div>',
                    unsafe_allow_html=True)
        st.latex(r"\min \; Z = \sum_{(i,j)\in A} \text{dist}(i,j) \cdot y(i,j)")
        st.caption("Minimiza la distancia total recorrida por toda la flota (km).")
 
    with col_m2:
        st.markdown('<div class="section-title">Restricciones</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        **① Balance de camiones** — flujo de camiones conservado en cada nodo:
        """)
        st.latex(r"\sum_j y(i,j) = \sum_j y(j,i) \quad \forall i")
 
        st.markdown("**② Balance de carga** — pallets entran − salen = demanda:")
        st.latex(r"\sum_j f(j,i) - \sum_j f(i,j) = d_i \quad \forall i \neq 0")
 
        st.markdown("**③ Carga total desde CD** — suma de todos los pallets despachados:")
        st.latex(r"\sum_j f(0,j) = D_{\text{total}}")
 
        st.markdown("**④ Capacidad por arco** *(restricción clave)*:")
        st.latex(r"f(i,j) \leq 24 \cdot y(i,j) \quad \forall (i,j)")
        st.info("⚡ Esta restricción garantiza que ningún camión transporte más de 24 pallets.")
 
    st.markdown('<div class="section-title">Parámetros operativos</div>',
                unsafe_allow_html=True)
    params_data = {
        "Parámetro": ["Capacidad camión", "Velocidad", "Tiempo/parada", "Tiempo/pallet",
                      "Reload entre trips", "Jornada"],
        "Valor": ["24 pallets", "40 km/h", "15 min", "3 min", "20 min", "8 h (480 min)"],
        "Uso": [
            "f(i,j) ≤ 24·y(i,j)",
            "km/vel×60 → duración trip",
            "+15 min por cantón visitado",
            "+3 min por pallet entregado",
            "Tiempo entre trips del mismo camión",
            "Bin-packing: suma trips + reloads ≤ 480",
        ],
    }
    st.dataframe(pd.DataFrame(params_data), use_container_width=True, hide_index=True)
 
    st.markdown('<div class="section-title">Fórmula de duración de trip</div>',
                unsafe_allow_html=True)
    st.latex(
        r"T_{\text{trip}} = \frac{\text{km\_total}}{40} \times 60 "
        r"+ \text{paradas} \times 15 "
        r"+ \text{pallets} \times 3 \quad [\text{minutos}]"
    )
 
    with st.expander("📊 Matriz de distancias (km)"):
        labels = [CANTONES[i] for i in range(14)]
        df_dist = pd.DataFrame(DIST, index=labels, columns=labels)
        st.dataframe(
            df_dist.style.background_gradient(cmap="RdPu", axis=None),
            use_container_width=True,
        )
 
 
# ── Sidebar: resumen ejecutivo ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌺 Resumen Ejecutivo")
    st.markdown("---")
    st.metric("Demanda total", f"{sum(DEMAND.values())} pallets")
    st.metric("Trips generados", len(trips))
    st.metric("Camiones requeridos", len(trucks))
    st.metric("Km totales", f"{result['total_km']:,.0f} km")
    st.metric("Camiones dedicados",
              sum(1 for tk in trucks if any(t.is_dedicated() for t in tk.trips)))
    st.markdown("---")
    st.markdown("**Provincia:** Puntarenas")
    st.markdown("**Cantones:** 13")
    st.markdown("**Productos:** Imperial · Pilsen · Tropical")
    st.markdown("**Capacidad:** 24 pallets/camión")
    st.markdown("---")
    st.markdown("**Hitos completados:**")
    st.markdown("✅ Hito 1 — Demand & Dataset")
    st.markdown("✅ Hito 2 — Modelo CVRP")
    st.markdown("✅ Hito 3 — Trips (Nivel 1)")
    st.markdown("✅ Hito 4 — Trucks (Nivel 2)")
    st.markdown("---")
    st.caption("II-1122 · Clase 13 · UCR Sede Alajuela")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MAPA DE RUTAS
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-title">Mapa de rutas por camión — Provincia de Puntarenas</div>',
                unsafe_allow_html=True)
 
    # Paleta de colores para camiones
    TRUCK_COLORS = [
        "#e91e63", "#9c27b0", "#3f51b5", "#00bcd4", "#009688",
        "#ff5722", "#795548", "#607d8b", "#f44336", "#2196f3",
        "#4caf50", "#ff9800", "#673ab7", "#03a9f4",
    ]
 
    # ── Selector de camión ────────────────────────────────────────────────────
    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        truck_options = ["Todos los camiones"] + [f"Camión {tk.truck_id}" for tk in trucks]
        selected_truck = st.selectbox("Filtrar por camión:", truck_options)
 
    # ── Construir figura Plotly ───────────────────────────────────────────────
    fig_map = go.Figure()
 
    # Seleccionar camiones a mostrar
    if selected_truck == "Todos los camiones":
        trucks_to_show = trucks
    else:
        tid = int(selected_truck.split(" ")[1])
        trucks_to_show = [tk for tk in trucks if tk.truck_id == tid]
 
    for tk in trucks_to_show:
        color = TRUCK_COLORS[(tk.truck_id - 1) % len(TRUCK_COLORS)]
        is_ded = any(t.is_dedicated() for t in tk.trips)
 
        for trip_idx, trip in enumerate(tk.trips):
            full_route = [0] + trip.route + [0]
 
            lats = [COORDS[n][0] for n in full_route]
            lons = [COORDS[n][1] for n in full_route]
            names = [CANTONES[n] for n in full_route]
 
            # Texto de hover por segmento
            hover_texts = []
            for i, node in enumerate(full_route):
                pallets = trip.pallets_per_stop.get(node, 0)
                txt = f"<b>{CANTONES[node]}</b>"
                if node != 0:
                    txt += f"<br>Pallets: {pallets}"
                hover_texts.append(txt)
 
            label = f"Camión {tk.truck_id} — Trip {trip_idx+1}"
            if is_ded:
                label += " ⚠"
 
            # Línea de ruta
            fig_map.add_trace(go.Scattermapbox(
                lat=lats,
                lon=lons,
                mode="lines+markers",
                line=dict(width=3, color=color),
                marker=dict(size=10, color=color),
                text=hover_texts,
                hoverinfo="text",
                name=label,
            ))
 
            # Flechas de dirección (puntos intermedios con texto)
            for i in range(len(full_route) - 1):
                mid_lat = (lats[i] + lats[i+1]) / 2
                mid_lon = (lons[i] + lons[i+1]) / 2
                fig_map.add_trace(go.Scattermapbox(
                    lat=[mid_lat],
                    lon=[mid_lon],
                    mode="markers",
                    marker=dict(size=6, color=color, opacity=0.5),
                    hoverinfo="skip",
                    showlegend=False,
                ))
 
    # ── Nodos (cantones) ──────────────────────────────────────────────────────
    node_lats, node_lons, node_texts, node_sizes, node_colors = [], [], [], [], []
    for nodo, nombre in CANTONES.items():
        lat, lon = COORDS[nodo]
        node_lats.append(lat)
        node_lons.append(lon)
        demand_val = DEMAND.get(nodo, 0)
        node_texts.append(
            f"<b>{nombre}</b><br>Demanda: {demand_val} pallets"
        )
        if nodo == 0:
            node_sizes.append(22)
            node_colors.append("#880e4f")
        else:
            node_sizes.append(14 + demand_val // 10)
            node_colors.append("#fce4ec")
 
    fig_map.add_trace(go.Scattermapbox(
        lat=node_lats,
        lon=node_lons,
        mode="markers+text",
        marker=dict(size=node_sizes, color=node_colors,
                    line=dict(width=2, color="#e91e63")),
        text=[CANTONES[n] for n in range(14)],
        textposition="top right",
        textfont=dict(size=11, color="#880e4f"),
        hovertext=node_texts,
        hoverinfo="text",
        name="Cantones",
    ))
 
    fig_map.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=9.3, lon=-83.9),
            zoom=7,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        legend=dict(
            bgcolor="rgba(255,240,245,0.9)",
            bordercolor="#f48fb1",
            borderwidth=1,
            font=dict(color="#880e4f", size=11),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )
 
    st.plotly_chart(fig_map, use_container_width=True)
 
    # ── Tabla de coordenadas / resumen de rutas ───────────────────────────────
    st.markdown('<div class="section-title">Detalle de rutas mostradas</div>',
                unsafe_allow_html=True)
 
    route_rows = []
    for tk in trucks_to_show:
        color_hex = TRUCK_COLORS[(tk.truck_id - 1) % len(TRUCK_COLORS)]
        is_ded = any(t.is_dedicated() for t in tk.trips)
        for trip_idx, trip in enumerate(tk.trips):
            ruta_str = " → ".join(["CD"] + [CANTONES[n] for n in trip.route] + ["CD"])
            paradas = ", ".join(
                f"{CANTONES[n]} ({trip.pallets_per_stop.get(n,0)} p)"
                for n in trip.route
            )
            route_rows.append({
                "Camión": tk.truck_id,
                "Trip": trip_idx + 1,
                "Ruta": ruta_str,
                "Paradas (pallets)": paradas,
                "Km": round(trip.distance_km, 1),
                "Min": round(trip.duration_min, 1),
                "Carga": trip.load,
                "Tipo": "⚠ Dedicado" if is_ded else "Multi-trip",
            })
 
    if route_rows:
        df_routes = pd.DataFrame(route_rows)
        st.dataframe(df_routes, use_container_width=True, hide_index=True)
 





