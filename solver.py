"""
solver.py — CVRP Puntarenas · Florida Bebidas
Todos los parámetros operativos son argumentos de función,
lo que permite que la app los sobreescriba libremente.
"""

from dataclasses import dataclass, field
from typing import List, Dict

# ── Datos estáticos de la provincia ──────────────────────────────────────────
CANTONES: Dict[int, str] = {
    0:  "CD Puntarenas",
    1:  "Puntarenas",
    2:  "Esparza",
    3:  "Buenos Aires",
    4:  "Montes de Oro",
    5:  "Osa",
    6:  "Quepos",
    7:  "Golfito",
    8:  "Coto Brus",
    9:  "Parrita",
    10: "Corredores",
    11: "Garabito",
    12: "Monteverde",
    13: "Puerto Jiménez",
}

# Demanda base (pallets/semana) — nodo 0 = CD
DEMAND_BASE: Dict[int, int] = {
    0: 0,
    1: 107, 2: 27,  3: 37,  4: 12,
    5: 28,  6: 24,  7: 33,  8: 35,
    9: 16,  10: 39, 11: 20, 12: 4,
    13: 8,
}

# Matriz de distancias por carretera (km) — simétrica, índice 0 = CD
DIST: List[List[int]] = [
    [0,   0,   25,  244, 27,  243, 124, 307, 307, 99,  332, 60,  47,  303],
    [0,   0,   25,  244, 27,  243, 124, 307, 307, 99,  332, 60,  47,  303],
    [25,  25,  0,   224, 19,  226, 109, 290, 287, 85,  314, 55,  49,  288],
    [244, 244, 224, 0,   240, 41,  124, 80,  63,  150, 95,  196, 267, 92 ],
    [27,  27,  19,  240, 0,   244, 127, 308, 303, 103, 331, 73,  30,  305],
    [243, 243, 226, 41,  244, 0,   119, 64,  79,  145, 90,  189, 272, 64 ],
    [124, 124, 109, 124, 127, 119, 0,   183, 186, 26,  208, 72,  156, 179],
    [307, 307, 290, 80,  308, 64,  183, 0,   54,  208, 31,  253, 336, 25 ],
    [307, 307, 287, 63,  303, 79,  186, 54,  0,   212, 46,  259, 330, 78 ],
    [99,  99,  85,  150, 103, 145, 26,  208, 212, 0,   234, 47,  133, 204],
    [332, 332, 314, 95,  331, 90,  208, 31,  46,  234, 0,   279, 359, 52 ],
    [60,  60,  55,  196, 73,  189, 72,  253, 259, 47,  279, 0,   102, 246],
    [47,  47,  49,  267, 30,  272, 156, 336, 330, 133, 359, 102, 0,   335],
    [303, 303, 288, 92,  305, 64,  179, 25,  78,  204, 52,  246, 335, 0  ],
]

# Parámetros por defecto (se usan si no se pasan argumentos)
DEFAULT_CAPACITY     = 24    # pallets por camión
DEFAULT_SPEED_KMH    = 40    # km/h
DEFAULT_MIN_PER_STOP = 15    # min por parada
DEFAULT_MIN_PER_PAL  = 3     # min por pallet
DEFAULT_RELOAD_MIN   = 20    # min de recarga entre trips
DEFAULT_JORNADA_MIN  = 480   # 8 h en minutos
DEFAULT_PCT_IMP      = 0.50
DEFAULT_PCT_PIL      = 0.25
DEFAULT_PCT_TRO      = 0.25


# ── Clases de datos ───────────────────────────────────────────────────────────

@dataclass
class Trip:
    route: List[int]
    load: int
    distance_km: float
    duration_min: float
    pallets_per_stop: Dict[int, int]
    jornada_min: float = DEFAULT_JORNADA_MIN   # referencia para saber si es dedicado

    def is_dedicated(self) -> bool:
        return self.duration_min > self.jornada_min


@dataclass
class Truck:
    truck_id: int
    reload_min: float
    jornada_min: float
    trips: List[Trip] = field(default_factory=list)

    def total_time_min(self) -> float:
        if not self.trips:
            return 0.0
        return (sum(t.duration_min for t in self.trips)
                + self.reload_min * (len(self.trips) - 1))

    def can_add(self, trip: Trip) -> bool:
        if trip.is_dedicated():
            return len(self.trips) == 0
        extra = (self.reload_min if self.trips else 0) + trip.duration_min
        return self.total_time_min() + extra <= self.jornada_min

    def total_distance_km(self) -> float:
        return sum(t.distance_km for t in self.trips)

    def total_pallets(self) -> int:
        return sum(t.load for t in self.trips)


# ── Funciones de cálculo ──────────────────────────────────────────────────────

def _trip_distance_km(route: List[int]) -> float:
    nodes = [0] + route + [0]
    return float(sum(DIST[nodes[i]][nodes[i + 1]] for i in range(len(nodes) - 1)))


def _trip_duration_min(
    route: List[int],
    pallets_per_stop: Dict[int, int],
    speed_kmh: float,
    min_per_stop: float,
    min_per_pal: float,
) -> float:
    km = _trip_distance_km(route)
    paradas = len(route)
    pallets = sum(pallets_per_stop.get(n, 0) for n in route)
    return (km / speed_kmh * 60) + (paradas * min_per_stop) + (pallets * min_per_pal)


# ── Algoritmo greedy + bin-packing ────────────────────────────────────────────

def generate_trips(
    demand: Dict[int, int],
    capacity: int,
    speed_kmh: float,
    min_per_stop: float,
    min_per_pal: float,
    jornada_min: float,
) -> List[Trip]:
    """
    Genera trips respetando la capacidad dada.
    1. Full-load trips para cantones con demanda >= capacity.
    2. Residuos agrupados con greedy nearest-neighbor.
    """
    remaining = {k: v for k, v in demand.items() if k != 0 and v > 0}
    trips: List[Trip] = []

    def make_trip(route, pps):
        return Trip(
            route=route,
            load=sum(pps.values()),
            distance_km=_trip_distance_km(route),
            duration_min=_trip_duration_min(route, pps, speed_kmh, min_per_stop, min_per_pal),
            pallets_per_stop=dict(pps),
            jornada_min=jornada_min,
        )

    # 1. Full-load trips
    for node in list(remaining.keys()):
        dem = remaining[node]
        while dem >= capacity:
            trips.append(make_trip([node], {node: capacity}))
            dem -= capacity
        remaining[node] = dem
        if dem == 0:
            del remaining[node]

    # 2. Greedy nearest-neighbor para residuos
    while remaining:
        route: List[int] = []
        load = 0
        pps: Dict[int, int] = {}
        unvisited = dict(remaining)
        current = 0

        while unvisited and load < capacity:
            best_node, best_d = None, float("inf")
            for node in unvisited:
                space = capacity - load
                if space > 0:
                    d = DIST[current][node]
                    if d < best_d:
                        best_d, best_node = d, node

            if best_node is None:
                break

            take = min(unvisited[best_node], capacity - load)
            route.append(best_node)
            pps[best_node] = take
            load += take
            remaining[best_node] -= take
            if remaining[best_node] == 0:
                del remaining[best_node]
                del unvisited[best_node]
            else:
                unvisited[best_node] = remaining[best_node]
            current = best_node

        if route:
            trips.append(make_trip(route, pps))

    return trips


def pack_trips_into_trucks(
    trips: List[Trip],
    reload_min: float,
    jornada_min: float,
) -> List[Truck]:
    """
    Bin-packing: asigna trips a camiones por Longest-Processing-Time.
    Trips > jornada → dedicated truck automático.
    """
    trucks: List[Truck] = []
    tid = 1

    for trip in sorted(trips, key=lambda t: t.duration_min, reverse=True):
        placed = False
        for truck in trucks:
            if truck.can_add(trip):
                truck.trips.append(trip)
                placed = True
                break
        if not placed:
            t = Truck(truck_id=tid, reload_min=reload_min, jornada_min=jornada_min)
            t.trips.append(trip)
            trucks.append(t)
            tid += 1

    return trucks


# ── Función principal parametrizada ──────────────────────────────────────────

def solve(
    demand: Dict[int, int] = None,
    capacity: int     = DEFAULT_CAPACITY,
    speed_kmh: float  = DEFAULT_SPEED_KMH,
    min_per_stop: float = DEFAULT_MIN_PER_STOP,
    min_per_pal: float  = DEFAULT_MIN_PER_PAL,
    reload_min: float   = DEFAULT_RELOAD_MIN,
    jornada_min: float  = DEFAULT_JORNADA_MIN,
    pct_imp: float = DEFAULT_PCT_IMP,
    pct_pil: float = DEFAULT_PCT_PIL,
    pct_tro: float = DEFAULT_PCT_TRO,
) -> Dict:
    if demand is None:
        demand = dict(DEMAND_BASE)

    trips  = generate_trips(demand, capacity, speed_kmh, min_per_stop, min_per_pal, jornada_min)
    trucks = pack_trips_into_trucks(trips, reload_min, jornada_min)

    total_km = round(sum(tk.total_distance_km() for tk in trucks), 1)

    demand_imp = {k: round(v * pct_imp) for k, v in demand.items()}
    demand_pil = {k: round(v * pct_pil) for k, v in demand.items()}
    demand_tro = {k: round(v * pct_tro) for k, v in demand.items()}

    return {
        "trips":        trips,
        "trucks":       trucks,
        "total_km":     total_km,
        "total_pallets": sum(tk.total_pallets() for tk in trucks),
        "num_trucks":   len(trucks),
        "num_dedicated": sum(1 for tk in trucks if any(t.is_dedicated() for t in tk.trips)),
        "demand":       demand,
        "demand_imp":   demand_imp,
        "demand_pil":   demand_pil,
        "demand_tro":   demand_tro,
        "cantones":     CANTONES,
        "dist":         DIST,
        # params used (for display)
        "params": dict(
            capacity=capacity, speed_kmh=speed_kmh,
            min_per_stop=min_per_stop, min_per_pal=min_per_pal,
            reload_min=reload_min, jornada_min=jornada_min,
        ),
    }


if __name__ == "__main__":
    r = solve()
    print(f"\n{'='*55}")
    print(f"  CVRP — Puntarenas · Florida Bebidas")
    print(f"{'='*55}")
    print(f"  Demanda total : {sum(r['demand'].values())} pallets")
    print(f"  Trips         : {len(r['trips'])}")
    print(f"  Camiones      : {r['num_trucks']}  (dedicados: {r['num_dedicated']})")
    print(f"  Distancia KM  : {r['total_km']} km")
    for tk in r["trucks"]:
        flag = " ⚠" if any(t.is_dedicated() for t in tk.trips) else ""
        print(f"  Camión {tk.truck_id:>2}  {len(tk.trips)} trip(s)  "
              f"{tk.total_distance_km():.0f} km  {tk.total_time_min():.0f} min{flag}")
