# AeroPath — Smart Flight Route Finder

AeroPath is a local educational flight-route planner. It compares sample routes between Indian airports using Dijkstra's algorithm and configurable classroom scenarios.

## Features

- Responsive aviation-themed website with dark/light mode.
- Airport search by city and airport code, plus a swap button.
- Shortest route, connecting airports, distance in kilometres, and stop count.
- Alternative routes and an interactive route diagram.
- Multi-objective route selection: balanced score, distance, illustrative fuel, duration, or CO₂ estimate.
- Simulated weather/turbulence severity, airport congestion, and restricted airspace links.
- Route estimates for duration, fuel, CO₂, stop count, and airspace utilization.
- Performance/scalability benchmark on generated graphs with 10–250 airports and low, medium, and high connection complexity.
- Popular destination shortcuts.
- Recent searches saved in browser local storage.
- Flask backend with sample airport data; no database or live flight API.

## Requirements

- Python 3.10 or newer
- Flask, installed from `requirements.txt`

## Run locally

Open a terminal in the `AeroPath` project folder and run:

```bash
python -m pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000` in a browser. Keep the terminal open while using the website. Press Ctrl+C to stop it. On Windows, after dependencies are installed, you can also double-click `run_aeropath.bat` to start the server and open Chrome.

## Project structure

```text
AeroPath/
├── app.py
├── requirements.txt
├── README.md
├── run_aeropath.bat
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```

## How the route search works

Airports are graph vertices. Sample flight connections are weighted edges whose weights are distances in kilometres. Dijkstra's algorithm uses a priority queue to find the minimum-distance route. The small graph is stored in Python dictionaries and lists. Alternative simple routes are listed by distance for comparison.

All airport connections and distances are educational sample data. Weather, congestion, restrictions, fuel, duration, CO₂, and utilization are simulated or illustrative estimates. They are not live flight information, forecasts, air traffic control data, or navigation guidance. The benchmark uses synthetic graphs; timing depends on the computer.

## Concepts demonstrated

- **Graph:** airports are vertices (nodes), and sample connections are weighted edges.
- **Dijkstra:** a priority queue expands the lowest accumulated score to find a least-cost route. The chosen cost can represent distance, fuel, time, emissions, or a balanced score.
- **Constraints:** the restricted-airspace option removes selected sample edges before route search.
- **Multi-objective comparison:** the balanced score combines normalized educational estimates; it is for demonstrating trade-offs, not real dispatch decisions.
- **Performance analysis:** the page generates synthetic graphs of increasing sizes and link complexity, then reports local algorithm run time, estimated flight duration, fuel, and the route's share of available links as sample airspace utilization. A binary heap implementation is approximately O((V + E) log V).

## Upload to GitHub

1. Create a new empty repository on GitHub.
2. Extract the ZIP and open a terminal inside the `AeroPath` folder.
3. Run the following commands, replacing the repository address with your own:

```bash
git init
git add .
git commit -m "Add AeroPath flight route planner"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

The `.gitignore` file excludes Python cache files and virtual environments.
