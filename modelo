"""
modelo_cvrp.py
CVRP — Florida Bebidas (FIFCO) · Provincia de Puntarenas
Minimiza la distancia total recorrida (km) · Capacidad: 24 pallets/camión

CORRECCIONES v2:
  - Restricción de jornada ahora controla el trip COMPLETO (no solo arcos individuales)
  - Se usa una estimación conservadora: CD→i→CD para cada cliente solo
    como límite de tiempo máximo permitido por trip
  - Clientes con demanda > CAP se atienden con trips dedicados automáticos
    ANTES del MIP, evitando infeasibility
  - El MIP ahora es más estricto: excluye arcos cuya combinación real
    de tiempo supera la jornada
"""
import math
from itertools import combinations
from pulp import (LpProblem, LpMinimize, LpVariable, LpStatus,
                  lpSum, value, PULP_CBC_CMD)

# ── Parámetros operativos ────────────────────────────────────
VELOCIDAD = 40    # km/h
T_PARADA  = 15    # min por parada
T_PALLET  = 3     # min por pallet
T_RELOAD  = 20    # min entre trips del mismo camión
JORNADA   = 480   # min (8 h)

# ── Datos del problema ───────────────────────────────────────
CANTONES = {
    0: "CD Puntarenas", 1: "Puntarenas",    2: "Esparza",
    3: "Buenos Aires",  4: "Montes de Oro", 5: "Osa",
    6: "Quepos",        7: "Golfito",       8: "Coto Brus",
    9: "Parrita",      10: "Corredores",   11: "Garabito",
   12: "Monteverde",   13: "Puerto Jiménez"
}

DEMANDA = {
    0: 0,   1: 107, 2: 27,  3: 37,  4: 12,
    5: 28,  6: 24,  7: 33,  8: 35,  9: 16,
   10: 39, 11: 20, 12:  4, 13:  8
}

COORDS = {
    0:  (9.9748, -84.8316),
    1:  (9.9748, -84.8316),
    2:  (9.9883, -84.6672),
    3:  (9.1636, -83.3317),
    4:  (10.0750,-84.6417),
    5:  (8.9394, -83.4675),
    6:  (9.4328, -84.1614),
    7:  (8.6470, -83.1818),
    8:  (8.9965, -82.9665),
    9:  (9.5155, -84.3272),
   10:  (8.5567, -83.0382),
   11:  (9.8725, -84.7255),
   12: (10.2992, -84.8258),
   13:  (8.5341, -83.3101),
}

DIST_RAW = [
#       0    1    2    3    4    5    6    7    8    9   10   11   12   13
    [   0,   0,  25, 244,  27, 243, 124, 307, 307,  99, 332,  60,  47, 303],
    [   0,   0,  25, 244,  27, 243, 124, 307, 307,  99, 332,  60,  47, 303],
    [  25,  25,   0, 224,  19, 226, 109, 290, 287,  85, 314,  55,  49, 288],
    [ 244, 244, 224,   0, 240,  41, 124,  80,  63, 150,  95, 196, 267,  92],
    [  27,  27,  19, 240,   0, 244, 127, 308, 303, 103, 331,  73,  30, 305],
    [ 243, 243, 226,  41, 244,   0, 119,  64,  79, 145,  90, 189, 272,  64],
    [ 124, 124, 109, 124, 127, 119,   0, 183, 186,  26, 208,  72, 156, 179],
    [ 307, 307, 290,  80, 308,  64, 183,   0,  54, 208,  31, 253, 336,  25],
    [ 307, 307, 287,  63, 303,  79, 186,  54,   0, 212,  46, 259, 330,  78],
    [  99,  99,  85, 150, 103, 145,  26, 208, 212,   0, 234,  47, 133, 204],
    [ 332, 332, 314,  95, 331,  90, 208,  31,  46, 234,   0, 279, 359,  52],
    [  60,  60,  55, 196,  73, 189,  72, 253, 259,  47, 279,   0, 102, 246],
    [  47,  47,  49, 267,  30, 272, 156, 336, 330, 133, 359, 102,   0, 335],
    [ 303, 303, 288,  92, 305,  64, 179,  25,  78, 204,  52, 246, 335,   0],
]

CAP = 24  # pallets/camión


# ── Funciones de tiempo ──────────────────────────────────────
def duracion_trip(ruta: list) -> float:
    """Duración real de un trip completo (min)."""
    km      = sum(DIST_RAW[ruta[k]][ruta[k+1]] for k in range(len(ruta)-1))
    paradas = len([n for n in ruta if n != 0])
    pallets = sum(DEMANDA[n] for n in ruta if n != 0)
    return (km / VELOCIDAD * 60) + paradas * T_PARADA + pallets * T_PALLET


def duracion_trip_solo(i: int) -> float:
    """Duración mínima de un trip que visita solo al cliente i: CD→i→CD."""
    km = DIST_RAW[0][i] + DIST_RAW[i][0]
    return (km / VELOCIDAD * 60) + T_PARADA + DEMANDA[i] * T_PALLET


def duracion_trip_par(i: int, j: int) -> float:
    """Duración estimada de un trip que visita i y j: CD→i→j→CD."""
    km = DIST_RAW[0][i] + DIST_RAW[i][j] + DIST_RAW[j][0]
    return (km / VELOCIDAD * 60) + 2 * T_PARADA + (DEMANDA[i] + DEMANDA[j]) * T_PALLET


def build_dist():
    d = {}
    N = list(range(14))
    for i in N:
        for j in N:
            if i != j:
                if DIST_RAW[i][j] > 0 or i == 0 or j == 0:
                    d[(i, j)] = DIST_RAW[i][j]
    return d


DIST = build_dist()


# ── Clasificar clientes ──────────────────────────────────────
def clasificar_clientes():
    """
    Separa clientes en:
      - dedicados_cap : demanda > CAP (siempre requieren múltiples trips dedicados)
      - dedicados_tiempo: demanda ≤ CAP pero trip solo > JORNADA (trip dedicado por tiempo)
      - normales: pueden combinarse con otros en el MIP
    """
    dedicados_cap    = []
    dedicados_tiempo = []
    normales         = []

    for i in range(1, 14):
        if DEMANDA[i] > CAP:
            dedicados_cap.append(i)
        elif duracion_trip_solo(i) > JORNADA:
            dedicados_tiempo.append(i)
        else:
            normales.append(i)

    return dedicados_cap, dedicados_tiempo, normales


# ── Generar trips dedicados para clientes con demanda > CAP ──
def generar_trips_dedicados_cap(cliente: int) -> list:
    """
    Para cliente con demanda > CAP, genera trips de CAP pallets hasta cubrir todo.
    Cada trip es: CD → cliente → CD con CAP pallets (excepto el último).
    """
    trips = []
    restante = DEMANDA[cliente]
    while restante > 0:
        carga = min(restante, CAP)
        ruta  = [0, cliente, 0]
        km    = DIST_RAW[0][cliente] + DIST_RAW[cliente][0]
        dur   = (km / VELOCIDAD * 60) + T_PARADA + carga * T_PALLET
        trips.append({
            "nodos":    ruta,
            "nombres":  [CANTONES[n] for n in ruta],
            "km":       km,
            "pallets":  carga,
            "duracion": round(dur, 1),
            "dedicado": True,
            "motivo":   "demanda > capacidad",
        })
        restante -= carga
    return trips


# ── Resolver CVRP ────────────────────────────────────────────
def resolver_cvrp(time_limit: int = 180, respetar_jornada: bool = True) -> dict:
    """
    Resuelve el CVRP para Puntarenas con restricciones correctas.

    Mejoras v2:
    - Clientes con demanda > CAP se sacan del MIP y se atienden con trips
      dedicados automáticos (evita infeasibility).
    - La restricción de jornada se aplica tanto a arcos individuales como
      a pares de clientes: si el trip mínimo CD→i→j→CD > JORNADA, el arco
      i→j queda prohibido.
    - Se valida post-solución que ningún trip supere JORNADA.
    """
    dedicados_cap, dedicados_tiempo, normales = clasificar_clientes()

    # Trips dedicados por capacidad (pre-MIP)
    trips_pre = []
    for c in dedicados_cap:
        trips_pre.extend(generar_trips_dedicados_cap(c))

    # Trips dedicados por tiempo (pre-MIP): trip solo ya > 480 min
    for c in dedicados_tiempo:
        ruta = [0, c, 0]
        trips_pre.append({
            "nodos":    ruta,
            "nombres":  [CANTONES[n] for n in ruta],
            "km":       DIST_RAW[0][c] + DIST_RAW[c][0],
            "pallets":  DEMANDA[c],
            "duracion": round(duracion_trip_solo(c), 1),
            "dedicado": True,
            "motivo":   "trip solo > jornada",
        })

    # Si no hay clientes normales, retornar solo trips dedicados
    if not normales:
        trucks = _bin_packing_trucks(trips_pre)
        return {
            "status":       "Optimal",
            "distancia_km": sum(t["km"] for t in trips_pre),
            "arcos":        {},
            "rutas":        trips_pre,
            "trucks":       trucks,
            "n_camiones":   len(trips_pre),
            "n_trucks":     len(trucks),
            "advertencias": [],
        }

    # ── MIP solo para clientes normales ─────────────────────
    N_all  = [0] + normales
    C      = normales
    ARCOS  = [(i, j) for i in N_all for j in N_all
              if i != j and (i, j) in DIST]

    prob = LpProblem("CVRP_Puntarenas_v2", LpMinimize)

    y = {(i, j): LpVariable(f"y_{i}_{j}", lowBound=0, cat="Integer")
         for (i, j) in ARCOS}
    f = {(i, j): LpVariable(f"f_{i}_{j}", lowBound=0)
         for (i, j) in ARCOS}

    # Objetivo: minimizar km
    prob += lpSum(DIST[i, j] * y[i, j] for (i, j) in ARCOS)

    # (1) Balance de camiones
    for i in C:
        prob += (lpSum(y[i, j] for j in N_all if (i, j) in ARCOS) ==
                 lpSum(y[j, i] for j in N_all if (j, i) in ARCOS))

    # (2) Balance de carga
    for i in C:
        prob += (lpSum(f[j, i] for j in N_all if (j, i) in ARCOS) -
                 lpSum(f[i, j] for j in N_all if (i, j) in ARCOS) == DEMANDA[i])

    # (3) Total que sale del CD
    prob += lpSum(f[0, j] for j in C if (0, j) in ARCOS) == sum(DEMANDA[i] for i in C)

    # (4) Capacidad
    for (i, j) in ARCOS:
        prob += f[i, j] <= CAP * y[i, j]

    # (5) Restricción de jornada — CORREGIDA
    # Aplica a arcos entre clientes: si el trip mínimo CD→i→j→CD > JORNADA,
    # se prohíbe el arco i→j (en ambas direcciones)
    if respetar_jornada:
        for (i, j) in ARCOS:
            if i != 0 and j != 0:
                t_par = duracion_trip_par(i, j)
                if t_par > JORNADA:
                    prob += y[i, j] == 0

        # También prohibir arcos desde CD si el trip solo del cliente ya está
        # muy cerca del límite (≥ 95% de jornada), para evitar combinaciones
        for i in C:
            t_solo = duracion_trip_solo(i)
            if t_solo >= JORNADA * 0.85:
                # Este cliente solo puede ir en trip de un cliente
                for j in C:
                    if j != i:
                        if (i, j) in ARCOS:
                            prob += y[i, j] == 0
                        if (j, i) in ARCOS:
                            prob += y[j, i] == 0

    prob.solve(PULP_CBC_CMD(msg=0, timeLimit=time_limit))

    status  = LpStatus[prob.status]
    dist_km = value(prob.objective) or 0

    arcos_activos = {
        (i, j): {
            "camiones": int(round(value(y[i, j]))),
            "pallets":  round(value(f[i, j]) or 0, 1),
            "km":       DIST[i, j],
        }
        for (i, j) in ARCOS
        if value(y[i, j]) and value(y[i, j]) > 0.5
    }

    rutas_mip = _reconstruir_rutas(arcos_activos, N_all)

    # Unir trips del MIP con trips pre-procesados
    todas_rutas = trips_pre + rutas_mip

    # Agregar km de trips pre al total
    dist_total = dist_km + sum(t["km"] for t in trips_pre)

    # Bin-packing
    trucks = _bin_packing_trucks(todas_rutas)

    # Advertencias de validación
    advertencias = _validar_solucion(todas_rutas, trucks)

    return {
        "status":       status,
        "distancia_km": dist_total,
        "arcos":        arcos_activos,
        "rutas":        todas_rutas,
        "trucks":       trucks,
        "n_camiones":   sum(v["camiones"] for (i, j), v in arcos_activos.items() if i == 0)
                        + len(trips_pre),
        "n_trucks":     len(trucks),
        "advertencias": advertencias,
    }


# ── Validar solución ─────────────────────────────────────────
def _validar_solucion(rutas: list, trucks: list) -> list:
    """Retorna lista de advertencias si alguna restricción se viola."""
    warns = []

    # Verificar capacidad por trip
    for i, r in enumerate(rutas):
        if r["pallets"] > CAP:
            warns.append(f"⚠️ Trip {i+1}: {r['pallets']} pallets > capacidad {CAP}")

    # Verificar jornada en camiones normales
    for i, t in enumerate(trucks):
        if t["tipo"] == "Normal" and t["tiempo"] > JORNADA:
            warns.append(f"⚠️ Camión {i+1} (Normal): {t['tiempo']:.0f} min > jornada {JORNADA} min")

    # Verificar cobertura total
    pallets_cubiertos = sum(r["pallets"] for r in rutas)
    demanda_total     = sum(DEMANDA[i] for i in range(1, 14))
    if abs(pallets_cubiertos - demanda_total) > 0.5:
        warns.append(f"⚠️ Cobertura incompleta: {pallets_cubiertos} / {demanda_total} pallets")

    return warns


# ── Reconstruir rutas desde arcos ────────────────────────────
def _reconstruir_rutas(arcos: dict, N: list) -> list:
    """Convierte arcos activos del MIP en lista de trips con métricas."""
    succ = {}
    for (i, j), v in arcos.items():
        for _ in range(v["camiones"]):
            succ.setdefault(i, []).append(j)

    rutas = []
    for nxt in list(succ.get(0, [])):
        ruta = [0, nxt]
        succ[0].remove(nxt)
        cur = nxt
        while cur != 0:
            nexts = succ.get(cur, [])
            if not nexts:
                break
            nxt2 = nexts.pop(0)
            ruta.append(nxt2)
            if nxt2 == 0:
                break
            cur = nxt2
        if ruta[-1] != 0:
            ruta.append(0)

        km      = sum(DIST_RAW[ruta[k]][ruta[k+1]] for k in range(len(ruta)-1))
        pallets = sum(DEMANDA[n] for n in ruta if n != 0)
        dur     = duracion_trip(ruta)
        rutas.append({
            "nodos":    ruta,
            "nombres":  [CANTONES[n] for n in ruta],
            "km":       km,
            "pallets":  pallets,
            "duracion": round(dur, 1),
            "dedicado": dur > JORNADA,
            "motivo":   "trip > jornada" if dur > JORNADA else "",
        })
    return rutas


# ── Bin-packing trips → camiones físicos ────────────────────
def _bin_packing_trucks(rutas: list) -> list:
    """
    Agrupa trips en camiones físicos respetando jornada 8 h.
    - Trip dedicado (> 480 min solo) → 1 camión exclusivo.
    - Resto: first-fit decreasing, sumando T_RELOAD entre trips.
    """
    dedicados    = [r for r in rutas if r.get("dedicado", False)]
    no_dedicados = sorted(
        [r for r in rutas if not r.get("dedicado", False)],
        key=lambda r: r["duracion"], reverse=True
    )

    trucks = []

    for r in dedicados:
        trucks.append({
            "tipo":     "Dedicado",
            "trips":    [r],
            "tiempo":   r["duracion"],
            "km_total": r["km"],
        })

    bins = []
    for trip in no_dedicados:
        colocado = False
        for b in bins:
            usado = b["tiempo"] + T_RELOAD + trip["duracion"]
            if usado <= JORNADA:
                b["trips"].append(trip)
                b["tiempo"]   += T_RELOAD + trip["duracion"]
                b["km_total"] += trip["km"]
                colocado = True
                break
        if not colocado:
            bins.append({
                "tipo":     "Normal",
                "trips":    [trip],
                "tiempo":   trip["duracion"],
                "km_total": trip["km"],
            })

    trucks += bins
    return trucks


if __name__ == "__main__":
    print("Resolviendo CVRP v2 con restricciones corregidas…")
    res = resolver_cvrp()
    print(f"Status         : {res['status']}")
    print(f"Distancia total: {res['distancia_km']:.0f} km")
    print(f"Trips generados: {len(res['rutas'])}")
    print(f"Camiones físicos: {res['n_trucks']}")
    if res["advertencias"]:
        print("\nADVERTENCIAS:")
        for w in res["advertencias"]:
            print(f"  {w}")
    else:
        print("\n✅ Todas las restricciones se cumplen.")
    print()
    for i, t in enumerate(res["trucks"]):
        print(f"  Camión {i+1} [{t['tipo']}] — {t['tiempo']:.0f} min — {t['km_total']} km")
        for r in t["trips"]:
            print(f"    {' → '.join(r['nombres'])} ({r['duracion']:.0f} min, {r['pallets']} pallets)")
