"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import base64
import json
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP passthrough.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request.
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _parse_a2ui_datapart(raw_val) -> dict | None:
    """Helper to parse A2UI data out of a text or byte payload."""
    if raw_val is None:
        return None
    if isinstance(raw_val, bytes):
        try:
            raw_val = raw_val.decode("utf-8")
        except Exception:
            try:
                raw_val = base64.b64decode(raw_val).decode("utf-8")
            except Exception:
                return None
    if not isinstance(raw_val, str):
        return None

    if "<a2a_datapart_json>" in raw_val:
        match = re.search(
            r"<a2a_datapart_json>(.*?)(?:</a2a_datapart_json>|<a2a_datapart_json>|$)",
            raw_val,
            re.DOTALL,
        )
        if match:
            json_str = match.group(1).strip()
            try:
                data_obj = json.loads(json_str)
                meta = data_obj.get("metadata") or {}
                if isinstance(meta, dict) and meta.get("mimeType") == _A2UI_MIME:
                    return data_obj.get("data")
                elif "beginRendering" in data_obj or "surfaceUpdate" in data_obj:
                    return data_obj
            except Exception:
                pass
    elif raw_val.strip().startswith("{"):
        try:
            data_obj = json.loads(raw_val.strip())
            meta = data_obj.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("mimeType") == _A2UI_MIME:
                return data_obj.get("data")
            elif "beginRendering" in data_obj or "surfaceUpdate" in data_obj:
                return data_obj
        except Exception:
            pass
    return None


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI."""
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            a2ui_data = _parse_a2ui_datapart(root.text)
            if a2ui_data:
                out.append({"kind": "a2ui", "data": a2ui_data})
            else:
                out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
            else:
                a2ui_data = _parse_a2ui_datapart(root.data)
                if a2ui_data:
                    out.append({"kind": "a2ui", "data": a2ui_data})
                else:
                    out.append({"kind": "text", "text": str(root.data)})
        elif isinstance(root, FilePart):
            file_obj = getattr(root, "file", None)
            file_bytes = getattr(file_obj, "bytes", None) or getattr(file_obj, "data", None)
            if file_bytes:
                a2ui_data = _parse_a2ui_datapart(file_bytes)
                if a2ui_data:
                    out.append({"kind": "a2ui", "data": a2ui_data})
                else:
                    uri = getattr(file_obj, "uri", None)
                    if uri:
                        out.append({"kind": "text", "text": uri})
            else:
                uri = getattr(file_obj, "uri", None)
                if uri:
                    out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Fallback: pull parts from final task's artifacts OR history agent messages
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

            if not parts:
                for msg_item in getattr(last_task, "history", []) or []:
                    role_str = str(getattr(msg_item, "role", ""))
                    if "agent" in role_str.lower():
                        parts.extend(_extract_parts(getattr(msg_item, "parts", []) or []))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


@app.post("/reset_session")
async def reset_session(req: Request):
    body = await req.json() if req.headers.get("content-type") == "application/json" else {}
    user_id = body.get("user_id") or "web-user"
    _contexts.pop(user_id, None)
    return JSONResponse({"status": "reset"})


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
