"""Serve the compiled console on the control plane origin, without exposing source or secrets."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ProductHeaders:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                ]
                if scope["path"].startswith("/v1/product"):
                    headers = [(key, value) for key, value in headers if key != b"cache-control"]
                    headers.append((b"cache-control", b"no-store"))
                else:
                    headers.append(
                        (
                            b"content-security-policy",
                            (
                                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
                                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
                            ).encode(),
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, secured)


def mount_console(app: FastAPI) -> None:
    # Opt-in, fixed operator path; never derive a filesystem path from a request.
    configured = os.environ.get("ZHIYU_WEB_DIST")
    if configured:
        directory = Path(configured).resolve(strict=True)
        if not (directory / "index.html").is_file():
            raise RuntimeError("ZHIYU_WEB_DIST must contain the compiled index.html")
        app.mount("/", StaticFiles(directory=directory, html=True), name="console")
