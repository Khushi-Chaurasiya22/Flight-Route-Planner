"""AeroPath: educational flight-route planner using sample Indian airport data."""
from flask import Flask, jsonify, render_template, request
import heapq
import random
import time

app = Flask(__name__)

# Coordinates are for the route diagram. All edge lengths and scenario values
# are educational samples; this is not a real flight-planning system.
AIRPORTS = {
    "DEL": {"name": "Indira Gandhi International", "city": "Delhi", "x": 490, "y": 85},
    "BOM": {"name": "Chhatrapati Shivaji Maharaj International", "city": "Mumbai", "x": 245, "y": 250},
    "BLR": {"name": "Kempegowda International", "city": "Bengaluru", "x": 425, "y": 355},
    "HYD": {"name": "Rajiv Gandhi International", "city": "Hyderabad", "x": 575, "y": 250},
    "MAA": {"name": "Chennai International", "city": "Chennai", "x": 735, "y": 365},
    "CCU": {"name": "Netaji Subhas Chandra Bose International", "city": "Kolkata", "x": 805, "y": 160},
    "GOI": {"name": "Manohar International", "city": "Goa", "x": 260, "y": 360},
    "PNQ": {"name": "Pune International", "city": "Pune", "x": 330, "y": 280},
    "AMD": {"name": "Sardar Vallabhbhai Patel International", "city": "Ahmedabad", "x": 335, "y": 150},
    "JAI": {"name": "Jaipur International", "city": "Jaipur", "x": 420, "y": 135},
}
FLIGHT_CONNECTIONS = [
    ("DEL", "BOM", 1150), ("DEL", "BLR", 1740), ("DEL", "HYD", 1250),
    ("DEL", "CCU", 1300), ("BOM", "BLR", 840), ("BOM", "GOI", 420),
    ("BOM", "HYD", 620), ("BLR", "MAA", 290), ("BLR", "HYD", 500),
    ("HYD", "MAA", 520), ("CCU", "MAA", 1360), ("GOI", "BLR", 500),
    ("PNQ", "BOM", 120), ("PNQ", "HYD", 500), ("AMD", "DEL", 775),
    ("AMD", "BOM", 440), ("JAI", "DEL", 280), ("JAI", "AMD", 530),
]
# Example restricted airspace connections. Toggle the checkbox to avoid them.
RESTRICTED_EDGES = {frozenset(("DEL", "CCU")), frozenset(("BOM", "GOI"))}
# Congestion and weather are simulated scenario values, not current conditions.
CONGESTED_EDGES = {frozenset(("DEL", "BOM")), frozenset(("BOM", "BLR")),
                   frozenset(("BLR", "MAA")), frozenset(("HYD", "MAA"))}
WEATHER_EDGES = {frozenset(("DEL", "BLR")), frozenset(("BOM", "GOI")),
                 frozenset(("CCU", "MAA")), frozenset(("GOI", "BLR"))}


def edge_cost(a, b, km, objective, weather, congestion):
    """Return an educational generalized cost for one edge."""
    weather_factor = {"clear": 1.0, "moderate": 1.12, "severe": 1.28}.get(weather, 1.0)
    wx = 1.22 if weather != "clear" and frozenset((a, b)) in WEATHER_EDGES else 1.0
    traffic = 1.25 if congestion and frozenset((a, b)) in CONGESTED_EDGES else 1.0
    adjusted_km = km * wx
    fuel = adjusted_km * 2.8 * traffic * weather_factor  # illustrative litres
    hours = adjusted_km / 780 + (0.35 if traffic > 1 else 0) + (0.25 if wx > 1 else 0)
    emissions = fuel * 2.5  # illustrative kg CO2 per litre factor
    if objective == "duration":
        return hours
    if objective == "environment":
        return emissions
    if objective == "fuel":
        return fuel
    # Balanced multi-objective score, normalised to avoid one unit dominating.
    return adjusted_km + (hours * 110) + (fuel * 0.08) + (emissions * 0.03)


def dijkstra(start, destination, objective="distance", weather="clear", congestion=True, avoid_restricted=False):
    """Dijkstra shortest path for the selected objective; returns path and score."""
    costs = {code: float("inf") for code in AIRPORTS}
    previous = {}
    costs[start] = 0
    queue = [(0, start)]
    while queue:
        current_cost, current = heapq.heappop(queue)
        if current_cost != costs[current]:
            continue
        if current == destination:
            break
        for a, b, km in FLIGHT_CONNECTIONS:
            if a == current:
                neighbour = b
            elif b == current:
                neighbour = a
            else:
                continue
            if avoid_restricted and frozenset((a, b)) in RESTRICTED_EDGES:
                continue
            new_cost = current_cost + edge_cost(a, b, km, objective, weather, congestion)
            if new_cost < costs[neighbour]:
                costs[neighbour] = new_cost
                previous[neighbour] = current
                heapq.heappush(queue, (new_cost, neighbour))
    if costs[destination] == float("inf"):
        return None
    path, node = [], destination
    while node != start:
        path.append(node)
        node = previous[node]
    path.append(start)
    path.reverse()
    return {"path": path, "score": round(costs[destination], 2)}


def route_metrics(path, weather="clear", congestion=True):
    """Calculate illustrative route metrics from sample edges."""
    distance = fuel = duration = 0.0
    weather_hits = congestion_hits = 0
    for a, b in zip(path, path[1:]):
        km = next((d for x, y, d in FLIGHT_CONNECTIONS if {x, y} == {a, b}), 0)
        key = frozenset((a, b))
        wx = 1.22 if weather != "clear" and key in WEATHER_EDGES else 1.0
        traffic = 1.25 if congestion and key in CONGESTED_EDGES else 1.0
        distance += km * wx
        fuel += km * wx * 2.8 * traffic * {"clear": 1, "moderate": 1.12, "severe": 1.28}.get(weather, 1)
        duration += km * wx / 780 + (0.35 if traffic > 1 else 0) + (0.25 if wx > 1 else 0)
        weather_hits += int(wx > 1)
        congestion_hits += int(traffic > 1)
    stops = max(0, len(path) - 2)
    duration += stops * 0.5  # illustrative connection time
    co2 = fuel * 2.5
    utilization = max(0, 100 - congestion_hits * 12 - weather_hits * 5)
    return {"distance": round(distance), "fuel": round(fuel), "duration": round(duration, 1),
            "co2": round(co2), "stops": stops, "weatherSegments": weather_hits,
            "congestedSegments": congestion_hits, "airspaceUtilization": utilization}


def simple_routes(start, destination, objective, weather, congestion, avoid_restricted, limit=4):
    """Enumerate simple paths in the tiny educational graph and rank by objective."""
    routes = []
    adjacency = {code: [] for code in AIRPORTS}
    for a, b, km in FLIGHT_CONNECTIONS:
        adjacency[a].append((b, km)); adjacency[b].append((a, km))
    def visit(node, path, score):
        if node == destination:
            metrics = route_metrics(path, weather, congestion)
            routes.append({"path": path[:], "score": round(score, 2), **metrics})
            return
        for nxt, km in adjacency[node]:
            if nxt in path or (avoid_restricted and frozenset((node, nxt)) in RESTRICTED_EDGES):
                continue
            visit(nxt, path + [nxt], score + edge_cost(node, nxt, km, objective, weather, congestion))
    visit(start, [start], 0)
    routes.sort(key=lambda item: item["score"])
    return routes[:limit]


@app.route("/")
def home():
    return render_template("index.html", airports=AIRPORTS)


@app.route("/find-route", methods=["POST"])
def find_route():
    data = request.get_json(silent=True) or {}
    start, destination = data.get("source", "").upper(), data.get("destination", "").upper()
    if start not in AIRPORTS or destination not in AIRPORTS:
        return jsonify({"error": "Please select airports from the list."}), 400
    if start == destination:
        return jsonify({"error": "Choose two different airports."}), 400
    objective = data.get("objective", "balanced")
    if objective not in {"distance", "balanced", "fuel", "duration", "environment"}:
        objective = "balanced"
    weather = data.get("weather", "clear")
    if weather not in {"clear", "moderate", "severe"}:
        weather = "clear"
    congestion = bool(data.get("congestion", True))
    avoid_restricted = bool(data.get("avoidRestricted", False))
    alternatives = simple_routes(start, destination, objective, weather, congestion, avoid_restricted)
    if not alternatives:
        return jsonify({"error": "No available route under these restrictions."}), 404
    return jsonify({"shortest": alternatives[0], "alternatives": alternatives,
                    "airports": AIRPORTS,
                    "connections": [{"from": a, "to": b, "distance": d,
                                     "restricted": frozenset((a, b)) in RESTRICTED_EDGES}
                                    for a, b, d in FLIGHT_CONNECTIONS],
                    "scenario": {"objective": objective, "weather": weather,
                                 "congestion": congestion, "avoidRestricted": avoid_restricted}})


@app.route("/performance", methods=["POST"])
def performance():
    """Compare runtime and route metrics across graph size and complexity."""
    results = []
    for size in (10, 50, 100, 250):
        for complexity, target_degree in (("Low", 2), ("Medium", 5), ("High", 10)):
            rng = random.Random(42 + size + target_degree)
            graph = {i: {} for i in range(size)}
            # A chain guarantees that every generated airport can be reached.
            for i in range(size - 1):
                weight = rng.randint(50, 1800)
                graph[i][i + 1] = weight; graph[i + 1][i] = weight
            target_edges = min(size * target_degree // 2, size * (size - 1) // 2)
            while sum(map(len, graph.values())) // 2 < target_edges:
                a, b = rng.randrange(size), rng.randrange(size)
                if a != b and b not in graph[a]:
                    w = rng.randint(50, 1800); graph[a][b] = w; graph[b][a] = w
            started = time.perf_counter()
            dist = {i: float("inf") for i in graph}; previous = {}; dist[0] = 0
            queue = [(0, 0)]
            while queue:
                cost, node = heapq.heappop(queue)
                if cost != dist[node]: continue
                if node == size - 1: break
                for neighbour, weight in graph[node].items():
                    candidate = cost + weight
                    if candidate < dist[neighbour]:
                        dist[neighbour] = candidate; previous[neighbour] = node
                        heapq.heappush(queue, (candidate, neighbour))
            elapsed = (time.perf_counter() - started) * 1000
            route = [size - 1]
            while route[-1] != 0:
                route.append(previous[route[-1]])
            route.reverse()
            distance = dist[size - 1]
            edge_count = sum(map(len, graph.values())) // 2
            # Utilization is the route's share of available sample links.
            utilization = len(route) - 1
            results.append({"airports": size, "connections": edge_count,
                            "complexity": complexity, "milliseconds": round(elapsed, 3),
                            "distance": round(distance), "duration": round(distance / 780, 2),
                            "fuel": round(distance * 2.8),
                            "airspaceUtilization": round(utilization / edge_count * 100, 1)})
    return jsonify({"results": results,
                    "note": "Synthetic classroom benchmark. Route time, fuel and network-link utilization are estimates; execution time varies by computer."})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
