const sourceSelect = document.querySelector("#source");
const destinationSelect = document.querySelector("#destination");
const searchButton = document.querySelector("#search-route");
const swapButton = document.querySelector("#swap-airports");
const errorBox = document.querySelector("#form-error");
const resultsSection = document.querySelector("#results-section");
const HISTORY_KEY = "aeropath-recent-searches";

let airportData = {};
let connections = [];
let currentRoutes = [];
let selectedRoute = null;

function setTheme(theme) {
  document.body.classList.toggle("light-theme", theme === "light");
  document.querySelector("#theme-label").textContent =
    theme === "light" ? "Dark mode" : "Light mode";
  document.querySelector("#theme-icon").textContent =
    theme === "light" ? "☾" : "☼";
  try {
    localStorage.setItem("aeropath-theme", theme);
  } catch (error) {
    // Theme switching still works if browser storage is unavailable.
  }
}

let savedTheme = "dark";
try {
  savedTheme = localStorage.getItem("aeropath-theme") || "dark";
} catch (error) {}
setTheme(savedTheme);

document.querySelector("#theme-toggle").addEventListener("click", () => {
  const nextTheme = document.body.classList.contains("light-theme")
    ? "dark"
    : "light";
  setTheme(nextTheme);
});

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch (error) {
    return [];
  }
}

function renderHistory() {
  const historyBox = document.querySelector("#search-history");
  const history = getHistory();
  historyBox.innerHTML = "";

  if (history.length === 0) {
    historyBox.innerHTML = '<span class="empty-history">Your recent routes will appear here.</span>';
    return;
  }

  for (const item of history) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "history-item";
    button.innerHTML = `<span>${item.fromCity} (${item.from}) → ${item.toCity} (${item.to})</span><small>${item.distance.toLocaleString()} km</small>`;
    button.addEventListener("click", () => {
      sourceSelect.value = item.from;
      destinationSelect.value = item.to;
      searchRoutes();
      document.querySelector("#planner").scrollIntoView({behavior: "smooth"});
    });
    historyBox.appendChild(button);
  }
}

function saveHistory(from, to, distance) {
  const history = getHistory().filter(
    item => !(item.from === from && item.to === to)
  );
  history.unshift({
    from,
    to,
    fromCity: airportData[from].city,
    toCity: airportData[to].city,
    distance,
  });
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 5)));
  } catch (error) {}
  renderHistory();
}

function showError(message) {
  errorBox.textContent = message;
}

function sameRoute(routeA, routeB) {
  return routeA && routeB && routeA.path.join("-") === routeB.path.join("-");
}

function drawRouteMap(route) {
  const svg = document.querySelector("#route-map");
  let drawing = '<rect class="map-bg" width="1000" height="450"/>';

  for (let x = 18; x < 1000; x += 38) {
    for (let y = 18; y < 450; y += 38) {
      drawing += `<circle class="map-grid-dot" cx="${x}" cy="${y}" r="1"/>`;
    }
  }

  const routePairs = new Set();
  if (route) {
    for (let i = 0; i < route.path.length - 1; i++) {
      routePairs.add([route.path[i], route.path[i + 1]].sort().join("-"));
    }
  }

  for (const connection of connections) {
    const a = airportData[connection.from];
    const b = airportData[connection.to];
    const key = [connection.from, connection.to].sort().join("-");
    const active = routePairs.has(key);
    drawing += `<path class="map-edge ${active ? "active" : ""} ${connection.restricted ? "restricted-edge" : ""}"
      d="M${a.x},${a.y} Q${(a.x + b.x) / 2},${(a.y + b.y) / 2 - 12} ${b.x},${b.y}"/>`;
  }

  const activeAirports = new Set(route ? route.path : []);
  for (const [code, airport] of Object.entries(airportData)) {
    const active = activeAirports.has(code);
    drawing += `<g class="map-airport ${active ? "active" : ""}">
      <circle class="map-airport-ring" cx="${airport.x}" cy="${airport.y}" r="9"/>
      <circle class="map-airport-dot" cx="${airport.x}" cy="${airport.y}" r="3"/>
      <text class="map-airport-name" x="${airport.x + 13}" y="${airport.y - 2}">${airport.city}</text>
      <text class="map-airport-code" x="${airport.x + 13}" y="${airport.y + 10}">${code}</text>
    </g>`;
  }

  svg.innerHTML = drawing;
  if (route) {
    const cities = route.path.map(code => airportData[code].city);
    document.querySelector("#map-caption").textContent =
      `${cities.join(" → ")} · ${route.path.length - 2} stop(s) · ${route.distance.toLocaleString()} km`;
  }
}

function renderRoutes() {
  const routeList = document.querySelector("#route-list");
  routeList.innerHTML = "";
  const shortest = currentRoutes[0];

  currentRoutes.forEach((route, index) => {
    const isShortest = sameRoute(route, shortest);
    const isSelected = sameRoute(route, selectedRoute);
    const card = document.createElement("button");
    card.type = "button";
    card.className = `route-card ${isShortest ? "shortest" : ""} ${isSelected ? "selected" : ""}`;
    const cityPath = route.path.map(code => `${airportData[code].city} (${code})`).join(" → ");

    card.innerHTML = `
      <div class="route-card-top">
        <span class="route-card-title">${isShortest ? "Shortest route" : `Route option ${index + 1}`}</span>
        ${isShortest ? '<span class="shortest-badge">BEST MATCH</span>' : ""}
      </div>
      <div class="route-distance">${route.distance.toLocaleString()} <small>km · ${route.duration} h</small></div>
      <div class="route-path-text">${cityPath}</div>
      <div class="route-card-bottom"><span>${route.stops} stop(s) · ${route.fuel.toLocaleString()} L est.</span><span>View route ↗</span></div>`;

    card.addEventListener("click", () => {
      selectedRoute = route;
      renderRoutes();
      drawRouteMap(route);
    });
    routeList.appendChild(card);
  });
}

async function searchRoutes() {
  const source = sourceSelect.value;
  const destination = destinationSelect.value;
  showError("");

  if (!source || !destination) {
    showError("Please select both departure and destination airports.");
    return;
  }
  if (source === destination) {
    showError("Choose two different airports.");
    return;
  }

  searchButton.disabled = true;
  searchButton.innerHTML = "Finding routes…";

  try {
    const response = await fetch("/find-route", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        source, destination,
        objective: document.querySelector("#objective").value,
        weather: document.querySelector("#weather").value,
        congestion: document.querySelector("#congestion").checked,
        avoidRestricted: document.querySelector("#avoid-restricted").checked,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not find a route.");
    }

    airportData = data.airports;
    connections = data.connections;
    currentRoutes = data.alternatives;
    selectedRoute = data.shortest;

    document.querySelector("#results-title").textContent =
      `${airportData[source].city} to ${airportData[destination].city}`;
    document.querySelector("#result-count").textContent =
      `${currentRoutes.length} route option(s)`;

    renderRoutes();
    drawRouteMap(selectedRoute);
    const metrics = data.shortest;
    document.querySelector("#route-metrics").innerHTML = [
      ["Distance", `${metrics.distance.toLocaleString()} km`],
      ["Estimated duration", `${metrics.duration} hours`],
      ["Estimated fuel", `${metrics.fuel.toLocaleString()} L`],
      ["Estimated CO₂", `${metrics.co2.toLocaleString()} kg`],
      ["Airspace utilization", `${metrics.airspaceUtilization}%`],
      ["Weather / turbulence links", `${metrics.weatherSegments}`],
      ["Congested links", `${metrics.congestedSegments}`],
      ["Stops", `${metrics.stops}`],
    ].map(([label, value]) => `<article class="metric-card"><small>${label}</small><strong>${value}</strong></article>`).join("");
    resultsSection.hidden = false;
    saveHistory(source, destination, data.shortest.distance);
    resultsSection.scrollIntoView({behavior: "smooth", block: "start"});
  } catch (error) {
    showError(error.message || "Could not connect to AeroPath. Please try again.");
  } finally {
    searchButton.disabled = false;
    searchButton.innerHTML = "<span>Find routes</span><b>→</b>";
  }
}

searchButton.addEventListener("click", searchRoutes);

swapButton.addEventListener("click", () => {
  const oldSource = sourceSelect.value;
  sourceSelect.value = destinationSelect.value;
  destinationSelect.value = oldSource;
});

document.querySelectorAll(".destination-card").forEach(card => {
  card.addEventListener("click", () => {
    const destination = card.dataset.city;
    if (sourceSelect.value === destination) {
      sourceSelect.value = "DEL";
    }
    destinationSelect.value = destination;
    document.querySelector("#planner").scrollIntoView({behavior: "smooth"});
  });
});

document.querySelector("#clear-history").addEventListener("click", () => {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch (error) {}
  renderHistory();
});

renderHistory();

document.querySelector("#run-analysis").addEventListener("click", async event => {
  const button = event.currentTarget;
  const box = document.querySelector("#performance-results");
  button.disabled = true;
  button.textContent = "Measuring…";
  try {
    const response = await fetch("/performance", {method: "POST"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis failed.");
    box.innerHTML = `<div class="table-scroll"><table class="analysis-table"><thead><tr><th>Airports</th><th>Links</th><th>Complexity</th><th>Algorithm</th><th>Flight time</th><th>Fuel est.</th><th>Airspace use</th></tr></thead><tbody>${data.results.map(row => `<tr><td>${row.airports}</td><td>${row.connections}</td><td>${row.complexity}</td><td>${row.milliseconds} ms</td><td>${row.duration} h</td><td>${row.fuel.toLocaleString()} L</td><td>${row.airspaceUtilization}%</td></tr>`).join("")}</tbody></table></div>`;
    document.querySelector("#performance-note").textContent = data.note;
  } catch (error) {
    box.textContent = error.message || "Could not run analysis.";
  } finally {
    button.disabled = false;
    button.textContent = "Run performance analysis →";
  }
});
