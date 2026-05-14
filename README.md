# Mars Rover Operator API

A RESTful API for controlling autonomous rovers on a configurable grid map, with real-time WebSocket support and a browser-based operator UI. Built with FastAPI and deployable via Docker on Azure.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker](#docker)
- [Azure Deployment](#azure-deployment)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [WebSocket Control](#websocket-control)
- [Rover Behavior](#rover-behavior)
- [Updating a Deployment](#updating-a-deployment)
- [Cleanup](#cleanup)

---

## Features

- CRUD endpoints for rovers, mines, and map configuration
- Rover command dispatch with step-by-step path tracking
- Real-time rover control via WebSocket
- Mine detection and defuse logic
- Static browser UI served directly from the FastAPI app
- Fully containerized with Docker
- Azure-ready (Azure Container Registry + Azure Web Apps)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, Pydantic |
| Server | Uvicorn (ASGI) |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Container | Docker |
| Cloud | Azure Container Registry, Azure Web Apps |

---

## Project Structure

```
lab4/
├── main.py                # All API routes and rover logic
├── models.py              # Pydantic request/response models
├── storage.py             # In-memory data store (map, mines, rovers)
├── Dockerfile             # Container build instructions
├── requirements.txt       # Python dependencies
├── .gitignore
└── ui/
    ├── index.html         # Operator dashboard
    ├── script.js          # Frontend logic and API calls
    ├── style.css          # Styling
    ├── config.example.js  # URL config template (committed)
    └── config.js          # Your actual Azure URL (gitignored — never committed)
```

---

## Prerequisites

Make sure the following are installed before you begin:

- [Python 3.10+](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) *(for cloud deployment only)*
- An Azure account with:
  - An **Azure Container Registry (ACR)** created
  - An **Azure Web App** configured for Docker (Linux)

---

## Local Development

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd lab4
```

### 2. Set up the frontend config

```bash
# Windows
copy ui\config.example.js ui\config.js

# macOS / Linux
cp ui/config.example.js ui/config.js
```

For local development you do not need to edit `config.js` — the app automatically detects `localhost` and points to `http://127.0.0.1:8000`.

### 3. Create and activate a virtual environment

```bash
# Create
python -m venv .venv

# Activate — Windows
.venv\Scripts\activate

# Activate — macOS / Linux
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the development server

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. The UI loads automatically.

> The `--reload` flag restarts the server on every file save — useful during development. Remove it in production.

---

## Docker

Docker lets you package the entire application (Python, dependencies, and all) into a portable image that runs the same everywhere.

### How the Dockerfile works

```dockerfile
FROM python:3.10-slim        # Start from a minimal official Python image
WORKDIR /app                 # All commands run from /app inside the container
COPY . .                     # Copy your project files into the container
RUN pip install ...          # Install dependencies at build time
EXPOSE 80                    # Document that the container listens on port 80
CMD ["uvicorn", ...]         # Command that runs when the container starts
```

### Build the image

```bash
docker build -t mars-rover:latest .
```

- `-t mars-rover:latest` — names and tags the image
- `.` — tells Docker to use the current directory as the build context (where it looks for the `Dockerfile` and files to copy)

### Run the container locally

```bash
docker run -p 80:80 mars-rover:latest
```

- `-p 80:80` — maps port 80 on your machine to port 80 inside the container

Open [http://localhost](http://localhost) in your browser.

### Useful Docker commands

```bash
docker images                        # List all local images
docker ps                            # List running containers
docker stop <container-id>           # Stop a running container
docker rm <container-id>             # Remove a stopped container
docker rmi mars-rover:latest         # Delete the image
```

---

## Azure Deployment

### Overview of the flow

```
Your code
   └── docker build   →   Local image
         └── docker push   →   Azure Container Registry (ACR)
                                    └── Azure Web App pulls image and runs it
```

### Step 1 — Log in to Azure and ACR

```bash
az login
docker login <your-acr>.azurecr.io
```

You will be prompted for your ACR username and password (found in Azure Portal → Container Registry → Access Keys).

### Step 2 — Build and tag the image for ACR

Always increment the version tag so you can track and roll back deployments.

```bash
docker build -t <your-acr>.azurecr.io/mars-rover:v1 .
```

### Step 3 — Push the image to ACR

```bash
docker push <your-acr>.azurecr.io/mars-rover:v1
```

This uploads your image to the private registry in Azure.

### Step 4 — Set the Azure URL in your frontend config

Edit `ui/config.js` (this file is gitignored and stays local):

```js
window.AZURE_URL = "your-app-name.azurewebsites.net";
```

Find your URL in: Azure Portal → Web App → Overview → Default Domain.

### Step 5 — Deploy to the Web App

1. Go to **Azure Portal → Web App → Deployment Center**
2. Set the **Image** to your ACR image and the **Tag** to your version (e.g., `v1`)
3. Click **Save** — the Web App restarts and pulls the new image automatically

### Required Azure Web App settings

Navigate to **Web App → Settings → Environment Variables** and **Configuration → General Settings**:

| Setting | Value | Where |
|---|---|---|
| `WEBSITES_PORT` | `80` | Environment Variables |
| Always On | Enabled | General Settings |
| WebSockets | Enabled | General Settings |

---

## Configuration

### `ui/config.js` (gitignored)

This file holds your Azure App Service URL and is **never committed to the repository**.

To set it up:

```bash
cp ui/config.example.js ui/config.js
```

Then edit `ui/config.js`:

```js
window.AZURE_URL = "your-app-name.azurewebsites.net";
```

The frontend automatically uses `http://127.0.0.1:8000` when running on localhost, and your Azure URL in production — no changes needed when switching between environments.

---

## API Reference

All endpoints return and accept JSON. Base URL is `http://127.0.0.1:8000` locally or `https://<your-azure-url>` in production.

Interactive docs are available at `/docs` (Swagger UI) once the server is running.

### Map

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/map` | Get map dimensions and all mine positions |
| `PUT` | `/map` | Update map width and height |

**PUT `/map` — request body:**
```json
{ "width": 10, "height": 10 }
```

---

### Mines

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/mines` | List all mines |
| `GET` | `/mines/{id}` | Get a specific mine by ID |
| `POST` | `/mines` | Create a new mine |
| `PUT` | `/mines/{id}` | Update mine position or serial number |
| `DELETE` | `/mines/{id}` | Remove a mine |

**POST `/mines` — request body:**
```json
{ "x": 3, "y": 5, "serial_number": "SN-1234" }
```

**PUT `/mines/{id}` — all fields optional:**
```json
{ "x": 4, "y": 6, "serial_number": "SN-9999" }
```

---

### Rovers

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/rovers` | List all rovers (ID and status only) |
| `GET` | `/rovers/{id}` | Get full rover details |
| `POST` | `/rovers` | Create a rover with a command sequence |
| `PUT` | `/rovers/{id}` | Update a rover's command sequence |
| `DELETE` | `/rovers/{id}` | Delete a rover |
| `POST` | `/rovers/{id}/dispatch` | Execute the rover's full command sequence |

**POST `/rovers` — request body:**
```json
{ "commands": "MMRMLMD" }
```

**Dispatch response example:**
```json
{
  "id": 1,
  "status": "Finished",
  "latest_position": { "x": 2, "y": 0 },
  "executed_commands": "MMRMLMD",
  "path": [
    { "x": 0, "y": 0 },
    { "x": 0, "y": 1 },
    { "x": 0, "y": 2 }
  ]
}
```

---

## WebSocket Control

Connect to control a rover in real time:

```
ws://127.0.0.1:8000/ws/rovers/{id}/control       (local)
wss://your-app.azurewebsites.net/ws/rovers/{id}/control  (Azure)
```

The rover must be in `Not Started` or `Finished` status to accept a connection.

### Commands (send as plain text)

| Command | Action |
|---|---|
| `M` | Move forward one cell |
| `L` | Turn left (counter-clockwise) |
| `R` | Turn right (clockwise) |
| `D` | Defuse mine at current cell |

### Keyboard shortcuts (in the UI)

| Key | Command |
|---|---|
| `Space` / `W` / `↑` | Move forward |
| `A` / `←` | Turn left |
| `D` / `→` | Turn right |
| `F` | Defuse mine |

### Server response (JSON)

```json
{ "command": "M", "success": true, "x": 1, "y": 0 }
```

If the rover hits an un-defused mine:
```json
{ "status": "Eliminated", "x": 2, "y": 3 }
```

---

## Rover Behavior

- All rovers start at position `(0, 0)` facing **South**
- Valid commands: `L`, `R`, `M`, `D`
- Moving onto a mine without defusing it first sets status to `Eliminated` and ends execution
- `D` removes the mine at the rover's current cell (if one exists)
- Moving out of map bounds is ignored (the rover stays in place)

### Rover statuses

| Status | Meaning |
|---|---|
| `Not Started` | Created, not yet dispatched |
| `Moving` | Currently executing commands |
| `Finished` | All commands executed successfully |
| `Eliminated` | Destroyed by a mine |

---

## Updating a Deployment

Every time you change code and want to redeploy:

```bash
# 1. Build with a new version tag
docker build -t <your-acr>.azurecr.io/mars-rover:v2 .

# 2. Push to ACR
docker push <your-acr>.azurecr.io/mars-rover:v2

# 3. Update the tag in Azure Portal → Web App → Deployment Center → Save
```

> Tip: if the browser shows stale JavaScript after a redeploy, bump the version query string in `ui/index.html`:
> ```html
> <script src="script.js?v=4"></script>
> ```

---

## Cleanup

To delete all Azure resources when the project is no longer needed:

1. Go to **Azure Portal → Resource Groups**
2. Select your resource group
3. Click **Delete Resource Group** and confirm

This removes the Web App, Container Registry, and all associated resources.
