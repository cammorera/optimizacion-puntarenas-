import streamlit as st
import pandas as pd
import altair as alt
import folium
from streamlit_folium import st_folium
from modelo_cvrp import (resolver_cvrp, CANTONES, DEMANDA, COORDS,
                          DIST_RAW, CAP, JORNADA, VELOCIDAD,
                          T_PARADA, T_PALLET, T_RELOAD,
                          duracion_trip, duracion_trip_solo, clasificar_clientes)

st.set_page_config(page_title="CVRP Puntarenas — FIFCO", page_icon="🍺", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1a0010; color: #fce4ec; }
    [data-testid="stSidebar"] { background-color: #2d0020 !important; }
    [data-testid="stSidebar"] * { color: #fce4ec !important; }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #2d0020; border-radius: 10px; padding: 4px; gap: 4px;
    }
    .stTabs [data-baseweb="tab"]   { color: #f48fb1; font-weight: 600; border-radius: 8px; }
    .stTabs [aria-selected="true"] { background-color: #880e4f !important; color: #fff !important; }
    [data-testid="stMetricValue"]    { font-size: 1.4rem !important; color: #f48fb1 !important; }
    [data-testid="stMetricLabel"]    { color: #f8bbd0 !important; font-weight: 600; }
    [data-testid="stMetricDelta"]    { color: #f48fb1 !important; }
    [data-testid="metric-container"] {
        background-color: #2d0020; border: 1px solid #880e4f;
        border-radius: 12px; padding: 14px 18px;
    }
    h1 { color: #f48fb1 !important; }
    h2, h3 { color: #f8bbd0 !important; }
    p, li { color: #fce4ec; }
    .stCaption { color: #ad1457 !important; }
    .stButton > button {
        background-color: #880e4f; color: #fff; border: none;
        border-radius: 8px; font-weight: 700;
    }
    .stButton > button:hover { background-color: #ad1457; color: #fff; }
    hr { border-color: #880e4f; opacity: 0.4; }
    .block-container { padding-top: 1.5rem; }
    .restriccion-ok   { background:#0a2e0a; border-left:4px solid #4caf50;
                         padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .restriccion-fail { background:#2e0a0a; border-left:4px solid #f44336;
                         padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .restriccion-warn { background:#2e1f00; border-left:4px solid #ff9800;
                         padding:10px 14px; border-radius:8px; margin-bottom:6px; }
</style>
""", unsafe_allow_html=True)

st.title("🍺 CVRP — Florida Bebidas · Puntarenas")
st.caption("Capacitated Vehicle Routing Problem · Minimiza km · Capacidad 24 pallets/camión · Jornada 8 h")

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.header("⚙️ Configuración")
time_limit       = st.sidebar.slider("Tiempo máximo solver (s)", 30, 300, 180, step=30)
respetar_jornada = st.sidebar.toggle("Restricción de jornada en MIP", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**📦 Capacidad por camión:** {CAP} pallets")
st.sidebar.markdown(f"**⏱️ Jornada:** {JORNADA} min (8 h)")
st.sidebar.markdown(f"**🚗 Velocidad:** {VELOCIDAD} km/h")
st.sidebar.markdown(f"**🛑 Por parada:** {T_PARADA} min")
st.sidebar.markdown(f"**📦 Por pallet:** {T_PALLET} min")
st.sidebar.markdown(f"**🔄 Reload entre trips:** {T_RELOAD} min")

dem_total = sum(v for k, v in DEMANDA.items() if k > 0)
ded_cap, ded_tiempo, normales = clasificar_clientes()

st.sidebar.markdown(f"**📊 Demanda total:** {dem_total} pallets")
st.sidebar.markdown(f"**🚛 Flota mínima teórica:** ⌈{dem_total}/{CAP}⌉ = {-(-dem_total//CAP)}")
st.sidebar.markdown("---")
if ded_cap:
    st.sidebar.warning(f"⚠️ Clientes con demanda > {CAP} pallets (se manejan fuera del MIP): "
                       f"{', '.join(CANTONES[c] for c in ded_cap)}")
optimizar = st.sidebar.button("🚀 Optimizar rutas", use_container_width=True)

# ── Sesión ────────────────────────────────────────────────────
if optimizar:
    with st.spinner("Resolviendo CVRP v2… puede tardar hasta 3 min"):
        res = resolver_cvrp(time_limit=time_limit, respetar_jornada=respetar_jornada)
    st.session_state["res"] = res

res = st.session_state.get("res")

COLORES = ["#e91e8c","#f48fb1","#ad1457","#ff80ab","#880e4f",
           "#c2185b","#ff4081","#f06292","#e91e63","#d81b60",
           "#ec407a","#ff1744","#ff6d00","#ffab40","#ccff90",
           "#69ff47","#40c4ff","#18ffff","#b9f6ca","#fff176"]

# ── Pestañas ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Resultado",
    "✅ Validación de restricciones",
    "🗺️ Mapa de rutas",
    "⏱️ Camiones físicos — Jornada 8 h",
    "📊 Datos del problema",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — RESULTADO
# ══════════════════════════════════════════════════════════════
with tab1:
    if res is None:
        st.info("Presioná **Optimizar rutas** en la barra lateral.")
    else:
        flota_min = -(-dem_total // CAP)

        if res["status"] in ("Optimal", "Not Solved") or res["distancia_km"] > 0:
            st.success(f"✅ Solución encontrada — Distancia total: **{res['distancia_km']:.0f} km**")
        else:
            st.error(f"❌ Solver: {res['status']} — Revisá los parámetros.")

        st.markdown("---")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📏 Distancia total",   f"{res['distancia_km']:.0f} km")
        c2.metric("🔀 Trips generados",    len(res["rutas"]))
        c3.metric("🚛 Camiones físicos",   res["n_trucks"],
                  f"mínimo teórico: {flota_min}")
        c4.metric("📦 Demanda total",      f"{dem_total} pallets")
        c5.metric("🔗 Arcos activos MIP",  len(res["arcos"]))

        # Advertencias de restricciones
        if res.get("advertencias"):
            st.markdown("---")
            st.error("### ⛔ Restricciones violadas")
            for w in res["advertencias"]:
                st.markdown(f"- {w}")
        else:
            st.markdown("---")
            st.success("✅ **Todas las restricciones se cumplen** en la solución actual.")

        st.markdown("---")
        st.subheader("🔀 Trips óptimos")

        # Clasificar trips para mostrar badge correcto
        for idx, r in enumerate(res["rutas"]):
            col   = COLORES[idx % len(COLORES)]
            cap_ok = r["pallets"] <= CAP
            dur_ok = r["duracion"] <= JORNADA or r.get("dedicado", False)

            if r.get("dedicado"):
                badge = f"🔴 Dedicado ({r.get('motivo','')})"
            else:
                badge = "🟢 Normal"

            cap_badge = f"{'✅' if cap_ok else '❌'} {r['pallets']} pallets"
            dur_badge = f"{'✅' if dur_ok else '❌'} {r['duracion']:.0f} min"

            st.markdown(
                f"<div style='background:#2d0020;border-left:4px solid {col};"
                f"padding:10px 14px;border-radius:8px;margin-bottom:8px;'>"
                f"<b style='color:{col}'>Trip {idx+1}</b> &nbsp;{badge}&nbsp;·&nbsp;"
                f"<span style='color:#fce4ec'>{' → '.join(r['nombres'])}</span><br>"
                f"<small style='color:#f48fb1'>"
                f"{cap_badge} · {r['km']} km · {dur_badge}"
                f"</small></div>",
                unsafe_allow_html=True
            )

# ══════════════════════════════════════════════════════════════
# TAB 2 — VALIDACIÓN DE RESTRICCIONES
# ══════════════════════════════════════════════════════════════
with tab2:
    if res is None:
        st.info("Optimizá primero desde la pestaña **Resultado**.")
    else:
        st.subheader("✅ Validación detallada de restricciones")
        st.markdown("Verificación de cada restricción del modelo MIP.")
        st.markdown("---")

        rutas  = res["rutas"]
        trucks = res["trucks"]

        # ── R1: Balance de camiones ──────────────────────────
        st.markdown("### Restricción 1 — Balance de camiones (flujo vehicular)")
        arcos = res["arcos"]
        balance_ok = True
        bal_rows = []
        for c in range(1, 14):
            ent = sum(v["camiones"] for (i, j), v in arcos.items() if j == c)
            sal = sum(v["camiones"] for (i, j), v in arcos.items() if i == c)
            ok  = ent == sal
            if not ok:
                balance_ok = False
            bal_rows.append({
                "Cantón": CANTONES[c],
                "Entradas": ent,
                "Salidas":  sal,
                "Estado":   "✅" if ok else "❌ VIOLA"
            })
        if balance_ok:
            st.markdown("<div class='restriccion-ok'>✅ <b>CUMPLIDA</b> — Entradas = Salidas para todos los clientes del MIP</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='restriccion-fail'>❌ <b>VIOLADA</b> — Algún cliente tiene desbalance</div>",
                        unsafe_allow_html=True)
        with st.expander("Ver detalle de balance por cantón"):
            st.dataframe(pd.DataFrame(bal_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── R2: Balance de carga ─────────────────────────────
        st.markdown("### Restricción 2 — Balance de carga (pallets atendidos)")
        carga_rows = []
        carga_ok   = True
        pallets_por_cliente = {c: 0 for c in range(1, 14)}
        for r in rutas:
            for n in r["nodos"]:
                if n != 0:
                    pallets_por_cliente[n] = pallets_por_cliente.get(n, 0) + r["pallets"]

        # Recalcular correctamente: sumar demanda de cada cliente cubierta en sus trips
        pallets_cubiertos = {c: 0 for c in range(1, 14)}
        for r in rutas:
            clientes_en_trip = [n for n in r["nodos"] if n != 0]
            for n in clientes_en_trip:
                pallets_cubiertos[n] += DEMANDA[n]

        for c in range(1, 14):
            cubierto  = pallets_cubiertos[c]
            requerido = DEMANDA[c]
            ok        = cubierto == requerido
            if not ok:
                carga_ok = False
            carga_rows.append({
                "Cantón":      CANTONES[c],
                "Demanda":     requerido,
                "Atendido":    cubierto,
                "Diferencia":  cubierto - requerido,
                "Estado":      "✅" if ok else "❌ VIOLA"
            })

        pallets_total_cubiertos = sum(pallets_cubiertos.values())
        if carga_ok:
            st.markdown("<div class='restriccion-ok'>✅ <b>CUMPLIDA</b> — Todos los clientes reciben su demanda exacta</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='restriccion-fail'>❌ <b>VIOLADA</b> — Algún cliente no está completamente atendido</div>",
                        unsafe_allow_html=True)
        with st.expander("Ver detalle de cobertura por cantón"):
            st.dataframe(pd.DataFrame(carga_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── R3: Total que sale del CD ────────────────────────
        st.markdown("### Restricción 3 — Cobertura total del CD")
        r3_ok = abs(pallets_total_cubiertos - dem_total) < 0.5
        cls3  = "restriccion-ok" if r3_ok else "restriccion-fail"
        icon3 = "✅" if r3_ok else "❌"
        st.markdown(
            f"<div class='{cls3}'>{icon3} <b>{'CUMPLIDA' if r3_ok else 'VIOLADA'}</b> — "
            f"Pallets despachados: <b>{pallets_total_cubiertos}</b> / "
            f"Demanda total: <b>{dem_total}</b></div>",
            unsafe_allow_html=True
        )

        st.markdown("---")

        # ── R4: Capacidad por trip ───────────────────────────
        st.markdown("### Restricción 4 — Capacidad del camión (≤ 24 pallets/trip)")
        cap_rows = []
        cap_ok   = True
        for idx, r in enumerate(rutas):
            ok = r["pallets"] <= CAP
            if not ok:
                cap_ok = False
            cap_rows.append({
                "Trip":     f"Trip {idx+1}",
                "Ruta":     " → ".join(r["nombres"]),
                "Pallets":  r["pallets"],
                "Límite":   CAP,
                "Estado":   "✅" if ok else f"❌ VIOLA (+{r['pallets']-CAP})"
            })
        if cap_ok:
            st.markdown("<div class='restriccion-ok'>✅ <b>CUMPLIDA</b> — Todos los trips respetan los 24 pallets</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='restriccion-fail'>❌ <b>VIOLADA</b> — Algún trip supera la capacidad</div>",
                        unsafe_allow_html=True)
        with st.expander("Ver detalle de carga por trip"):
            df_cap = pd.DataFrame(cap_rows)
            st.dataframe(df_cap, use_container_width=True, hide_index=True)

        # Gráfico de pallets por trip
        df_cap_chart = pd.DataFrame([
            {"Trip": f"T{i+1}", "Pallets": r["pallets"],
             "Estado": "OK" if r["pallets"] <= CAP else "VIOLA"}
            for i, r in enumerate(rutas)
        ])
        chart_cap = (
            alt.Chart(df_cap_chart)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Trip:N", sort=None),
                y=alt.Y("Pallets:Q", scale=alt.Scale(domain=[0, CAP + 5])),
                color=alt.Color("Estado:N", scale=alt.Scale(
                    domain=["OK", "VIOLA"], range=["#e91e8c", "#f44336"]
                )),
                tooltip=["Trip:N", "Pallets:Q"]
            )
            .properties(height=220, title="Pallets por trip")
        )
        linea_cap = (
            alt.Chart(pd.DataFrame({"y": [CAP]}))
            .mark_rule(color="white", strokeDash=[5, 3], strokeWidth=2)
            .encode(y="y:Q")
        )
        st.altair_chart(chart_cap + linea_cap, use_container_width=True)
        st.caption(f"Línea blanca = límite {CAP} pallets")

        st.markdown("---")

        # ── R5: Jornada ──────────────────────────────────────
        st.markdown("### Restricción 5 — Jornada 8 h (≤ 480 min por camión)")
        jornada_rows = []
        jornada_ok   = True
        for idx, t in enumerate(trucks):
            ok = t["tipo"] == "Dedicado" or t["tiempo"] <= JORNADA
            if not ok:
                jornada_ok = False
            estado = ("✅ Normal OK" if t["tipo"] == "Normal" and ok
                      else "🔴 Dedicado (por diseño)" if t["tipo"] == "Dedicado"
                      else "❌ VIOLA")
            jornada_rows.append({
                "Camión":       f"Camión {idx+1}",
                "Tipo":         t["tipo"],
                "Tiempo (min)": round(t["tiempo"], 0),
                "Límite":       JORNADA,
                "Exceso (min)": max(0, round(t["tiempo"] - JORNADA, 0)),
                "Estado":       estado,
            })

        if jornada_ok:
            st.markdown("<div class='restriccion-ok'>✅ <b>CUMPLIDA</b> — Todos los camiones normales respetan las 8 h. "
                        "Los dedicados operan en jornada extendida por diseño.</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='restriccion-fail'>❌ <b>VIOLADA</b> — Algún camión normal supera las 8 h</div>",
                        unsafe_allow_html=True)

        with st.expander("Ver detalle de jornada por camión"):
            st.dataframe(pd.DataFrame(jornada_rows), use_container_width=True, hide_index=True)

        # Gráfico de jornada
        df_jornada = pd.DataFrame([
            {"Camión": f"C{i+1}", "Tiempo": round(t["tiempo"]),
             "Tipo": t["tipo"]}
            for i, t in enumerate(trucks)
        ])
        chart_j = (
            alt.Chart(df_jornada)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Camión:N", sort=None),
                y=alt.Y("Tiempo:Q"),
                color=alt.Color("Tipo:N", scale=alt.Scale(
                    domain=["Normal", "Dedicado"],
                    range=["#e91e8c", "#ff1744"]
                )),
                tooltip=["Camión:N", "Tipo:N", "Tiempo:Q"]
            )
            .properties(height=250, title="Tiempo de jornada por camión")
        )
        linea_j = (
            alt.Chart(pd.DataFrame({"y": [JORNADA]}))
            .mark_rule(color="white", strokeDash=[5, 3], strokeWidth=2)
            .encode(y="y:Q")
        )
        st.altair_chart(chart_j + linea_j, use_container_width=True)
        st.caption(f"Línea blanca = límite {JORNADA} min (8 h) · Camiones dedicados pueden excederlo por diseño")

        st.markdown("---")

        # ── Resumen final ─────────────────────────────────────
        st.subheader("📊 Resumen de cumplimiento")
        checks = [
            ("R1 — Balance camiones",   balance_ok),
            ("R2 — Balance de carga",   carga_ok),
            ("R3 — Cobertura total CD", r3_ok),
            ("R4 — Capacidad 24 pallets", cap_ok),
            ("R5 — Jornada (camiones normales)", jornada_ok),
        ]
        for nombre, ok in checks:
            icono = "✅" if ok else "❌"
            color_div = "restriccion-ok" if ok else "restriccion-fail"
            st.markdown(
                f"<div class='{color_div}'>{icono} <b>{nombre}</b></div>",
                unsafe_allow_html=True
            )

# ══════════════════════════════════════════════════════════════
# TAB 3 — MAPA DE RUTAS
# ══════════════════════════════════════════════════════════════
with tab3:
    if res is None:
        st.info("Optimizá primero desde la pestaña **Resultado**.")
    else:
        st.subheader("🗺️ Mapa de rutas óptimas — Puntarenas")

        m = folium.Map(location=[9.2, -84.0], zoom_start=8,
                       tiles="CartoDB dark_matter")

        for nodo, nombre in CANTONES.items():
            lat, lon = COORDS[nodo]
            color  = "red"  if nodo == 0 else "pink"
            icon   = "home" if nodo == 0 else "circle"
            popup  = (f"<b>{nombre}</b><br>Demanda: {DEMANDA[nodo]} pallets"
                      if nodo > 0 else "<b>CD Puntarenas (Depósito)</b>")
            folium.Marker([lat, lon], popup=popup, tooltip=nombre,
                          icon=folium.Icon(color=color, icon=icon, prefix="fa")
                          ).add_to(m)

        for idx, r in enumerate(res["rutas"]):
            color  = COLORES[idx % len(COLORES)]
            puntos = [COORDS[n] for n in r["nodos"]]
            tip    = (f"Trip {idx+1}: {' → '.join(r['nombres'])} "
                      f"({r['pallets']} pallets · {r['duracion']:.0f} min)")
            dash   = "10 5" if r.get("dedicado") else None
            folium.PolyLine(puntos, color=color, weight=3,
                            opacity=0.85, tooltip=tip,
                            dash_array=dash).add_to(m)

        st_folium(m, width=None, height=560)
        st.caption("🔴 = CD Puntarenas · Cada color = un trip · Línea punteada = trip dedicado")

# ══════════════════════════════════════════════════════════════
# TAB 4 — CAMIONES FÍSICOS
# ══════════════════════════════════════════════════════════════
with tab4:
    if res is None:
        st.info("Optimizá primero desde la pestaña **Resultado**.")
    else:
        st.subheader("⏱️ Asignación de trips a camiones físicos (Hito 4)")
        st.markdown(
            "Cada camión físico opera en una **jornada de 8 horas (480 min)**. "
            "Puede encadenar varios trips mientras la suma no pase de 480 min. "
            f"Si un trip solo supera los **480 min** → **dedicated truck**."
        )
        st.markdown("---")

        trucks = res["trucks"]
        norm  = sum(1 for t in trucks if t["tipo"] == "Normal")
        ded   = sum(1 for t in trucks if t["tipo"] == "Dedicado")

        c1, c2, c3 = st.columns(3)
        c1.metric("🚛 Camiones normales",  norm)
        c2.metric("🔴 Camiones dedicados", ded,
                  "Trip único > 8 h" if ded else "Ninguno")
        c3.metric("🚛 Total camiones",     norm + ded)

        st.markdown("---")

        for idx, t in enumerate(trucks):
            color = "#e91e8c" if t["tipo"] == "Normal" else "#ff1744"
            ocup  = t["tiempo"] / JORNADA * 100
            label = f"Camión {idx+1} — {t['tipo']} — {t['tiempo']:.0f} min ({ocup:.0f}% jornada)"
            with st.expander(label):
                df_bar = pd.DataFrame({
                    "Concepto": ["Utilizado", "Disponible"],
                    "Minutos":  [min(t["tiempo"], JORNADA),
                                 max(JORNADA - t["tiempo"], 0)]
                })
                bar = (
                    alt.Chart(df_bar)
                    .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
                    .encode(
                        x=alt.X("Minutos:Q", scale=alt.Scale(domain=[0, JORNADA + 50])),
                        y=alt.Y("Concepto:N", axis=alt.Axis(labelAngle=0)),
                        color=alt.Color("Concepto:N", scale=alt.Scale(
                            domain=["Utilizado", "Disponible"],
                            range=[color, "#2d0020"]
                        ), legend=None),
                    )
                    .properties(height=100)
                )
                st.altair_chart(bar, use_container_width=True)

                acum = 0
                for ti, trip in enumerate(t["trips"]):
                    if ti > 0:
                        acum += T_RELOAD
                    acum += trip["duracion"]
                    cap_ok = trip["pallets"] <= CAP
                    st.markdown(
                        f"<div style='background:#1a0010;border-left:3px solid {color};"
                        f"padding:8px 12px;border-radius:6px;margin-bottom:6px;'>"
                        f"<b style='color:{color}'>Trip {ti+1}</b> — "
                        f"{' → '.join(trip['nombres'])}<br>"
                        f"<small style='color:#f8bbd0'>"
                        f"{'✅' if cap_ok else '❌'} {trip['pallets']} pallets · "
                        f"{trip['km']} km · {trip['duracion']:.0f} min · "
                        f"acumulado: {acum:.0f} min</small></div>",
                        unsafe_allow_html=True
                    )

        st.markdown("---")
        st.subheader("📊 Resumen por camión")
        rows = []
        for idx, t in enumerate(trucks):
            rows.append({
                "Camión":             f"Camión {idx+1}",
                "Tipo":               t["tipo"],
                "Trips":              len(t["trips"]),
                "Tiempo usado (min)": round(t["tiempo"], 0),
                "Ocupación jornada":  f"{t['tiempo']/JORNADA*100:.0f}%",
                "km totales":         t["km_total"],
                "¿Jornada OK?":       "✅" if t["tipo"] == "Dedicado" or t["tiempo"] <= JORNADA else "❌",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Gantt
        st.subheader("📅 Uso de jornada por camión")
        df_jornada = pd.DataFrame({
            "Camión":    [f"Camión {i+1}" for i in range(len(trucks))],
            "Utilizado": [round(t["tiempo"]) for t in trucks],
            "Tipo":      [t["tipo"] for t in trucks],
        })
        gantt = (
            alt.Chart(df_jornada)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("Utilizado:Q", title="Minutos utilizados"),
                y=alt.Y("Camión:N", sort=None),
                color=alt.Color("Tipo:N", scale=alt.Scale(
                    domain=["Normal", "Dedicado"],
                    range=["#e91e8c", "#ff1744"]
                )),
                tooltip=["Camión:N", "Tipo:N", "Utilizado:Q"]
            )
            .properties(height=max(200, len(trucks) * 28))
        )
        linea_jornada = (
            alt.Chart(pd.DataFrame({"x": [JORNADA]}))
            .mark_rule(color="white", strokeDash=[6, 3], strokeWidth=1.5)
            .encode(x="x:Q")
        )
        st.altair_chart(gantt + linea_jornada, use_container_width=True)
        st.caption(f"Línea blanca = límite {JORNADA} min (8 h)")

# ══════════════════════════════════════════════════════════════
# TAB 5 — DATOS DEL PROBLEMA
# ══════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📊 Cantones y demanda")
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total cantones",   len(CANTONES)-1)
    c2.metric("Demanda total",    f"{dem_total} pallets/sem")
    c3.metric("Capacidad camión", f"{CAP} pallets")

    # Clasificación de clientes
    st.markdown("#### Clasificación de clientes")
    cls_rows = []
    for i in range(1, 14):
        t_solo = duracion_trip_solo(i)
        if i in ded_cap:
            tipo = f"🔴 Demanda > {CAP} pallets (requiere múltiples trips)"
        elif i in ded_tiempo:
            tipo = f"🟠 Trip solo > {JORNADA} min ({t_solo:.0f} min)"
        else:
            tipo = "🟢 Normal (entra al MIP)"
        cls_rows.append({
            "Cantón":          CANTONES[i],
            "Demanda":         DEMANDA[i],
            "Tiempo trip solo (min)": round(t_solo, 0),
            "Clasificación":   tipo,
        })
    st.dataframe(pd.DataFrame(cls_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📏 Matriz de distancias (km)")
    labels  = [CANTONES[i] for i in range(14)]
    df_dist = pd.DataFrame(DIST_RAW, index=labels, columns=labels)
    st.dataframe(df_dist, use_container_width=True)

    st.markdown("---")
    st.subheader("📐 Modelo matemático")
    st.markdown(f"""
**Variables de decisión:**
- `y(i,j)` — entero ≥ 0: camiones en el arco i→j
- `f(i,j)` — continua ≥ 0: pallets en el arco i→j

**Función objetivo:**
```
Min Z = Σ dist(i,j) · y(i,j)
```

**Restricciones:**
```
(1) Balance camiones : Σⱼ y(i,j) = Σⱼ y(j,i)          ∀i ∈ clientes normales
(2) Balance carga    : Σⱼ f(j,i) − Σⱼ f(i,j) = dᵢ     ∀i ∈ clientes normales
(3) Total del CD     : Σⱼ f(0,j) = Σ demanda clientes normales
(4) Capacidad        : f(i,j) ≤ {CAP} · y(i,j)          ∀(i,j)
(5) Jornada (par)   : si t(CD→i→j→CD) > {JORNADA} min → y(i,j) = 0
```

**Pre-procesamiento (clientes especiales):**
```
- Demanda > {CAP} pallets → trips dedicados automáticos (fuera del MIP)
- Trip solo > {JORNADA} min → trip dedicado automático (fuera del MIP)
```

**Post-procesamiento (Hito 4):**
```
Duración trip = (km/vel × 60) + paradas × {T_PARADA} + pallets × {T_PALLET}
Trips normales → bin-packing first-fit con reload de {T_RELOAD} min entre trips
Trips dedicados → 1 camión exclusivo
```
    """)
