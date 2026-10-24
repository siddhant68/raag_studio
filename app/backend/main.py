"""FastAPI app factory for Raag Studio (PRD v2 section 10). Binds 127.0.0.1:8477 by default.

    cd app && .venv/bin/python -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8477

(scripts/start.sh does exactly that.) Handlers are thin: the work is in jobs.py (Service),
queue_worker.py (renders), exports.py (ffmpeg) and the M1 planner/compiler.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import exports, ui_api
from .db import Database
from .events import EventBus, format_sse
from .jobs import Service
from .queue_worker import QueueWorker
from .schemas import (ApiError, CreateSongBody, ExportBody, FeedbackBody, PlanOnlyBody, PruneBody,
                      RoundBody)
from .settings import VERSION, Config
from .storage import Storage
from .system_info import SystemProbe

PLACEHOLDER_HTML = """<!doctype html><meta charset="utf-8"><title>Raag Studio</title>
<body style="font:16px system-ui;max-width:40rem;margin:3rem auto;padding:0 1rem">
<h1>Raag Studio</h1><p>The backend is running. The web interface is not installed yet
(<code>app/web/</code> is empty). The API is at <a href="/api/system">/api/system</a>.</p></body>"""


def _json_response_class(engine: str):
    class EngineJSONResponse(JSONResponse):
        """Every JSON body carries `engine` (per-object value wins; otherwise the server's engine mode)."""

        def render(self, content: Any) -> bytes:
            if isinstance(content, dict):
                content = {**content}
                content.setdefault("engine", engine)
            return super().render(content)
    return EngineJSONResponse


class LocalOnlyMiddleware:
    """Refuse state-changing requests whose Origin is not this server (blocks drive-by posts from other web pages)."""

    def __init__(self, app, port: int):
        self.app = app
        self.allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ("POST", "PUT", "PATCH", "DELETE"):
            origin = dict(scope["headers"]).get(b"origin", b"").decode()
            if origin and origin not in self.allowed:
                body = json.dumps({"error": {"code": "forbidden_origin",
                                             "message": "Requests from other web pages are not allowed."}}).encode()
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def create_app(config: Optional[Config] = None) -> FastAPI:
    config = config or Config.from_env()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(config.db_path)
    storage = Storage(config.runs_dir, config.tmp_dir)
    probe = SystemProbe(config)
    bus = EventBus()
    svc = Service(config, db, storage, probe, bus)
    worker = QueueWorker(svc)
    svc.worker = worker

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.closing = asyncio.Event()
        app.state.recovery = svc.recover()
        worker.start()
        try:
            yield
        finally:
            app.state.closing.set()
            await asyncio.get_running_loop().run_in_executor(None, worker.stop)

    app = FastAPI(title="Raag Studio", version=VERSION, lifespan=lifespan,
                  default_response_class=_json_response_class(config.engine), docs_url="/api/docs",
                  openapi_url="/api/openapi.json")
    app.state.config, app.state.svc, app.state.worker, app.state.bus = config, svc, worker, bus
    app.state.closing = None
    JSON = _json_response_class(config.engine)

    hosts = ["127.0.0.1", "localhost", "[::1]"] + (["testserver"] if config.is_fake else [])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    app.add_middleware(LocalOnlyMiddleware, port=config.port)

    # ------------------------------------------------------------------ errors
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSON({"error": {"code": exc.code, "message": exc.message, **exc.extra}}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = [{"loc": [str(p) for p in e["loc"] if p != "body"], "msg": e["msg"]} for e in exc.errors()]
        first = fields[0] if fields else {"loc": [], "msg": "invalid request"}
        where = ".".join(first["loc"])
        return JSON({"error": {"code": "invalid_request", "message": f"{where}: {first['msg']}" if where else first["msg"],
                               "fields": fields}}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSON({"error": {"code": code, "message": str(exc.detail)}}, status_code=exc.status_code)

    # ------------------------------------------------------------------ songs
    # Planning may call a smart provider (up to 60 s); run it in a worker thread so the event loop (SSE) never blocks.
    @app.post("/api/songs", status_code=202)
    async def create_song(body: CreateSongBody, idempotency_key: Optional[str] = Header(default=None)):
        return await asyncio.to_thread(svc.create_song, body, idempotency_key)

    @app.get("/api/songs")
    def list_songs():
        return {"songs": svc.list_songs()}

    @app.get("/api/songs/{song_id}")
    def get_song(song_id: str):
        return svc.song_detail(song_id)

    @app.post("/api/songs/{song_id}/plan")
    async def plan_only(song_id: str, body: Optional[PlanOnlyBody] = None):
        return await asyncio.to_thread(svc.plan_only, song_id, body or PlanOnlyBody())

    @app.post("/api/songs/{song_id}/rounds", status_code=202)
    async def create_round(song_id: str, body: RoundBody, idempotency_key: Optional[str] = Header(default=None)):
        return await asyncio.to_thread(svc.create_round, song_id, body, idempotency_key)

    @app.patch("/api/songs/{song_id}/controls")
    def patch_controls(song_id: str, body: dict[str, Any]):
        return svc.patch_controls(song_id, body)

    # ------------------------------------------------------------------ jobs and events
    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return svc.job_view(job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        return svc.cancel_job(job_id)

    @app.get("/api/events")
    async def events(request: Request):
        last = request.headers.get("last-event-id", "")
        sub, backlog = bus.subscribe(asyncio.get_running_loop(), int(last) if last.isdigit() else None)
        hello = {"event": "hello", "data": {"engine": config.engine, "version": VERSION, "queue": svc.queue_info()}}

        async def stream():
            try:
                yield ": connected\n\n"
                yield f"event: hello\ndata: {json.dumps(hello['data'])}\n\n"
                for item in backlog:
                    yield format_sse(item)
                idle = 0
                while not (request.app.state.closing and request.app.state.closing.is_set()):
                    if await request.is_disconnected():
                        break
                    try:
                        item = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        idle += 1
                        if idle % 15 == 0:
                            yield ": keep-alive\n\n"
                        continue
                    idle = 0
                    yield format_sse(item)
            finally:
                bus.unsubscribe(sub)
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ------------------------------------------------------------------ takes
    @app.get("/api/takes/{take_id}")
    def get_take(take_id: str):
        return svc.take_view(svc.get_take(take_id))

    @app.get("/api/takes/{take_id}/audio")
    def take_audio(take_id: str, kind: str = "preview"):
        take = svc.get_take(take_id)
        if kind not in ("preview", "native"):
            raise ApiError(422, "invalid_kind", "kind must be 'preview' or 'native'")
        native = storage.abs(take["native_path"])
        path = storage.abs(take["preview_path"]) if kind == "preview" else native
        if kind == "preview" and not (path and path.is_file()):
            path = native                                      # no preview: fall back to the native file
        if not path or not path.is_file():
            raise ApiError(410 if take["native_pruned_at"] else 404, "audio_missing",
                           "The native audio was pruned." if take["native_pruned_at"] else "Audio file not found.")
        media_type = {".mp3": "audio/mpeg", ".flac": "audio/flac", ".wav": "audio/wav"}.get(path.suffix, "audio/mpeg")
        return FileResponse(path, media_type=media_type,
                            headers={"X-Raag-Engine": take["engine"], "Cache-Control": "private, max-age=3600"})

    @app.post("/api/takes/{take_id}/feedback")
    def feedback(take_id: str, body: FeedbackBody):
        return svc.add_feedback(take_id, body.favourite, body.rating, body.tags, body.note)

    @app.post("/api/takes/{take_id}/exports", status_code=201)
    def export_take(take_id: str, body: ExportBody):
        return exports.create_export(svc, take_id, body)

    @app.get("/api/exports/{export_id}/file")
    def export_file(export_id: str):
        path, media_type, filename = exports.export_file(svc, export_id)
        return FileResponse(path, media_type=media_type, filename=filename)

    # ------------------------------------------------------------------ system, settings, admin
    @app.get("/api/system")
    def system():
        return probe.snapshot(svc.settings(), svc.queue_info(), svc.effective_planner())

    @app.get("/api/settings")
    def get_settings():
        return {"settings": svc.settings(), "planner": ui_api.planner_view(svc)}

    @app.put("/api/settings")
    def put_settings(body: dict[str, Any]):
        settings = svc.update_settings(body)
        return {"settings": settings, "planner": ui_api.planner_view(svc)}

    @app.put("/api/settings/engine")
    def put_engine_settings(body: dict[str, Any]):
        """The only settings the web page may write: which local pipeline and model renders. Planner settings are
        refused here (switching a smart planner on sends your brief to Anthropic; that stays a deliberate call)."""
        allowed = {"engine_profile", "song_pipeline"}
        extra = sorted(set(body) - allowed)
        if extra:
            raise ApiError(422, "invalid_settings", f"only {sorted(allowed)} can be changed here, not {extra}")
        settings = svc.update_settings(body)
        return {"settings": settings, "planner": ui_api.planner_view(svc)}

    # ------------------------------------------------------------------ read-only data for the web UI (M3)
    @app.get("/api/recipes")
    def recipes():
        return ui_api.recipes_view()

    @app.get("/api/capabilities")
    def capabilities_endpoint():
        return ui_api.capabilities_view()

    @app.get("/api/instruments")
    def instruments():
        return ui_api.instruments_view()

    @app.get("/api/genres")
    def genres_list() -> dict:
        return ui_api.genres_view()

    @app.get("/api/ledger")
    def ledger():
        return ui_api.ledger_view(svc)

    @app.get("/api/storage")
    def storage_info():
        return ui_api.storage_view(svc)

    @app.post("/api/admin/prune")
    def prune(body: PruneBody):
        if not body.confirm:
            raise ApiError(400, "confirm_required", "Pruning removes native audio files. Send confirm:true to proceed.")
        return svc.prune(body.older_than_days)

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def unknown_api(rest: str):
        raise ApiError(404, "not_found", f"No such endpoint: /api/{rest}")

    # ------------------------------------------------------------------ web UI (filled by a later milestone)
    if config.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=config.web_dir, html=True), name="web")
    else:
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def placeholder():
            return PLACEHOLDER_HTML

    return app
