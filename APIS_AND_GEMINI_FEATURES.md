# 📚 APIs, GCP Services & Gemini AI Features Reference

This document provides a comprehensive technical index of all Google Cloud APIs, Gemini foundational models, Agent Development Kit (ADK) features, and external integrations used throughout the **FPL Scout** project.

---

## 🧠 1. Gemini & Multimodal Models

### 1.1 `gemini-3.6-flash`
- **Role**: Primary reasoning, planning, tactical dialogue, and tool calling engine.
- **Client Configuration**:
  ```python
  model = "gemini-3.6-flash"
  client_kwargs = {"location": "global"}
  ```
  *Note: Pinned explicitly to `global` region in `app/agent.py` to prevent regional 404 lookup failures across Cloud Reasoning Engine nodes.*
- **Responsibilities**:
  - Mini-league differential pick analysis.
  - Squad starting 11 lineup & captaincy selection.
  - Multi-gameweek transfer hit math calculations (-4 / -8 penalty evaluations).
  - Translating natural language football queries into dynamic A2UI surface components.

### 1.2 `gemini-3.1-flash-lite-image`
- **Role**: Multimodal image generation for visual scouting assets.
- **Model Endpoint**: `projects/{PROJECT_ID}/locations/global/publishers/google/models/gemini-3.1-flash-lite-image`
- **Capabilities & Implementations**:
  - **Tactical Pitch Formations**: Renders visual starting 11 pitch arrangements (e.g., 3-5-2, 4-3-3) with player jersey badges.
  - **Player Scouting & Radar Cards**: Graphical metric cards displaying player form, xG, xA, and fixture FDR difficulty.
  - **Chip Activation Banners**: Visual infographics for Wildcard, Triple Captain, Free Hit, and Bench Boost events.
- **Dual-Destination Pipeline**:
  1. Local Playground visualization via `tool_context.save_artifact(...)`.
  2. Direct programmatic byte streaming to Google Cloud Storage with public URL generation.

---

## 🎨 2. A2UI (Agent-to-User Interface) Integration

### 2.1 A2UI Schema & Versioning
- **Version**: `v0.8` (Basic Catalog specification).
- **Core Modules**:
  - `a2ui.schema.manager.A2uiSchemaManager`: Enforces strict contract structures for UI messages.
  - `a2ui_utils.py`: Provides custom `after_model_callback` hooks intercepting model outputs and converting structured visual blocks into A2UI events.
- **Supported Catalog Components**:
  - `Card`: Primary surface containers with elevated elevation and border outlines.
  - `Column` / `Row`: Flexbox layout containers supporting `spaceBetween` distribution and responsive alignment.
  - `Text`: Multi-tiered typography with semantics (`h1`, `h2`, `h3`, `body`, `caption`).
  - `Divider`: Visual separation bars.
  - `Image`: Safe-protocol (`https://`) asset rendering.
  - `Icon`: Material Symbols icon bindings mapped dynamically.

---

## 💾 3. Vertex AI Memory Bank (`shared://memory`)

### 3.1 Long-Term Context Retention
- **Service**: `VertexAiMemoryBankService` (Google Agent Development Kit).
- **URI Protocol**: `shared://memory` (deployed) and `agentengine://807048131857350656` (local playground).
- **Engine ID**: `807048131857350656`
- **Configuration** (`app/app_utils/services.py`):
  ```python
  from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService

  MEMORY_SERVICE_URI = "shared://memory"

  def get_memory_service():
      return VertexAiMemoryBankService(
          project="qwiklabs-gcp-04-2d53b9c1010c",
          location="us-east1",
          agent_engine_id="807048131857350656",
      )
  ```
- **Retained Entities**:
  - User FPL manager ID and team name (`Byebye veliya po!`).
  - Active mini-leagues (e.g., *Chennai PL Pasanga*).
  - Target transfer watchlist and budgetary constraints.
  - Historic chip utilization across the 38-gameweek season.

---

## ☁️ 4. Google Cloud Platform (GCP) APIs & Services

### 4.1 Vertex AI Reasoning Engine (Agent Platform)
- **API**: `aiplatform.googleapis.com`
- **Resource Identifier**:
  `projects/840012412258/locations/us-east1/reasoningEngines/8076420880386752512`
- **Role**: Scalable serverless execution environment hosting the containerized agent, tools, and session state.

### 4.2 Cloud Run
- **API**: `run.googleapis.com`
- **Deployed Service**: `fpl-scout-frontend`
- **Region**: `us-east1`
- **URL**: `https://fpl-scout-frontend-840012412258.us-east1.run.app`
- **Configuration**:
  - Stateless container running FastAPI + Uvicorn.
  - Communicates directly to the Vertex AI Reasoning Engine over the Agent-to-Agent (A2A) protocol.

### 4.3 Google Cloud Storage (GCS)
- **API**: `storage.googleapis.com`
- **Bucket**: `gs://bwg3-qwiklabs-gcp-04-2d53b9c1010c`
- **Usage**: Public hosting of dynamically generated tactical formation images, radar cards, and banners.
- **IAM Permission**: `roles/storage.objectAdmin` granted to the agent service account.

### 4.4 Cloud Firestore
- **API**: `firestore.googleapis.com`
- **Project**: `qwiklabs-gcp-04-2d53b9c1010c`
- **Role**: NoSQL document database storing team metadata, player cache tables, and differential tracking indices.
- **IAM Permission**: `roles/datastore.user` granted to agent and Reasoning Engine service accounts.

---

## 🌐 5. Protocols & Communication Standards

### 5.1 A2A Protocol (Agent-to-Agent SDK v1.x)
- **Protobuf Schemas**:
  - `SendMessageRequest`, `Message`, `Part`, `Role`.
  - Streaming responses parsed via `StreamResponse` supporting `artifactUpdate`, `task.artifacts`, and `statusUpdate`.
- **Endpoints**:
  - Card Discovery: `GET .../api/a2a/{AGENT_DIRECTORY}/.well-known/agent-card.json`
  - JSON-RPC Streaming: `POST .../api/a2a/{AGENT_DIRECTORY}`

### 5.2 Official Fantasy Premier League (FPL) APIs
- **Bootstrap Endpoint**: `https://fantasy.premierleague.com/api/bootstrap-static/` (Player lists, team IDs, price changes, fixture difficulty ratings).
- **Manager Profile**: `https://fantasy.premierleague.com/api/entry/{team_id}/`
- **Gameweek Squad**: `https://fantasy.premierleague.com/api/entry/{team_id}/event/{gw}/picks/`
- **Classic League Standings**: `https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/`

---

## 🔐 6. IAM Roles & Security Mapping

| Principal | Role | Purpose |
|---|---|---|
| `840012412258-compute@developer.gserviceaccount.com` | `roles/aiplatform.user` | Allows Cloud Run frontend proxy to call Reasoning Engine |
| `840012412258-compute@developer.gserviceaccount.com` | `roles/datastore.user` | Firestore read/write operations |
| `840012412258-compute@developer.gserviceaccount.com` | `roles/storage.objectAdmin` | Upload generated infographics to GCS bucket |
| `service-840012412258@gcp-sa-aiplatform-re.iam.gserviceaccount.com` | `roles/datastore.user` | Reasoning Engine runtime Firestore access |
| `service-840012412258@gcp-sa-aiplatform-re.iam.gserviceaccount.com` | `roles/storage.objectAdmin` | Reasoning Engine runtime image upload access |
