"""
app.py — CVRP Puntarenas · Florida Bebidas
Interfaz Streamlit con tema rosado, parámetros editables y botón Optimizar.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from solver import (
    solve,
    CANTONES, DEMAND_BASE, DIST,
    DEFAULT_CAPACITY, DEFAULT_SPEED_KMH,
    DEFAULT_MIN_PER_STOP, DEFAULT_MIN_PER_PAL,
    DEFAULT_RELOAD_MIN, DEFAULT_JORNADA_MIN,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CVRP · Puntarenas",
    page_icon="🌺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,#fff0f5 0%,#fce4ec 55%,#fdf2f8 100%);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#f8bbd0 0%,#f06292 100%);
}
[data-testid="stSidebar"] * { color:#4a0e2a !important; }
[data-testid="stSidebar"] .stSlider > div { color:#4a0e2a !important; }

/* ── Header ── */
.main-header {
    background: linear-gradient(135deg,#e91e63 0%,#ad1457 60%,#880e4f 100%);
    padding:1.8rem 2.2rem; border-radius:16px; margin-bottom:1.4rem;
    box-shadow:0 8px 32px rgba(233,30,99,.25);
}
.main-header h1 { color:#fff !important; font-size:2rem; font-weight:800; margin:0; }
.main-header p  { color:#fce4ec !important; margin:.25rem 0 0; font-size:.95rem; }

/* ── KPI cards ── */
.kpi-card {
    background:#fff; border-radius:14px; padding:1.1rem 1.4rem;
    box-shadow:0 4px 20px rgba(233,30,99,.12); border-left:5px solid #e91e63;
}
.kpi-number { font-size:2.1rem; font-weight:800; color:#c2185b; line-height:1.1; }
.kpi-label  { font-size:.76rem; color:#ad1457; font-weight:700;
              text-transform:uppercase; letter-spacing:.6px; margin-top:.25rem; }

/* ── Section title ── */
.sec-title {
    font-size:1.1rem; font-weight:700; color:#880e4f;
    border-bottom:3px solid #f48fb1; padding-bottom:.35rem;
    margin:1.4rem 0 .7rem;
}

/* ── Optimize button ── */
div[data-testid="stButton"] > button {
    background:linear-gradient(135deg,#e91e63,#c2185b) !important;
    color:#fff !important; border:none !important;
    border-radius:10px !important; font-weight:800 !important;
    font-size:1rem !important; padding:.65rem 2rem !important;
    box-shadow:0 4px 14px rgba(233,30,99,.35) !important;
    width:100%;
}
div[data-testid="stButton"] > button:hover {
    background:linear-gradient(135deg,#ad1457,#880e4f) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:#fce4ec; border-radius:10px; padding:4px;
}
.stTabs [data-baseweb="tab"] { color:#ad1457; font-weight:600; }
.stTabs [aria-selected="true"] {
    background:#e91e63 !important; color:#fff !important; border-radius:8px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-thumb { background:#f48fb1; border-radius:3px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def pink_scale(val: float, max_val: float):
    """Devuelve estilo CSS en escala rosa sin matplotlib."""
    if max_val == 0:
        return ""
    ratio = max(0.0, min(1.0, val / max_val))
    r = int(255 - ratio * 30)
    g = int(255 - ratio * 175)
    b = int(255 - ratio * 155)
    text = "#fff" if ratio > 0.6 else ("#880e4f" if ratio > 0.25 else "#4a0e2a")
    return f"background-color:rgb({r},{g},{b});color:{text};font-weight:600"


def sec(title: str):
    st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)


def kpi_card(col, value, label):
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-number">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


PLOTLY_BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#880e4f",
    margin=dict(l=0, r=0, t=10, b=0),
)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — PARÁMETROS EDITABLES
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌺 Parámetros del modelo")
    st.markdown("---")

    st.markdown("### 🚛 Operativos")
    capacity     = st.slider("Capacidad camión (pallets)", 8, 48, DEFAULT_CAPACITY, 2)
    speed_kmh    = st.slider("Velocidad (km/h)", 20, 80, int(DEFAULT_SPEED_KMH), 5)
    min_per_stop = st.slider("Tiempo por parada (min)", 5, 40, int(DEFAULT_MIN_PER_STOP), 1)
    min_per_pal  = st.slider("Tiempo por pallet (min)", 1, 10, int(DEFAULT_MIN_PER_PAL), 1)
    reload_min   = st.slider("Reload entre trips (min)", 5, 60, int(DEFAULT_RELOAD_MIN), 5)
    jornada_h    = st.slider("Jornada laboral (horas)", 6, 12, 8, 1)
    jornada_min  = jornada_h * 60

    st.markdown("---")
    st.markdown("### 📦 Demanda por cantón (pallets/sem)")
    demand_custom: dict = {}
    for nodo, canton in CANTONES.items():
        if nodo == 0:
            continue
        demand_custom[nodo] = st.number_input(
            canton, min_value=0, max_value=500,
            value=int(DEMAND_BASE[nodo]), step=1, key=f"dem_{nodo}",
        )
    demand_custom[0] = 0

    st.markdown("---")
    st.markdown("### 🍺 Mix de productos")
    pct_imp = st.slider("% Imperial", 0, 100, 50, 5) / 100
    pct_pil = st.slider("% Pilsen",   0, 100, 25, 5) / 100
    pct_tro = st.slider("% Tropical", 0, 100, 25, 5) / 100
    total_pct = pct_imp + pct_pil + pct_tro
    if abs(total_pct - 1.0) > 0.01:
        st.warning(f"⚠ El mix suma {total_pct*100:.0f}% (debe ser 100%)")

    st.markdown("---")
    run_btn = st.button("🚀 Optimizar rutas")

    st.markdown("---")
    st.caption("II-1122 · Clase 13 · UCR Sede Alajuela")


# ─────────────────────────────────────────────────────────────────────────────
# ESTADO Y EJECUCIÓN
# ─────────────────────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    # Carga inicial con parámetros por defecto
    st.session_state.result = solve()
    st.session_state.ran = False

if run_btn:
    if abs(total_pct - 1.0) > 0.01:
        st.sidebar.error("Corrige el mix de productos antes de optimizar.")
    else:
        with st.spinner("Optimizando rutas…"):
            st.session_state.result = solve(
                demand=demand_custom,
                capacity=capacity,
                speed_kmh=float(speed_kmh),
                min_per_stop=float(min_per_stop),
                min_per_pal=float(min_per_pal),
                reload_min=float(reload_min),
                jornada_min=float(jornada_min),
                pct_imp=pct_imp,
                pct_pil=pct_pil,
                pct_tro=pct_tro,
            )
        st.session_state.ran = True

result = st.session_state.result
trips  = result["trips"]
trucks = result["trucks"]
demand = result["demand"]
params = result["params"]


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🌺 CVRP · Provincia de Puntarenas</h1>
  <p>Distribución semanal · Florida Bebidas (FIFCO) · Imperial · Pilsen · Tropical</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.ran:
    st.success("✅ Optimización completada con los parámetros configurados.")

# ─────────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
kpi_card(c1, sum(demand.values()), "pallets / semana")
kpi_card(c2, len(trips),           "trips totales")
kpi_card(c3, len(trucks),          "camiones físicos")
kpi_card(c4, f"{result['total_km']:,.0f}", "km totales")
kpi_card(c5, result["num_dedicated"], "camiones dedicados")
st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📦 Demanda & Cantones",
    "🚛 Trips",
    "🔧 Camiones",
    "📐 Modelo CVRP",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DEMANDA
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns(2)

    with col_l:
        sec("Demanda por cantón (pallets/semana)")
        rows = []
        cap_used = params["capacity"]
        for nodo, canton in CANTONES.items():
            if nodo == 0:
                continue
            d = demand.get(nodo, 0)
            rows.append({
                "Nodo": nodo,
                "Cantón": canton,
                f"Imperial ({pct_imp*100:.0f}%)": result["demand_imp"].get(nodo, 0),
                f"Pilsen ({pct_pil*100:.0f}%)":   result["demand_pil"].get(nodo, 0),
                f"Tropical ({pct_tro*100:.0f}%)": result["demand_tro"].get(nodo, 0),
                "Total": d,
                f"Full-loads ({cap_used})": d // cap_used,
                "Residuo": d % cap_used,
            })
        df_demand = pd.DataFrame(rows)
        max_d = df_demand["Total"].max() or 1

        def style_demand(val):
            return pink_scale(val, max_d)

        st.dataframe(
            df_demand.style.map(style_demand, subset=["Total"]),
            use_container_width=True, hide_index=True,
        )

    with col_r:
        sec("Distribución de demanda")
        fig_bar = px.bar(
            df_demand, x="Cantón", y="Total",
            color="Total",
            color_continuous_scale=["#fce4ec", "#e91e63", "#880e4f"],
            labels={"Total": "Pallets/semana"},
        )
        fig_bar.update_layout(**PLOTLY_BASE, xaxis_tickangle=-40,
                              coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)

        total_dem = sum(d for k, d in demand.items() if k != 0) or 1
        fig_pie = go.Figure(go.Pie(
            labels=[f"Imperial {pct_imp*100:.0f}%",
                    f"Pilsen {pct_pil*100:.0f}%",
                    f"Tropical {pct_tro*100:.0f}%"],
            values=[round(total_dem * pct_imp),
                    round(total_dem * pct_pil),
                    round(total_dem * pct_tro)],
            hole=0.5,
            marker_colors=["#e91e63", "#f48fb1", "#f8bbd0"],
        ))
        fig_pie.update_layout(**PLOTLY_BASE, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRIPS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    sec("Detalle de cada trip")

    trip_rows = []
    for idx, trip in enumerate(trips, 1):
        ruta = " → ".join(["CD"] + [CANTONES[n] for n in trip.route] + ["CD"])
        trip_rows.append({
            "Trip": idx,
            "Ruta": ruta,
            "Paradas": len(trip.route),
            "Carga (pallets)": trip.load,
            "Dist. (km)": round(trip.distance_km, 1),
            "Duración (min)": round(trip.duration_min, 1),
            "Duración (h)": round(trip.duration_min / 60, 2),
            "Tipo": "⚠ Dedicado" if trip.is_dedicated() else "Normal",
        })
    df_trips = pd.DataFrame(trip_rows)
    max_dist_t = df_trips["Dist. (km)"].max() or 1

    def style_tipo_trip(val):
        if "Dedicado" in str(val):
            return "background-color:#fce4ec;color:#c2185b;font-weight:700"
        return "background-color:#f3e5f5;color:#6a1b9a;font-weight:600"

    def style_dist_trip(val):
        return pink_scale(val, max_dist_t)

    st.dataframe(
        df_trips.style
            .map(style_tipo_trip, subset=["Tipo"])
            .map(style_dist_trip, subset=["Dist. (km)"]),
        use_container_width=True, hide_index=True,
    )

    sec("Duración de trips vs límite de jornada")
    j_lim = params["jornada_min"]
    colors_t = ["#e91e63" if t.is_dedicated() else "#f48fb1" for t in trips]
    fig_dur = go.Figure(go.Bar(
        x=[f"T{i+1}" for i in range(len(trips))],
        y=[round(t.duration_min, 1) for t in trips],
        marker_color=colors_t,
        text=[f"{t.duration_min/60:.1f}h" for t in trips],
        textposition="outside",
    ))
    fig_dur.add_hline(
        y=j_lim, line_dash="dash", line_color="#880e4f", line_width=2,
        annotation_text=f"Límite jornada ({j_lim/60:.0f} h)",
        annotation_font_color="#880e4f",
    )
    fig_dur.update_layout(**PLOTLY_BASE, yaxis_title="Minutos",
                          xaxis_title="Trip")
    st.plotly_chart(fig_dur, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CAMIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    sec("Asignación de trips a camiones (bin-packing)")

    truck_rows = []
    for tk in trucks:
        is_ded = any(t.is_dedicated() for t in tk.trips)
        rutas = " | ".join(
            " → ".join(["CD"] + [CANTONES[n] for n in t.route] + ["CD"])
            for t in tk.trips
        )
        jorn_pct = tk.total_time_min() / params["jornada_min"] * 100
        truck_rows.append({
            "Camión":        tk.truck_id,
            "Trips":         len(tk.trips),
            "Tiempo (min)":  round(tk.total_time_min(), 1),
            "Tiempo (h)":    round(tk.total_time_min() / 60, 2),
            "% Jornada":     round(jorn_pct, 1),
            "Km totales":    round(tk.total_distance_km(), 1),
            "Pallets":       tk.total_pallets(),
            "Tipo":          "⚠ Dedicado" if is_ded else "Multi-trip",
            "Rutas":         rutas,
        })
    df_trucks = pd.DataFrame(truck_rows)
    max_km_t = df_trucks["Km totales"].max() or 1

    def style_tipo_truck(val):
        if "Dedicado" in str(val):
            return "background-color:#fce4ec;color:#c2185b;font-weight:700"
        return "background-color:#e8f5e9;color:#1b5e20;font-weight:600"

    def style_km_truck(val):
        return pink_scale(val, max_km_t)

    def style_pct(val):
        try:
            pct = float(val)
        except Exception:
            return ""
        if pct > 100:
            return "background-color:#ffcdd2;color:#b71c1c;font-weight:700"
        if pct > 85:
            return "background-color:#fce4ec;color:#880e4f;font-weight:600"
        return "background-color:#f3e5f5;color:#4a148c"

    st.dataframe(
        df_trucks.style
            .map(style_tipo_truck, subset=["Tipo"])
            .map(style_km_truck,   subset=["Km totales"])
            .map(style_pct,        subset=["% Jornada"]),
        use_container_width=True, hide_index=True,
    )

    # ── Gantt horizontal ──────────────────────────────────────────────────────
    sec("Utilización de jornada por camión")

    rl = params["reload_min"]
    jl = params["jornada_min"]
    palette = ["#e91e63", "#f06292", "#f48fb1", "#f8bbd0",
               "#ce93d8", "#ba68c8", "#9c27b0", "#ad1457"]
    fig_h = go.Figure()
    for tk in trucks:
        cursor = 0.0
        for i, trip in enumerate(tk.trips):
            color = "#e91e63" if trip.is_dedicated() else palette[i % len(palette)]
            label = f"T{trips.index(trip)+1} ({trip.duration_min:.0f}m)"
            fig_h.add_trace(go.Bar(
                y=[f"Camión {tk.truck_id}"],
                x=[trip.duration_min],
                base=[cursor],
                orientation="h",
                marker_color=color,
                text=label,
                textposition="inside",
                insidetextanchor="middle",
                name=label,
                showlegend=False,
                hovertemplate=(
                    f"<b>Camión {tk.truck_id}</b><br>"
                    f"Trip {trips.index(trip)+1}<br>"
                    f"Duración: {trip.duration_min:.0f} min<br>"
                    f"Dist: {trip.distance_km:.0f} km<br>"
                    f"Carga: {trip.load} pallets<extra></extra>"
                ),
            ))
            cursor += trip.duration_min
            if i < len(tk.trips) - 1:
                # franja de reload
                fig_h.add_trace(go.Bar(
                    y=[f"Camión {tk.truck_id}"],
                    x=[rl],
                    base=[cursor],
                    orientation="h",
                    marker_color="#fce4ec",
                    marker_line_color="#f48fb1",
                    marker_line_width=1,
                    text="reload",
                    textposition="inside",
                    insidetextanchor="middle",
                    showlegend=False,
                    hoverinfo="skip",
                ))
                cursor += rl

    fig_h.add_vline(x=jl, line_dash="dash", line_color="#880e4f", line_width=2,
                    annotation_text=f"Límite {jl/60:.0f} h",
                    annotation_font_color="#880e4f")
    fig_h.update_layout(
        **PLOTLY_BASE, barmode="stack",
        xaxis_title="Minutos acumulados",
        height=max(300, len(trucks) * 42 + 60),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_h, use_container_width=True)

    # ── Km y pallets ──────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        sec("Km por camión")
        fig_km = px.bar(df_trucks, x="Camión", y="Km totales",
                        color="Km totales",
                        color_continuous_scale=["#fce4ec", "#e91e63", "#880e4f"])
        fig_km.update_layout(**PLOTLY_BASE, coloraxis_showscale=False)
        st.plotly_chart(fig_km, use_container_width=True)
    with col_b:
        sec("Pallets por camión")
        fig_pal = px.bar(df_trucks, x="Camión", y="Pallets",
                         color="Pallets",
                         color_continuous_scale=["#f3e5f5", "#ce93d8", "#7b1fa2"])
        fig_pal.update_layout(**PLOTLY_BASE, coloraxis_showscale=False)
        st.plotly_chart(fig_pal, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MODELO CVRP
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        sec("Variables de decisión")
        st.markdown("""
| Variable | Tipo | Descripción |
|---|---|---|
| `y(i,j)` | Entera ≥ 0 | Camiones en el arco i→j |
| `f(i,j)` | Continua ≥ 0 | Pallets en el arco i→j |
""")
        sec("Función objetivo")
        st.latex(r"\min \; Z = \sum_{(i,j)\in A} \mathrm{dist}(i,j)\cdot y(i,j)")
        st.caption("Minimiza la distancia total recorrida por toda la flota (km).")

    with col_m2:
        sec("Restricciones")
        st.markdown("**① Balance de camiones** — conservación de flujo:")
        st.latex(r"\sum_j y(i,j) = \sum_j y(j,i) \quad \forall\, i")
        st.markdown("**② Balance de carga** — demanda satisfecha:")
        st.latex(r"\sum_j f(j,i) - \sum_j f(i,j) = d_i \quad \forall\, i \neq 0")
        st.markdown("**③ Carga total desde CD:**")
        st.latex(r"\sum_j f(0,j) = D_{\mathrm{total}}")
        st.markdown("**④ Capacidad por arco** *(restricción clave)*:")
        st.latex(r"f(i,j) \leq C \cdot y(i,j) \quad \forall\,(i,j)")
        st.info(f"⚡ Capacidad C = **{params['capacity']} pallets**. "
                "Ningún camión puede cargar más de eso en un arco.")

    sec("Parámetros activos")
    p = params
    params_df = pd.DataFrame({
        "Parámetro":  ["Capacidad", "Velocidad", "Tiempo/parada",
                       "Tiempo/pallet", "Reload", "Jornada"],
        "Valor": [f"{p['capacity']} pallets", f"{p['speed_kmh']} km/h",
                  f"{p['min_per_stop']} min",  f"{p['min_per_pal']} min",
                  f"{p['reload_min']} min",     f"{p['jornada_min']/60:.0f} h ({p['jornada_min']:.0f} min)"],
        "Restricción / uso": [
            "f(i,j) ≤ C·y(i,j)",
            "km/vel×60 → duración trip",
            "+min/parada por cantón visitado",
            "+min/pallet por pallet entregado",
            "tiempo entre trips del mismo camión",
            "bin-packing: Σtrips + Σreloads ≤ jornada",
        ],
    })
    st.dataframe(params_df, use_container_width=True, hide_index=True)

    sec("Fórmula de duración de trip")
    st.latex(
        r"T = \frac{\mathrm{km}}{v}\times 60"
        r"+ n_{\mathrm{paradas}}\times t_{\mathrm{stop}}"
        r"+ n_{\mathrm{pallets}}\times t_{\mathrm{pal}}"
        r"\quad [\mathrm{min}]"
    )

    with st.expander("📊 Matriz de distancias por carretera (km)"):
        labels = [CANTONES[i] for i in range(14)]
        df_dist = pd.DataFrame(DIST, index=labels, columns=labels)
        max_d_val = max(max(row) for row in DIST)

        def style_dist_cell(val):
            if val == 0:
                return "background-color:#fce4ec;color:#c2185b;font-weight:700"
            return pink_scale(val, max_d_val)

        st.dataframe(
            df_dist.style.map(style_dist_cell),
            use_container_width=True,
        )
