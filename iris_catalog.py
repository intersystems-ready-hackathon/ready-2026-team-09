"""IRIS catalog lookup with graceful fallback.

Tries the IRIS REST /api/atelier endpoint to ask whether a class exists in the
running instance. If IRIS is unreachable, falls back to the curated catalog
shipped in version_history.json so the demo still works offline.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).parent
VERSION_HISTORY_PATH = ROOT / "version_history.json"

IRIS_HOST = os.getenv("IRIS_HOST", "localhost")
IRIS_PORT = int(os.getenv("IRIS_PORT", "52773"))
IRIS_USER = os.getenv("IRIS_USER", "SuperUser")
IRIS_PASSWORD = os.getenv("IRIS_PASSWORD", "SYS")
IRIS_NAMESPACE = os.getenv("IRIS_NAMESPACE", "USER")


def _load_curated() -> dict[str, Any]:
    with VERSION_HISTORY_PATH.open() as f:
        return json.load(f)


def get_iris_version() -> dict[str, Any]:
    """Hit /api/atelier/ to learn the running IRIS version. Returns a status dict."""
    url = f"http://{IRIS_HOST}:{IRIS_PORT}/api/atelier/"
    try:
        r = requests.get(url, auth=HTTPBasicAuth(IRIS_USER, IRIS_PASSWORD), timeout=2)
        if r.status_code == 200:
            data = r.json()
            return {"reachable": True, "version": data.get("result", {}).get("content", {}).get("version", "unknown"), "raw": data}
        return {"reachable": False, "error": f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"reachable": False, "error": str(e)}


def class_exists_in_iris(class_name: str) -> dict[str, Any]:
    """Ask IRIS directly whether `class_name` is defined.

    Uses the Atelier REST endpoint GET /api/atelier/v1/{namespace}/doc/{name}.cls
    which returns 200 if the class exists. Falls back to the curated catalog on
    any connection error.
    """
    cls = class_name.lstrip("%")
    encoded = "%25" + cls if class_name.startswith("%") else cls
    url = f"http://{IRIS_HOST}:{IRIS_PORT}/api/atelier/v1/{IRIS_NAMESPACE}/doc/{encoded}.cls"
    try:
        r = requests.get(url, auth=HTTPBasicAuth(IRIS_USER, IRIS_PASSWORD), timeout=2)
        if r.status_code == 200:
            return {"exists": True, "source": "iris_live", "namespace": IRIS_NAMESPACE}
        if r.status_code == 404:
            return {"exists": False, "source": "iris_live", "namespace": IRIS_NAMESPACE}
        return {"exists": None, "source": "iris_live", "error": f"HTTP {r.status_code}"}
    except requests.RequestException:
        curated = _load_curated()
        if class_name in curated:
            entry = curated[class_name]
            return {
                "exists": bool(entry.get("introduced_in")),
                "source": "curated_fallback",
                "available_in": entry.get("available_in", []),
            }
        return {"exists": None, "source": "curated_fallback", "note": "class not in curated catalog"}


def lookup_version_history(class_name: str) -> dict[str, Any]:
    """Read curated version history for a class."""
    curated = _load_curated()
    if class_name in curated:
        return {"found": True, "class_name": class_name, **curated[class_name]}
    return {
        "found": False,
        "class_name": class_name,
        "note": "not in curated catalog — version history unknown",
        "known_classes": list(curated.keys()),
    }


def normalize_iris_release(release_label: str) -> str:
    """Map informal release labels like 'iris20253' to '2025.3'."""
    s = release_label.strip().lower().replace("iris", "").replace("for", "").replace("health", "").strip()
    s = s.replace(" ", "").replace("-", "").replace("_", "")
    if "." not in s and len(s) >= 5 and s[:4].isdigit():
        return f"{s[:4]}.{s[4:]}"
    return s
