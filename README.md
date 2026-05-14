# Mars Rover Operator API

A RESTful API for controlling autonomous rovers on a configurable grid map, with real-time WebSocket support and a browser-based operator UI. Built with FastAPI and deployable via Docker on Azure.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, Pydantic |
| Server | Uvicorn (ASGI) |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Container | Docker |
| Cloud | Azure Container Registry, Azure Web Apps |

---

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) *(deployment only)*

---

## Local Development

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd mars-rover-api

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up frontend config
copy ui\config.example.js ui\config.js   # Windows
cp ui/config.example.js ui/config.js     # macOS / Linux
# Edit ui/config.js — for local use, no changes needed

# 5. Create your .env file
copy .env.example .env    # Windows
cp .env.example .env      # macOS / Linux
# Edit .env and set a strong API_KEY value

# 6. Run
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Docker

```bash
# Build the image
docker build -t mars-rover:latest .

# Run locally
docker run -p 80:80 -e API_KEY=your-api-key mars-rover:latest
```

Open [http://localhost](http://localhost) in your browser.

**Useful commands**

```bash
docker images                     # List local images
docker ps                         # List running containers
docker stop <container-id>        # Stop a container
docker rm <container-id>          # Remove a stopped container
docker rmi mars-rover:latest      # Delete the image
```

---

## Azure Deployment

```bash
# 1. Log in
az login
docker login <your-acr>.azurecr.io

# 2. Build and tag for ACR (increment version each deploy)
docker build -t <your-acr>.azurecr.io/mars-rover:v1 .

# 3. Push to ACR
docker push <your-acr>.azurecr.io/mars-rover:v1
```

**4. Deploy to Web App**
- Azure Portal → Web App → Deployment Center
- Set the image tag to your new version → **Save**

**Required Web App settings**

| Setting | Value |
|---|---|
| `API_KEY` | Your secret key (Environment Variables) |
| `WEBSITES_PORT` | `80` (Environment Variables) |
| Always On | Enabled (General Settings) |
| WebSockets | Enabled (General Settings) |

---

## Configuration

Copy `ui/config.example.js` → `ui/config.js` and fill in your values:

```js
window.AZURE_URL = "your-app.azurewebsites.net";
window.API_KEY   = "your-secret-api-key";
```

This file is gitignored and will never be committed.

To generate a strong API key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## API Reference

All endpoints require the header `X-API-Key: <your-key>`.

### Map
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/map` | Get map dimensions and mines |
| `PUT` | `/map` | Update map size (max 100×100) |

### Mines
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/mines` | List all mines |
| `POST` | `/mines` | Create a mine (max 50) |
| `PUT` | `/mines/{id}` | Update a mine |
| `DELETE` | `/mines/{id}` | Remove a mine |

### Rovers
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/rovers` | List all rovers |
| `POST` | `/rovers` | Create a rover (max 10) |
| `PUT` | `/rovers/{id}` | Update rover commands (max 200 chars) |
| `DELETE` | `/rovers/{id}` | Delete a rover |
| `POST` | `/rovers/{id}/dispatch` | Run the rover's command sequence |
| `WS` | `/ws/rovers/{id}/control?api_key=` | Real-time control via WebSocket |

---

## Updating a Deployment

```bash
docker build -t <your-acr>.azurecr.io/mars-rover:v2 .
docker push <your-acr>.azurecr.io/mars-rover:v2
# Update the tag in Azure Deployment Center → Save
```

---

## Cleanup

Azure Portal → Resource Groups → select your group → **Delete Resource Group**.
