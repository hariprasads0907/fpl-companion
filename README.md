# ⚽ FPL Scout — Fantasy Premier League Tactical Agent

An agentic AI assistant designed for **Fantasy Premier League (FPL)** managers. Built on **Google Cloud Agent Platform (Reasoning Engine)**, powered by **Gemini 3.6 Flash**, and integrated with **A2UI**, **Memory Bank**, **Google Cloud Storage**, **Firestore**, and **Cloud Run**.

---

## 🚀 Live Deployments

- **Frontend (Cloud Run)**: [https://fpl-scout-frontend-840012412258.us-east1.run.app](https://fpl-scout-frontend-840012412258.us-east1.run.app)
- **Agent Engine (Reasoning Engine)**: `projects/840012412258/locations/us-east1/reasoningEngines/8076420880386752512`
- **Memory Bank (Agent Engine ID)**: `807048131857350656`
- **GCS Bucket (Scouting Images & Radar Cards)**: `gs://bwg3-qwiklabs-gcp-04-2d53b9c1010c`
- **GCP Project**: `qwiklabs-gcp-04-2d53b9c1010c` (Location: `us-east1`)

---

## 📌 Architecture & Features

```
               ┌────────────────────────────────────────────────────────┐
               │              FPL Scout Frontend (Cloud Run)            │
               │   FastAPI Proxy + Branded FPL Chat UI + A2UI v0.8     │
               └───────────────────────────┬────────────────────────────┘
                                           │ A2A Protocol (gRPC/HTTP)
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           Agent Engine (Vertex AI Reasoning Engine)    │
               │                   gemini-3.6-flash                     │
               └───────┬───────────────────┬───────────────────┬────────┘
                       │                   │                   │
                       ▼                   ▼                   ▼
       ┌───────────────────────┐ ┌───────────────────┐ ┌────────────────┐
       │   Memory Bank (Vertex)│ │ Firestore Database│ │ Imagen (GCS)   │
       │ Persistent FPL stats, │ │ Manager details,  │ │ Pitch diagrams │
       │ user squads & watch   │ │ player stats      │ │ Radar cards    │
       └───────────────────────┘ └───────────────────┘ └────────────────┘
```

### Core Capabilities
1. **Mini-League Differential Scouting**:
   - Analyzes mini-league rivals' squads and recommends low-ownership high-upside differential picks for upcoming gameweeks to help you climb the leaderboard.
2. **Lineup & Captaincy Engine**:
   - Optimal starting 11 selection, vice-captain backup, bench order prioritization, and fixture difficulty rating (FDR) assessment.
3. **Transfer Hit Calculator**:
   - Evaluates whether taking a `-4` or `-8` point deduction is mathematically justifiable over a 3-gameweek horizon.
4. **Interactive A2UI Cards (v0.8 Basic Catalog)**:
   - Dynamic UI cards rendered in the browser (welcome dashboard, player scouting cards, chip activation banners, squad comparison tables).
5. **AI Image Generation**:
   - Uses `gemini-3.1-flash-lite-image` in global region to produce tactical pitch formations, radar scouting cards, and chip activation infographics uploaded directly to public Cloud Storage.
6. **Cross-Session Memory Bank**:
   - Powered by Vertex AI Memory Bank (`shared://memory`), remembering manager profile, favorite clubs, budget headroom, and chip usage history across chats.

---

## 🛠️ Step-by-Step Build History & Implementation

### Phase 1: Core Agent & Domain Setup
- Implemented FPL tools for fetching manager profiles, squad data, mini-league standings, player form, and FDR tables.
- Seeded Firestore collections for persistent team metadata.

### Phase 2: Multimodal Image Generation Tool
- Implemented `generate_formation_image` tool with `gemini-3.1-flash-lite-image`.
- Configured double-destination handling:
  1. `tool_context.save_artifact` for local Playground visualization.
  2. Direct upload to `gs://bwg3-qwiklabs-gcp-04-2d53b9c1010c` returning public HTTPS URLs.

### Phase 3: Vertex AI Memory Bank Integration
- Wired `VertexAiMemoryBankService` in `app/app_utils/services.py` with `MEMORY_SERVICE_URI = "shared://memory"`.
- Connected to reused Memory Bank engine `807048131857350656`.

### Phase 4: A2UI v0.8 Rich Visual Interfaces
- Integrated `A2uiSchemaManager(version="v0.8", catalog=BASIC_CATALOG)` in `app/agent.py`.
- Injected system prompt guidelines for A2UI JSON structures (`beginRendering` and `surfaceUpdate`).
- Created and vendored `a2ui_utils.py` and the `a2ui` core package into `app/` with an `after_model_callback` pipeline.

### Phase 5: Agent Platform Deployment & IAM Configuration
- Fixed region pinning by configuring `client_kwargs={"location": "global"}` on the LLM client.
- Deployed agent to Agent Platform:
  `agents-cli deploy --no-confirm-project` -> Resource `8076420880386752512`.
- Configured Cloud IAM permissions:
  - `roles/datastore.user` on Firestore for agent service accounts.
  - `roles/storage.objectAdmin` on GCS image bucket for agent service accounts.

### Phase 6: Frontend Proxy & Plain Chat UI
- Created minimal FastAPI proxy in `./frontend/main.py`.
- Configured compatibility with `a2a-sdk` v1.x protobuf streaming, `A2ACardResolver`, and structured JSON-RPC passthrough.
- Built interactive chat interface supporting both plain text and client-rendered A2UI cards.

### Phase 7: Rebranding & UI Polish
- Customized dark theme with Premier League Deep Purple (`#37003c`), Cyan, and Mint Green (`#00ff87`).
- Added 3 interactive prompt chips:
  - Mini-League Differentials
  - Lineup & Captaincy Picks
  - Player Scout & Fixtures

### Phase 8: Cloud Run Production Deployment
- Deployed frontend to Cloud Run:
  `gcloud run deploy fpl-scout-frontend --region us-east1 --allow-unauthenticated`
- Granted `roles/aiplatform.user` to the Cloud Run compute service account (`840012412258-compute@developer.gserviceaccount.com`).

---

## 💻 Local Development

### Prerequisites
- Python 3.11+ / uv package manager
- Google Cloud SDK (`gcloud`) authenticated to GCP project `qwiklabs-gcp-04-2d53b9c1010c`

### Running the Agent Playground Locally
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://807048131857350656
```

### Running the Frontend Locally
```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/840012412258/locations/us-east1/reasoningEngines/8076420880386752512"
export AGENT_DIRECTORY="app"
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## 📂 Repository Structure

```
├── app/
│   ├── a2ui/                  # Vendored A2UI package
│   ├── app_utils/             # Service definitions & memory bank
│   ├── agent.py               # Root ADK agent with Gemini 3.6 Flash & A2UI callback
│   ├── a2ui_utils.py          # A2UI callback hooks and schemas
│   ├── fast_api_app.py        # Local API server definition
│   └── tools.py               # FPL stats, differential picks & image generator
├── frontend/
│   ├── static/
│   │   └── index.html         # FPL-branded chat interface with A2UI renderer
│   ├── main.py                # FastAPI A2A client proxy to Reasoning Engine
│   └── requirements.txt       # Cloud Run dependencies
├── agents-cli-manifest.yaml   # Manifest for agents-cli deployment
├── deployment_metadata.json   # Deployed Reasoning Engine ID & metadata
├── project_brief.md           # Project specification & capabilities
└── pyproject.toml             # Python dependencies
```
