"""
CVRP Solver for Provincia de Puntarenas — Florida Bebidas
Capacidad por camión: 24 pallets
Jornada: 8 h (480 min)
Parámetros de tiempo: velocidad 40 km/h, 15 min/parada, 3 min/pallet, 20 min reload
"""

import itertools
from dataclasses import dataclass, field
from typing import List, Tuple, Dict

# ── Datos de la provincia ──────────────────────────────────────────────────────
CANTONES = {
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

# Demanda total por cantón (pallets/semana)
DEMAND = {
    0: 0,   # CD
    1: 107,
    2: 27,
    3: 37,
    4: 12,
    5: 28,
    6: 24,
    7: 33,
    8: 35,
    9: 16,
    10: 39,
    11: 20,
    12: 4,
    13: 8,
}

# Distribución por producto (50% Imperial, 25% Pilsen, 25% Tropical)
DEMAND_IMPERIAL = {k: round(v * 0.50) for k, v in DEMAND.items()}
DEMAND_PILSEN   = {k: round(v * 0.25) for k, v in DEMAND.items()}
DEMAND_TROPICAL = {k: round(v * 0.25) for k, v in DEMAND.items()}

# Matriz de distancias por carretera (km) — índice 0 = CD
DIST = [
    [0,   0,   25,  244, 27,  243, 124, 307, 307, 99,  332, 60,  47,  303],
    [0,   0,   25,  244, 27,  243, 124, 307, 307, 99,  332, 60,  47,  303],
    [25,  25,  0,   224, 19,  226, 109, 290, 287, 85,  314, 55,  49,  288],
    [244, 244, 224, 0,   240, 41,  124, 80,  63,  150, 95,  196, 267, 92],
    [27,  27,  19,  240, 0,   244, 127, 308, 303, 103, 331, 73,  30,  305],
    [243, 243, 226, 41,  244, 0,   119, 64,  79,  145, 90,  189, 272, 64],
    [124, 124, 109, 124, 127, 119, 0,   183, 186, 26,  208, 72,  156, 179],
    [307, 307, 290, 80,  308, 64,  183, 0,   54,  208, 31,  253, 336, 25],
    [307, 307, 287, 63,  303, 79,  186, 54,  0,   212, 46,  259, 330, 78],
    [99,  99,  85,  150, 103, 145, 26,  208, 212, 0,   234, 47,  133, 204],
    [332, 332, 314, 95,  331, 90,  208, 31,  46,  234, 0,   279, 359, 52],
    [60,  60,  55,  196, 73,  189, 72,  253, 259, 47,  279, 0,   102, 246],
    [47,  47,  49,  267, 30,  272, 156, 336, 330, 133, 359, 102, 0,   335],
    [303, 303, 288, 92,  305, 64,  179, 25,  78,  204, 52,  246, 335, 0],
]

# ── Parámetros operativos ──────────────────────────────────────────────────────
CAPACITY    = 24      # pallets por camión
SPEED_KMH   = 40      # km/h
MIN_PER_STOP = 15     # minutos por parada
MIN_PER_PALLET = 3   # minutos por pallet entregado
RELOAD_MIN  = 20      # minutos de recarga entre trips
JORNADA_MIN = 480     # 8 horas


def trip_duration_min(route: List[int], pallets_per_stop: Dict[int, int]) -> float:
    """
    Calcula la duración en minutos de un trip dado.
    route: lista de nodos visitados (sin incluir CD al inicio/fin)
    Fórmula: (km_totales / vel * 60) + paradas * 15 + pallets_total * 3
    """
    nodes = [0] + route + [0]
    km_total = sum(DIST[nodes[i]][nodes[i+1]] for i in range(len(nodes)-1))
    paradas = len(route)
    pallets = sum(pallets_per_stop.get(n, 0) for n in route)
    return (km_total / SPEED_KMH * 60) + (paradas * MIN_PER_STOP) + (pallets * MIN_PER_PALLET)


def trip_distance_km(route: List[int]) -> float:
    nodes = [0] + route + [0]
    return sum(DIST[nodes[i]][nodes[i+1]] for i in range(len(nodes)-1))


# ── Generador de trips con heurística greedy ──────────────────────────────────

@dataclass
class Trip:
    route: List[int]
    load: int
    distance_km: float
    duration_min: float
    pallets_per_stop: Dict[int, int]

    def is_dedicated(self) -> bool:
        return self.duration_min > JORNADA_MIN


def generate_trips(demand: Dict[int, int]) -> List[Trip]:
    """
    Genera trips respetando capacidad de 24 pallets.
    - Cantones con demanda > 24: varios full-load trips + posible trip residual.
    - Cantones con demanda <= 24: agrupados por cercanía greedy.
    Retorna lista de Trip.
    """
    remaining = {k: v for k, v in demand.items() if k != 0 and v > 0}
    trips: List[Trip] = []

    # 1. Full-load trips para cantones con demanda > 24
    full_load_nodes = []
    for node, dem in list(remaining.items()):
        while dem >= CAPACITY:
            pps = {node: CAPACITY}
            t = Trip(
                route=[node],
                load=CAPACITY,
                distance_km=trip_distance_km([node]),
                duration_min=trip_duration_min([node], pps),
                pallets_per_stop=pps,
            )
            trips.append(t)
            dem -= CAPACITY
        remaining[node] = dem
        if dem == 0:
            del remaining[node]

    # 2. Agrupar residuos con greedy nearest-neighbor desde CD
    while remaining:
        route = []
        load = 0
        pps = {}
        unvisited = dict(remaining)

        current = 0
        while unvisited:
            # Buscar nodo más cercano al actual que quede espacio
            best_node, best_dist = None, float("inf")
            for node, dem in unvisited.items():
                if load + min(dem, CAPACITY - load) <= CAPACITY:
                    d = DIST[current][node]
                    if d < best_dist:
                        best_dist = d
                        best_node = node

            if best_node is None:
                break  # camión lleno

            take = min(unvisited[best_node], CAPACITY - load)
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

            if load >= CAPACITY:
                break

        if route:
            trips.append(Trip(
                route=route,
                load=load,
                distance_km=trip_distance_km(route),
                duration_min=trip_duration_min(route, pps),
                pallets_per_stop=pps,
            ))

    return trips


# ── Bin-packing de trips en camiones ──────────────────────────────────────────

@dataclass
class Truck:
    truck_id: int
    trips: List[Trip] = field(default_factory=list)

    def total_time_min(self) -> float:
        if not self.trips:
            return 0
        t = sum(trip.duration_min for trip in self.trips)
        t += RELOAD_MIN * (len(self.trips) - 1)
        return t

    def can_add(self, trip: Trip) -> bool:
        if trip.is_dedicated():
            return len(self.trips) == 0
        new_total = self.total_time_min() + trip.duration_min
        if self.trips:
            new_total += RELOAD_MIN
        return new_total <= JORNADA_MIN

    def total_distance_km(self) -> float:
        return sum(t.distance_km for t in self.trips)

    def total_pallets(self) -> int:
        return sum(t.load for t in self.trips)


def pack_trips_into_trucks(trips: List[Trip]) -> List[Truck]:
    """
    Bin-packing: asigna trips a camiones respetando jornada de 480 min.
    Trips > 8 h → dedicated truck automático.
    """
    trucks: List[Truck] = []
    truck_id = 1

    for trip in sorted(trips, key=lambda t: t.duration_min, reverse=True):
        placed = False
        for truck in trucks:
            if truck.can_add(trip):
                truck.trips.append(trip)
                placed = True
                break
        if not placed:
            new_truck = Truck(truck_id=truck_id)
            new_truck.trips.append(trip)
            trucks.append(new_truck)
            truck_id += 1

    return trucks


# ── Función principal ─────────────────────────────────────────────────────────

def solve() -> Dict:
    trips = generate_trips(DEMAND)
    trucks = pack_trips_into_trucks(trips)

    total_km = sum(tk.total_distance_km() for tk in trucks)
    total_pallets_delivered = sum(tk.total_pallets() for tk in trucks)
    dedicated = [tk for tk in trucks if any(t.is_dedicated() for t in tk.trips)]

    return {
        "trips": trips,
        "trucks": trucks,
        "total_km": round(total_km, 1),
        "total_pallets": total_pallets_delivered,
        "num_trucks": len(trucks),
        "num_dedicated": len(dedicated),
        "demand": DEMAND,
        "cantones": CANTONES,
        "dist": DIST,
    }


if __name__ == "__main__":
    result = solve()
    print(f"\n{'='*55}")
    print(f"  CVRP — Puntarenas · Florida Bebidas")
    print(f"{'='*55}")
    print(f"  Demanda total : {sum(DEMAND.values())} pallets")
    print(f"  Trips totales : {len(result['trips'])}")
    print(f"  Camiones      : {result['num_trucks']}  (dedicados: {result['num_dedicated']})")
    print(f"  Distancia KM  : {result['total_km']} km")
    print(f"\n  Detalle por camión:")
    for tk in result["trucks"]:
        flag = " ⚠ dedicado" if any(t.is_dedicated() for t in tk.trips) else ""
        print(f"  Camión {tk.truck_id:>2}  |  {len(tk.trips)} trip(s)  |  "
              f"{tk.total_distance_km():.0f} km  |  {tk.total_time_min():.0f} min{flag}")
