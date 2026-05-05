from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import os

app = FastAPI(title="Nizami Local AI Web")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
NX_FILE = os.path.join(os.environ["USERPROFILE"], "Desktop", "nx.ps1")


class ChatRequest(BaseModel):
    profile: str
    message: str


def clean_output(stdout: str) -> str:
    cleaned = []
    for line in stdout.splitlines():
        s = line.strip()
        if s.startswith("[nx] loaded."):
            continue
        if "nx a <profile>" in s:
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip() or "(no output)"


def run_powershell(command: str) -> str:
    try:
        result = subprocess.run(
            [
                "pwsh",
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            return f"ERROR:\n{stderr or stdout or 'Unknown error'}"

        return clean_output(stdout)

    except Exception as e:
        return f"ERROR:\n{str(e)}"


@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/chat")
def chat(req: ChatRequest):
    profile = req.profile.strip().lower()
    message = req.message.strip()

    if profile not in ["analyst", "writer", "coder"]:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid profile"}
        )

    if not message:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Message is empty"}
        )

    safe_message = message.replace('"', '`"')
    ps_command = f'. "{NX_FILE}"; nx a {profile} "{safe_message}"'
    output = run_powershell(ps_command)

    return {"ok": True, "output": output}


@app.get("/api/status")
def status():
    ps_command = f'. "{NX_FILE}"; nx status'
    output = run_powershell(ps_command)
    return {"ok": True, "output": output}


@app.get("/api/doctor")
def doctor():
    ps_command = f'. "{NX_FILE}"; nx doctor'
    output = run_powershell(ps_command)
    return {"ok": True, "output": output}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")