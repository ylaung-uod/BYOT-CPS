#!/usr/bin/env python3
import configparser
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

class APIError(RuntimeError):
    pass

class GNS3API:
    def __init__(self, config_path=None):
        path = Path(config_path or os.environ.get("GNS3_SERVER_CONFIG", "~/.config/GNS3/2.2/gns3_server.conf")).expanduser()
        parser = configparser.ConfigParser()
        if path.exists():
            parser.read(path)
        section = parser["Server"] if parser.has_section("Server") else {}
        host = os.environ.get("GNS3_HOST", section.get("host", "127.0.0.1"))
        if host == "localhost":
            host = "127.0.0.1"
        port = os.environ.get("GNS3_PORT", section.get("port", "3080"))
        self.base = f"http://{host}:{port}/v2"
        self.user = os.environ.get("GNS3_USER", section.get("user", ""))
        self.password = os.environ.get("GNS3_PASSWORD", section.get("password", ""))

    def request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if self.user:
            import base64
            token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req.add_header("Authorization", "Basic " + token)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise APIError(f"{method} {path}: HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise APIError(f"Cannot reach GNS3 at {self.base}: {exc.reason}") from exc

    def get(self, path): return self.request("GET", path)
    def post(self, path, payload=None): return self.request("POST", path, payload)
    def put(self, path, payload=None): return self.request("PUT", path, payload)
    def delete(self, path): return self.request("DELETE", path)
