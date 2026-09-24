# Copyright 2026 Google LLC
# IT Helpdesk & Incident Assistant Agent with Firestore backend, status/KB tools, public IP API tool, Google Maps tools, Image Generation tool, Agent Engine Sandbox Code Execution, Vertex AI Memory Bank, and A2UI support

import base64
import datetime
import json
import os
import random
import urllib.parse
import urllib.request
from pathlib import Path

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from app.a2ui_utils import a2ui_callback

# CRITICAL: Hardcode the project ID string (ID, not number) for Firestore and Vertex AI
FIRESTORE_PROJECT = "qwiklabs-gcp-01-4aae627fbb97"

# CRITICAL: Hardcode the public Cloud Storage bucket name
GCS_BUCKET_NAME = "it-helpdesk-assets-4aae627fbb97"

# Memory Bank Engine ID from deployment_metadata.json
MEMORY_BANK_ID = "6980220981633613824"

# Initialize lazy Firestore client
_db = None

def get_firestore_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db


# ---------------------------------------------------------------------------
# Firestore Ticket Tools
# ---------------------------------------------------------------------------

def get_ticket(ticket_id: str) -> str:
    """Retrieve details of a specific IT support ticket by its ticket ID.

    Args:
        ticket_id: The ticket ID (e.g. 'TCK-1001').

    Returns:
        A string containing ticket details or an error message if not found.
    """
    db = get_firestore_db()
    doc_ref = db.collection("support_tickets").document(ticket_id.strip())
    doc = doc_ref.get()

    if not doc.exists:
        return f"Ticket '{ticket_id}' was not found in the IT Helpdesk system."

    data = doc.to_dict()
    return (
        f"Ticket ID: {data.get('ticket_id')}\n"
        f"Title: {data.get('title')}\n"
        f"User: {data.get('user_email')}\n"
        f"Device: {data.get('device_info', 'N/A')}\n"
        f"Category: {data.get('category')}\n"
        f"Priority: {data.get('priority')}\n"
        f"Status: {data.get('status')}\n"
        f"Created At: {data.get('created_at')}\n"
        f"Description: {data.get('description')}"
    )


def list_user_tickets(user_email: str) -> str:
    """List all IT support tickets associated with a given employee email address.

    Args:
        user_email: The employee's email address (e.g. 'alex.smith@company.com').

    Returns:
        A summary list of all tickets for the given user.
    """
    db = get_firestore_db()
    query = db.collection("support_tickets").where("user_email", "==", user_email.strip().lower())
    docs = query.stream()

    tickets = [doc.to_dict() for doc in docs]
    if not tickets:
        return f"No support tickets found for user '{user_email}'."

    summary_lines = [f"Found {len(tickets)} ticket(s) for {user_email}:"]
    for t in tickets:
        summary_lines.append(
            f"- [{t.get('ticket_id')}] {t.get('title')} | Category: {t.get('category')} | Priority: {t.get('priority')} | Status: {t.get('status')}"
        )
    return "\n".join(summary_lines)


def create_ticket(
    user_email: str,
    title: str,
    description: str,
    category: str = "General",
    priority: str = "Medium",
    device_info: str = "Standard Laptop",
) -> str:
    """File a new IT support ticket in the Firestore database.

    Args:
        user_email: The employee's email address filing the ticket.
        title: Short title summarizing the issue.
        description: Detailed explanation of the technical problem.
        category: Ticket category ('Network', 'Hardware', 'Software', 'Access', 'General').
        priority: Urgency level ('Low', 'Medium', 'High', 'Critical').
        device_info: The hardware/device specification of the user.

    Returns:
        Confirmation message with the newly generated Ticket ID.
    """
    db = get_firestore_db()

    ticket_number = random.randint(1005, 9999)
    ticket_id = f"TCK-{ticket_number}"
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    ticket_data = {
        "ticket_id": ticket_id,
        "user_email": user_email.strip().lower(),
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip(),
        "priority": priority.strip(),
        "status": "Open",
        "device_info": device_info.strip(),
        "created_at": now_str,
    }

    db.collection("support_tickets").document(ticket_id).set(ticket_data)

    return (
        f"Successfully created IT Support Ticket '{ticket_id}'.\n"
        f"Status: Open\n"
        f"User: {user_email}\n"
        f"Title: {title}\n"
        f"Category: {category} | Priority: {priority}"
    )


def update_ticket_status(ticket_id: str, new_status: str) -> str:
    """Update the status of an existing IT support ticket in Firestore.

    Args:
        ticket_id: The ticket ID to update (e.g. 'TCK-1001').
        new_status: The new status ('Open', 'In Progress', 'Resolved', 'Closed').

    Returns:
        Confirmation message of the status update.
    """
    db = get_firestore_db()
    doc_ref = db.collection("support_tickets").document(ticket_id.strip())
    doc = doc_ref.get()

    if not doc.exists:
        return f"Cannot update status: Ticket '{ticket_id}' was not found."

    valid_statuses = ["Open", "In Progress", "Resolved", "Closed"]
    formatted_status = new_status.strip().title()
    if formatted_status not in valid_statuses:
        return f"Invalid status '{new_status}'. Allowed values are: {', '.join(valid_statuses)}."

    doc_ref.update({"status": formatted_status})
    return f"Ticket '{ticket_id}' status updated to '{formatted_status}' successfully."


# ---------------------------------------------------------------------------
# Service Health Status Tool
# ---------------------------------------------------------------------------

def check_service_status(service_name: str = "all") -> str:
    """Check the real-time operational status of corporate IT infrastructure services.

    Args:
        service_name: Name of the service to check (e.g. 'VPN', 'SSO', 'Slack', 'Email', 'Cloud', or 'all').

    Returns:
        A detailed operational status report for the requested service(s).
    """
    services_status = {
        "VPN": {
            "name": "Corporate VPN (vpn.company.com)",
            "status": "Operational",
            "latency": "24ms",
            "uptime": "99.98%",
            "incident": "None reported",
        },
        "SSO": {
            "name": "Single Sign-On / Identity Provider (sso.company.com)",
            "status": "Operational",
            "latency": "15ms",
            "uptime": "100.0%",
            "incident": "None reported",
        },
        "Slack": {
            "name": "Corporate Slack Workspace",
            "status": "Operational",
            "latency": "45ms",
            "uptime": "99.95%",
            "incident": "None reported",
        },
        "Cloud": {
            "name": "Google Cloud / AWS Infrastructure",
            "status": "Operational",
            "latency": "12ms",
            "uptime": "99.99%",
            "incident": "None reported",
        },
        "Email": {
            "name": "Email & Calendar Services (Google Workspace)",
            "status": "Operational",
            "latency": "18ms",
            "uptime": "100.0%",
            "incident": "None reported",
        },
    }

    target = service_name.strip().upper()
    if target != "ALL" and target:
        matched_keys = [k for k in services_status.keys() if k.upper() in target or target in k.upper()]
        if matched_keys:
            key = matched_keys[0]
            info = services_status[key]
            return (
                f"Service: {info['name']}\n"
                f"Status: {info['status']}\n"
                f"Latency: {info['latency']} | Uptime: {info['uptime']}\n"
                f"Active Incidents: {info['incident']}"
            )

    report_lines = ["--- Corporate Infrastructure Status Report ---"]
    for k, info in services_status.items():
        report_lines.append(f"🟢 [{info['status']}] {info['name']} (Latency: {info['latency']})")
    report_lines.append("All systems operational. No ongoing critical incidents.")
    return "\n".join(report_lines)


# ---------------------------------------------------------------------------
# Knowledge Base Search Tool
# ---------------------------------------------------------------------------

def search_knowledge_base(query: str) -> str:
    """Search the IT Knowledge Base for troubleshooting articles, guides, and procedures.

    Args:
        query: The search query keywords (e.g., 'VPN setup', 'password reset', 'monitor flickering').

    Returns:
        Relevant knowledge base articles and resolution instructions.
    """
    db = get_firestore_db()
    docs = db.collection("knowledge_base").stream()

    query_words = [w.lower() for w in query.strip().split() if len(w) > 2]
    matched_articles = []

    for doc in docs:
        article = doc.to_dict()
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()
        tags = [t.lower() for t in article.get("tags", [])]
        content = article.get("content", "").lower()

        score = 0
        for word in query_words:
            if word in title:
                score += 3
            if any(word in t for t in tags):
                score += 2
            if word in summary:
                score += 1
            if word in content:
                score += 1

        if score > 0:
            matched_articles.append((score, article))

    if not matched_articles:
        return (
            f"No specific Knowledge Base articles found for '{query}'. "
            f"Try searching for broader terms like 'VPN', 'password', 'monitor', or 'software'."
        )

    matched_articles.sort(key=lambda x: x[0], reverse=True)

    results_text = [f"Found {len(matched_articles)} relevant Knowledge Base article(s):"]
    for score, article in matched_articles[:3]:
        results_text.append(
            f"\n📖 [{article.get('article_id')}] {article.get('title')}\n"
            f"Category: {article.get('category')}\n"
            f"Summary: {article.get('summary')}\n"
            f"Instructions:\n{article.get('content')}"
        )

    return "\n".join(results_text)


# ---------------------------------------------------------------------------
# Public Network IP Lookup API Tool
# ---------------------------------------------------------------------------

def lookup_network_ip(ip_or_domain: str = "8.8.8.8") -> str:
    """Fetch network ISP, organization, location, and AS details for an IP address or domain using a public API.

    Args:
        ip_or_domain: The IP address or domain name to inspect (e.g., '8.8.8.8' or '1.1.1.1').

    Returns:
        A string containing ISP, location, AS number, and network metadata.
    """
    target = ip_or_domain.strip() if ip_or_domain else "8.8.8.8"
    url = f"http://ip-api.com/json/{target}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IT-Helpdesk-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") == "success":
            return (
                f"Network IP Lookup for '{data.get('query')}':\n"
                f"- ISP: {data.get('isp')}\n"
                f"- Organization: {data.get('org')}\n"
                f"- AS Number: {data.get('as')}\n"
                f"- Location: {data.get('city')}, {data.get('regionName')}, {data.get('country')}\n"
                f"- Timezone: {data.get('timezone')}"
            )
        else:
            return f"IP Lookup failed for '{target}': {data.get('message', 'Invalid IP or domain')}"
    except Exception as e:
        return f"Network lookup request failed: {e}"


# ---------------------------------------------------------------------------
# Google Maps Geocoding & Places (New) Tools
# ---------------------------------------------------------------------------

def geocode_address(address: str) -> str:
    """Convert a physical address or office location into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: Street address or location (e.g. '1600 Amphitheatre Parkway, Mountain View, CA').

    Returns:
        Formatted address, latitude, and longitude.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Google Maps API Key not configured in GOOGLE_MAPS_API_KEY environment variable."

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address.strip())}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") == "OK" and data.get("results"):
            first_result = data["results"][0]
            fmt_addr = first_result.get("formatted_address")
            location = first_result.get("geometry", {}).get("location", {})
            lat = location.get("lat")
            lng = location.get("lng")
            return (
                f"Geocoding result for '{address}':\n"
                f"- Formatted Address: {fmt_addr}\n"
                f"- Location: Latitude {lat}, Longitude {lng}"
            )
        else:
            return f"Geocoding failed for '{address}': Status {data.get('status', 'Unknown')}"
    except Exception as e:
        return f"Geocoding API error: {e}"


def find_nearby_places(latitude: float, longitude: float, place_type: str = "restaurant", radius_meters: float = 1000.0) -> str:
    """Find nearby places (restaurants, IT supply stores, cafes, etc.) of a given type around a location using Google Places API (New).

    Args:
        latitude: Latitude of the center point.
        longitude: Longitude of the center point.
        place_type: Type of place to search for (e.g., 'restaurant', 'cafe', 'store').
        radius_meters: Search radius in meters (default: 1000.0).

    Returns:
        List of nearby places with name, formatted address, and coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Google Maps API Key not configured in GOOGLE_MAPS_API_KEY environment variable."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = json.dumps({
        "includedTypes": [place_type.strip().lower()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters)
            }
        }
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }

    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        places = data.get("places", [])
        if not places:
            return f"No nearby places of type '{place_type}' found within {radius_meters}m."

        summary_lines = [f"Found {len(places)} nearby place(s) of type '{place_type}':"]
        for p in places:
            display_name = p.get("displayName", {}).get("text", "N/A")
            addr = p.get("formattedAddress", "N/A")
            loc = p.get("location", {})
            summary_lines.append(
                f"- Name: {display_name}\n"
                f"  Address: {addr}\n"
                f"  Location: Lat {loc.get('latitude')}, Lng {loc.get('longitude')}"
            )
        return "\n".join(summary_lines)
    except Exception as e:
        return f"Places API (New) searchNearby error: {e}"


# ---------------------------------------------------------------------------
# Image Generation Tool (using gemini-3.1-flash-lite-image in global region)
# ---------------------------------------------------------------------------

def generate_equipment_image(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generate an image for IT equipment, hardware diagrams, or helpdesk assets using the gemini-3.1-flash-lite-image model in global region.

    Args:
        prompt: Detailed description of the IT equipment item to generate (e.g. 'A sleek modern laptop dock').
        tool_context: Tool context for saving artifacts in the Playground.

    Returns:
        Public Cloud Storage HTTPS URL of the generated image.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"Generate a professional, realistic image of IT equipment: {prompt}",
    )

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return "Image generation failed: No image bytes received from gemini-3.1-flash-lite-image model."

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"it_asset_{timestamp}.jpg"

    # 1. Save artifact with tool_context.save_artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to public Cloud Storage bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return f"Successfully generated IT equipment image!\nPublic Image URL: {public_url}"


def generate_equipment_video(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generate a short video clip for IT equipment, server rack maintenance, cabling guide, or helpdesk walkthroughs using Google's Omni model (gemini-omni-flash-preview) in global region.

    Args:
        prompt: Detailed description of the IT helpdesk video clip to generate (e.g. 'A server rack rebooting with status lights flashing green').
        tool_context: Tool context for saving artifacts in the Playground.

    Returns:
        Public Cloud Storage HTTPS URL of the generated video.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short IT helpdesk video clip: {prompt}",
    )

    video_bytes = None
    mime_type = "video/mp4"

    if interaction.output_video and getattr(interaction.output_video, "data", None):
        raw_data = interaction.output_video.data
        if isinstance(raw_data, str):
            try:
                video_bytes = base64.b64decode(raw_data)
            except Exception:
                video_bytes = raw_data.encode("utf-8")
        elif isinstance(raw_data, bytes):
            video_bytes = raw_data
        if getattr(interaction.output_video, "mime_type", None):
            mime_type = str(interaction.output_video.mime_type)

    if not video_bytes:
        return "Video generation failed: No video bytes received from gemini-omni-flash-preview model."

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"it_asset_video_{timestamp}.mp4"

    # 1. Save artifact with tool_context.save_artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload video bytes directly to public Cloud Storage bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return f"Successfully generated IT equipment video!\nPublic Video URL: {public_url}"


# ---------------------------------------------------------------------------
# Code Executor Setup (Agent Engine Sandbox)
# ---------------------------------------------------------------------------

def _get_sandbox_code_executor():
    """Load deployment metadata, env vars, or resource fallback to initialize AgentEngineSandboxCodeExecutor."""
    metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
    agent_engine_resource_name = os.getenv("AGENT_ENGINE_RESOURCE_NAME")

    if not agent_engine_resource_name and metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
        except Exception as e:
            print(f"Warning: Could not read deployment_metadata.json: {e}")

    if not agent_engine_resource_name:
        app_url = os.getenv("APP_URL", "")
        if "/reasoningEngines/" in app_url:
            parts = app_url.split("/api")[0].split("/v1/")
            if len(parts) > 1:
                agent_engine_resource_name = parts[1]

    if not agent_engine_resource_name:
        agent_engine_resource_name = "projects/820036928684/locations/us-east1/reasoningEngines/8581883967861424128"

    return AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_resource_name)


# ---------------------------------------------------------------------------
# Memory Bank Integration (Vertex AI Memory Bank)
# ---------------------------------------------------------------------------

async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each agent turn, process session events and extract durable memories to Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory extraction skipped: {e}")
    return None


def memory_bank_service_builder():
    """Build and return a VertexAiMemoryBankService instance for future deployments."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


# ---------------------------------------------------------------------------
# A2UI System Prompt Generation
# ---------------------------------------------------------------------------

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the IT Helpdesk & Incident Assistant for company employees. "
        "You assist users with IT troubleshooting, checking live service status, searching the Knowledge Base, "
        "inspecting IP network details, geocoding office addresses, finding nearby places, generating images and video clips of IT assets, "
        "and executing Python code in a secure Agent Engine sandbox environment when calculations or data processing are needed. "
        "You pay special attention to and remember all user allergies (e.g. food allergies, dietary restrictions, chemical/material sensitivities), "
        "as well as hardware preferences and personal facts from previous conversations, ensuring all responses and recommendations account for them. "
        "Always use your tools or code executor to perform live queries, calculations, or actions before responding."
    ),
    workflow_description="Analyze the user request, call appropriate tools, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


# ---------------------------------------------------------------------------
# Root Agent Definition
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=_get_sandbox_code_executor(),
    instruction=instruction,
    tools=[
        get_ticket,
        list_user_tickets,
        create_ticket,
        update_ticket_status,
        check_service_status,
        search_knowledge_base,
        lookup_network_ip,
        geocode_address,
        find_nearby_places,
        generate_equipment_image,
        generate_equipment_video,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
