# IT Helpdesk & Incident Assistant Agent

<p align="center">
  <img src="https://img.shields.io/badge/Google%20Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="Google Cloud" />
  <img src="https://img.shields.io/badge/Vertex%20AI-Agent%20Runtime-8E44AD?style=for-the-badge&logo=google&logoColor=white" alt="Vertex AI Agent Runtime" />
  <img src="https://img.shields.io/badge/Framework-Google%20ADK-34A853?style=for-the-badge&logo=google&logoColor=white" alt="Google ADK Framework" />
  <img src="https://img.shields.io/badge/Memory-Vertex%20AI%20Memory%20Bank-FF6F00?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Vertex AI Memory Bank" />
  <img src="https://img.shields.io/badge/UI-A2UI%20v0.8-00C853?style=for-the-badge" alt="A2UI v0.8" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge" alt="License" />
</p>

![IT Helpdesk Agent Demo](./demo.gif)

## 📌 Project Overview

**IT Helpdesk & Incident Assistant Agent** is an enterprise-grade autonomous IT support agent built with the **Google Agent Development Kit (ADK)** framework and deployed to **Vertex AI Agent Runtime**. 

The assistant streamlines internal enterprise IT support operations by resolving service disruptions, managing support ticket lifecycles in Google Cloud Firestore, generating equipment media via Imagen & Omni models (`gemini-omni-flash-preview`), maintaining persistent user preferences across sessions via **Vertex AI Memory Bank**, and rendering dynamic structured UI surfaces via **Agent-to-User Interface (A2UI v0.8)**.

---

## 🎯 What Problem Does This Project Solve?

Modern enterprise IT departments face critical operational bottlenecks:

1. **High Ticket Backlog & Long Resolution Delays**: L1 support teams spend excessive hours manually categorizing, querying, and updating repetitive IT incident tickets.
2. **Context Loss Across Support Sessions**: Traditional helpdesk bots forget employee hardware configurations, past ticket histories, and dietary or accessibility sensitivities between chat sessions.
3. **Lack of Visual Equipment Walkthroughs**: Employees struggling with hardware issues (e.g. router setup, laptop dock replacement) receive plain text instructions rather than clear visual diagrams or video guides.
4. **Opaque Service Status Telemetry**: Employees lack real-time visibility into internal corporate service outages (VPN, SSO, Cloud Identity, Email) before opening redundant tickets.

---

## 💡 Key Benefits of IT Helpdesk Assistant Agent

- **Long-Term Memory via Vertex AI Memory Bank**: Integrates `VertexAiMemoryBankService` to recall user hardware setups, OS preferences, and sensitivities across multi-turn interactions.
- **Real-Time Ticket Management in Cloud Firestore**: Full CRUD support for helpdesk tickets (`tickets` collection) with lazy database client initialization (`get_ticket`, `list_user_tickets`, `create_ticket`, `update_ticket_status`).
- **Multimodal Asset & Video Generation**: Generates high-resolution equipment images via `gemini-3.1-flash-lite-image` and short video walkthroughs using Google's Gemini Omni model (`gemini-omni-flash-preview`) in the `global` region.
- **Rich Agent-to-User Interface (A2UI)**: Outputs structured JSON component trees (`Card`, `Column`, `Row`, `Text`, `Image`, `Video`) parsed by `a2ui_callback` for native web client rendering.
- **Isolated Code Sandbox Execution**: Executes custom Python diagnostic scripts within an isolated sandbox environment (`AgentEngineSandboxCodeExecutor`).

---

## 📖 Comprehensive User Manual & Usage Guide

This step-by-step manual guides system administrators, IT support agents, and enterprise employees on how to effectively operate the IT Helpdesk Assistant Agent.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      IT HELPDESK ASSISTANT AGENT CANVAS                                 │
├──────────────────────────────┬──────────────────────────────┬──────────────────────────┤
│ 1. Incident Control Panel    │ 2. Interactive Chat Studio   │ 3. A2UI Surface & Cards  │
│  - System Service Status     │  - Real-Time Token Stream    │  - Structured Ticket Cards│
│  - Active Outage Banner      │  - Voice Input Microphone    │  - Generated Video Player│
│  - Quick Prompt Chips        │  - Tool Call Accordions      │  - Equipment Photo Gallery│
└──────────────────────────────┴──────────────────────────────┴──────────────────────────┘
```

### Step 1: Launching the Local Agent Studio
1. Open terminal and run the FastAPI frontend proxy server:
   ```bash
   python frontend/main.py
   ```
2. Open your web browser and navigate to:
   ```text
   http://localhost:8080
   ```

---

### Step 2: Filing & Tracking IT Support Tickets
1. **Filing a New Support Incident**:
   - Type a prompt detailing your issue into the chat input:
     ```text
     My corporate VPN fails to connect with error code 800. Please file an urgent ticket.
     ```
   - The agent executes `create_ticket`, creating a new Firestore document and rendering an **A2UI Ticket Summary Card**.
2. **Checking Active Ticket Status**:
   - Ask the agent:
     ```text
     What is the status of my open tickets?
     ```
   - The agent calls `list_user_tickets` and returns a structured list of assigned tickets.

---

### Step 3: Utilizing Long-Term User Memory
1. State a preference or fact during a session:
   ```text
   Note that I use a MacBook Pro 16-inch M3 Max with an external 4K DisplayPort monitor.
   ```
2. In subsequent support sessions, ask hardware-specific questions:
   ```text
   How do I reset my display arrangement?
   ```
3. The agent retrieves memory facts via `VertexAiMemoryBankService` and tailors troubleshooting steps specifically for macOS and your M3 setup.

---

### Step 4: Generating Equipment Visuals & Videos
1. Request an equipment visual walkthrough:
   ```text
   Generate a quick video showing how to plug in the Dual USB-C Laptop Docking Station.
   ```
2. The `generate_equipment_video` tool function:
   - Invokes Google's Gemini Omni model (`gemini-omni-flash-preview`) in the `global` region.
   - Registers video blobs with `tool_context.save_artifact`.
   - Streams bytes to Google Cloud Storage bucket (`it-helpdesk-assets-4aae627fbb97`).
3. View the generated video stream rendered inside an interactive **A2UI Media Card**.

---

## 🔑 Required APIs, Tools & IAM Access Permissions

To deploy and execute all features in this repository, ensure the following Google Cloud APIs, CLI tools, software libraries, and IAM roles are provisioned:

### 1. 🌐 Google Cloud APIs Required
- **Vertex AI API** (`aiplatform.googleapis.com`): Invokes Vertex AI Reasoning Engine, Memory Bank, and Gemini Omni models.
- **Cloud Storage API** (`storage.googleapis.com`): Handles byte streaming and public GCS asset hosting.
- **Cloud Firestore API** (`firestore.googleapis.com`): Manages document storage for support tickets.
- **Cloud Run API** (`run.googleapis.com`): Hosts the FastAPI web client.

### 2. 🛡️ Required IAM Roles & Permissions
- **Vertex AI User** (`roles/aiplatform.user`): Granted to the executing service account/user to run Reasoning Engines and Omni models.
- **Storage Object Admin** (`roles/storage.objectAdmin`): Granted to write equipment media files into Cloud Storage.
- **Datastore User** (`roles/datastore.user`): Granted to read/write Firestore ticket documents.
- **Storage Object Viewer (`roles/storage.objectViewer`) for `allUsers`**: Granted on the GCS bucket (`gs://it-helpdesk-assets-4aae627fbb97`).

### 3. 🐍 Required Python Packages
```bash
pip install google-adk google-genai google-cloud-storage google-cloud-firestore fastapi uvicorn pydantic numpy scipy
```

### 4. 🛠️ CLI & Runtime Requirements
- **`agents-cli`**: Google Agents CLI for scaffolding, evaluating, and deploying ADK agents to Vertex AI Agent Runtime.
- **`gcloud` CLI**: Google Cloud SDK for Cloud Run deployment and IAM configuration.
- **`Python 3.10+`**: Python runtime.

---

## ⚡ Prerequisites

Before setting up or deploying IT Helpdesk & Incident Assistant Agent, ensure you have:

1. **Google Cloud Platform Account & Project**:
   - Active GCP Project with billing enabled.
   - Vertex AI API & Firestore database initialized.
2. **GCP Cloud Storage Bucket**:
   - Public GCS bucket configured (e.g., `it-helpdesk-assets-4aae627fbb97`).
3. **Local Development Tools**:
   - Python 3.10+
   - Google Cloud SDK (`gcloud`) authenticated (`gcloud auth application-default login`).

---

## ⚙️ Post-Settings & Environment Configuration

After cloning the repository, perform the following post-settings to configure public video uploads and permissions:

### 1. Bucket IAM Public Read Configuration
Grant public object viewer access to your GCS bucket so generated equipment videos are viewable over HTTPS:
```bash
gcloud storage buckets add-iam-policy-binding gs://it-helpdesk-assets-4aae627fbb97 \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

### 2. Vertex AI Global Region & Project Setup
Export your environment variables:
```bash
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_REGION="us-east1"
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-east1/reasoningEngines/<REASONING_ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT=8080
```

### 3. Application Authentication
Initialize Application Default Credentials (ADC):
```bash
gcloud auth application-default login
```

---

## 💻 Local Setup & Execution Instructions

### 1. Install Dependencies
```bash
pip install -r frontend/requirements.txt
```

### 2. Seed Firestore Database (Optional Initial Data)
```bash
python seed_firestore.py
```

### 3. Start Local Web Server
```bash
python frontend/main.py
```

Access the agent interface locally in your browser at `http://localhost:8080`.

---

## ☁️ Deployment Guide

### Deploy Agent to Vertex AI Agent Runtime
```bash
agents-cli deploy --no-confirm-project --project <YOUR_GCP_PROJECT_ID>
```

### Deploy Frontend to Cloud Run
```bash
gcloud run deploy it-helpdesk-frontend \
  --source ./frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<YOUR_REASONING_ENGINE_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```

Grant the Cloud Run compute service account permission to invoke Reasoning Engine:
```bash
gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

## 📁 Project Directory & File Structure

```text
it-helpdesk-agent/
├── README.md                     # Comprehensive project documentation & guide
├── LICENSE                       # Apache License 2.0
├── demo.gif                      # Looping demo video recording
├── lofi_track.wav                # Synthesized lo-fi background audio track
├── agents-cli-manifest.yaml      # ADK Agent Runtime deployment manifest
├── deployment_metadata.json      # Deployed Reasoning Engine metadata
├── pyproject.toml                # Python project configuration & dependencies
├── uv.lock                       # Locked dependency versions
├── Dockerfile                    # Container definition for Cloud Run deployment
├── .env.example                  # Template environment variables
├── app/                          # Core ADK Agent Package
│   ├── agent.py                  # ADK Root Agent, tool definitions, Firestore & Memory Bank setup
│   ├── a2ui_utils.py             # A2UI schema parsing & model callback handlers
│   ├── fast_api_app.py           # FastAPI application module
│   └── app_utils/                # Internal utility modules
│       ├── a2a.py                # Agent-to-Agent protocol handlers
│       ├── reasoning_engine_adapter.py # Reasoning Engine deployment wrapper
│       ├── services.py           # Shared GCP service clients
│       ├── telemetry.py          # Telemetry and logging utilities
│       └── typing.py             # Type definitions
├── frontend/                     # Web Frontend Package
│   ├── main.py                   # FastAPI proxy server contacting Agent Engine
│   ├── requirements.txt          # Frontend dependencies
│   └── static/
│       └── index.html            # Web client (Dark/Light mode, IT status banner, A2UI renderer)
├── tools/                        # Helpdesk Diagnostic & Media Tools
│   ├── ticket_tools.py           # Firestore ticket CRUD operations
│   ├── media_tools.py            # Imagen & Gemini Omni video generation
│   └── memory_tools.py           # PreloadMemoryTool & Memory Bank integration
├── scripts/                      # Utility and Automation Scripts
│   ├── create_lofi_music.py      # Audio synthesizer script
│   ├── record_demo.py            # Playwright demo video recorder
│   └── seed_firestore.py         # Firestore initial data seeder
├── deployment/                   # Infrastructure as Code
│   └── terraform/                # Terraform GCP resource templates
└── tests/                        # Automated Test Suites
    ├── test_agent.py             # ADK agent unit tests
    └── test_a2ui.py              # A2UI schema verification tests
```

---

## 🛠️ Google Cloud Services & Tools Status

| Service / Tool | Status | Details |
|---|---|---|
| **Vertex AI Agent Runtime** | `Implemented` | Deployed Reasoning Engine endpoint managing agent invocation and tool execution. |
| **Vertex AI Memory Bank** | `Implemented` | `VertexAiMemoryBankService` preserving long-term user context and preferences across sessions. |
| **Google Cloud Storage (GCS)** | `Implemented` | Public asset hosting (`it-helpdesk-assets-4aae627fbb97`) for generated equipment images and videos. |
| **Google Cloud Firestore** | `Implemented` | Live document storage for support tickets (`tickets` collection) with `seed_firestore.py`. |
| **Vertex AI / Gemini Omni Model** | `Implemented` | `gemini-omni-flash-preview` in `global` region for video walkthrough generation. |
| **Vertex AI / Imagen Image Model** | `Implemented` | `gemini-3.1-flash-lite-image` for high-resolution hardware visual creation. |
| **Agent-to-User Interface (A2UI v0.8)** | `Implemented` | Structured JSON cards (`Card`, `Column`, `Row`, `Text`, `Image`, `Video`) parsed by `a2ui_callback`. |
| **Code Execution Sandbox** | `Implemented` | `AgentEngineSandboxCodeExecutor` for isolated diagnostic script execution. |
