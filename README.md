# Local Early Warning System (LEWS)

A disaster early-warning and evacuation-routing system built around proximity-aware alerting. The architecture — geofenced alerting, bunker routing, MQTT edge nodes — generalizes to any city with disaster risk and a network of edge alert nodes.

## What it actually does

- **Polls live disaster data automatically** every 60 seconds from three sources — USGS (earthquakes), NASA EONET, and GDACS — running as a background task on server startup, no manual triggering required. Between these sources, earthquake, flood, severe weather, and wildfire events can all arrive live.
- **Geofenced alerting** — when a threat event is created (live or simulated), the system calculates the haversine distance from every registered alert node to the event source and only triggers sirens on nodes actually within the affected radius. No blanket alerts.
- **Evacuation routing** — computes routes from a user's location to the nearest operational bunkers/shelters, using OSRM road routing with a haversine fallback if the routing service is unavailable.
- **Bunker management** — bunkers can be created, updated, and removed via coordinates through the API (not hardcoded).
- **Deduplication** — incoming threat events are checked against recent events at the same coordinates/type before creating duplicate alerts.
- **PIN-gated simulation mode** — lets you trigger realistic fake disaster scenarios (earthquake, flood, multi-hazard) for demos, completely isolated from live data via an `is_simulation` flag.
- **MQTT-based edge architecture** — alerts are published over MQTT to edge nodes (e.g. ESP32-class devices) that can trigger physical sirens.

## What it doesn't do (yet)

- No authentication on most endpoints beyond the simulation PIN — this is a portfolio/demo build, not hardened for public deployment.
- Routing assumes an OSRM instance is reachable; without one it falls back to straight-line haversine distance, which is fine for triage but not real evacuation guidance.

## Architecture

```
┌─────────────┐     poll (60s)     ┌──────────────────┐
│ USGS/EONET/ │ ─────────────────► │  Threat Analyzer   │
│   GDACS     │                    │  (parse + dedupe)   │
└─────────────┘                    └─────────┬───────────┘
                                              │
                                   haversine filter by node
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │   MQTT Broadcast     │
                                   │ (only affected nodes) │
                                   └─────────┬─────────────┘
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │   Edge Alert Nodes    │
                                   │  (siren / ESP32)       │
                                   └─────────────────────┘
```

## Stack

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL
- **Live data:** USGS Earthquake API, NASA EONET, GDACS
- **Messaging:** MQTT (paho-mqtt)
- **Routing:** OSRM with haversine fallback
- **Frontend:** React (Map Dashboard, Admin Panel, Simulation Control)
- **Edge:** Python-based alert node script (designed for ESP32-class hardware)

## Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with the following variables (none of these are committed to the repo):

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/lews` |
| `MQTT_BROKER` | MQTT broker host | `localhost` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `SECRET_KEY` | App secret key | any random string |
| `SIMULATION_PIN` | PIN required to trigger demo scenarios | any string you choose |
| `DEBUG` | Debug mode | `true` / `false` |

```bash
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Or use `wrapper.py` from the project root to start both at once.

## Simulation mode

To trigger a demo scenario without waiting for a real event:

```
POST /simulation/trigger
{
  "scenario_type": "earthquake_severe",
  "pin": "<your SIMULATION_PIN>"
}
```

Available scenarios: `earthquake_light`, `earthquake_severe`, `flood_minor`, `flood_major`, `multi_scenario_demo`.

## License

MIT
