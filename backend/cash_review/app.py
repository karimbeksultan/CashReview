"""FastAPI boundary for the same local detector used by jury and browser jobs."""

from collections import defaultdict, deque
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import Settings
from .references import sponsor_reference
from .store import JobStore, QueueFull
from .worker import Worker, model_readiness


class BodyTooLarge(Exception):
    pass


class UploadTimedOut(Exception):
    pass


class RateLimiter:
    """Bounded, per-process abuse guard. The ingress must apply global limits."""
    def __init__(self) -> None:
        self.events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allowed(self, identity: str, category: str, maximum: int) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.events) > 10000:
                for key in list(self.events):
                    if not self.events[key] or self.events[key][-1] < now - 60:
                        del self.events[key]
            key = (identity, category)
            if key not in self.events and len(self.events) >= 10000:
                return False
            events = self.events[key]
            while events and events[0] <= now - 60:
                events.popleft()
            if len(events) >= maximum:
                return False
            events.append(now)
            return True


def key_is_valid(settings: Settings, supplied: str) -> bool:
    return bool(settings.api_key and supplied and secrets.compare_digest(settings.api_key.encode("utf-8"), supplied.encode("utf-8")))


class BoundaryMiddleware:
    """Enforce limits before multipart parsing can spool unauthenticated bodies."""
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app, self.settings = app, settings
        self.limiter = RateLimiter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        path = scope.get("path", "")
        method = scope.get("method", "")
        is_upload = method == "POST" and path in {"/api/v1/analyze", "/api/ui/analyze"}
        if is_upload:
            scope.setdefault("state", {}).update({"admitted_at": time.time(),
                                                  "upload_deadline": time.monotonic() + self.settings.deadline_seconds})
        if path.startswith("/api/v1/") and method != "OPTIONS" and not key_is_valid(self.settings, headers.get("x-api-key", "")):
            await JSONResponse({"detail": "A valid X-API-Key is required."}, 401)(scope, receive, send)
            return
        if path.startswith("/api/ui/") and method not in {"OPTIONS", "GET", "HEAD"}:
            origin = headers.get("origin", "").rstrip("/")
            scheme = scope.get("scheme", "http")
            same_origin = f"{scheme}://{headers.get('host', '')}"
            if origin and origin not in self.settings.origins and origin != same_origin:
                await JSONResponse({"detail": "This browser origin is not allowed."}, 403)(scope, receive, send)
                return
        if path.startswith("/api/") and method != "OPTIONS":
            peer = str((scope.get("client") or ("unknown",))[0])
            category = "upload" if is_upload else "poll"
            maximum = self.settings.upload_rate_limit if is_upload else self.settings.poll_rate_limit
            if not self.limiter.allowed(peer, category, maximum):
                await JSONResponse({"detail": "Too many requests. Retry shortly."}, 429, headers={"Retry-After": "60"})(scope, receive, send)
                return
        # Allow small multipart headers beyond the actual video limit.
        maximum_body = self.settings.max_upload_bytes + 1024 * 1024
        if is_upload:
            try:
                content_length = int(headers.get("content-length", "0"))
            except ValueError:
                content_length = maximum_body + 1
            if content_length < 0 or content_length > maximum_body:
                await JSONResponse({"detail": "Upload exceeds the configured size limit."}, 413)(scope, receive, send)
                return
        received = 0
        started = False

        async def limited_receive() -> Message:
            nonlocal received
            if is_upload:
                remaining = scope["state"]["upload_deadline"] - time.monotonic()
                if remaining <= 0:
                    raise UploadTimedOut()
                try:
                    message = await asyncio.wait_for(receive(), timeout=remaining)
                except TimeoutError:
                    raise UploadTimedOut() from None
            else:
                message = await receive()
            if is_upload and message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > maximum_body:
                    raise BodyTooLarge()
            return message

        async def secured_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message.setdefault("headers", []).extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                ])
                if path.startswith("/api/"):
                    message["headers"] = [(name, value) for name, value in message["headers"] if name.lower() != b"cache-control"]
                    message["headers"].append((b"cache-control", b"no-store"))
            await send(message)
        try:
            await self.app(scope, limited_receive, secured_send)
        except BodyTooLarge:
            if not started:
                await JSONResponse({"detail": "Upload exceeds the configured size limit."}, 413)(scope, receive, send)
        except UploadTimedOut:
            if not started:
                await JSONResponse({"detail": "Upload exceeded the analysis deadline."}, 408)(scope, receive, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store = JobStore(config.data_dir, config.queue_capacity)
        store.expire_deadlines()
        store.cleanup()
        worker = Worker(store, config)
        application.state.store = store
        application.state.worker = worker
        if config.start_worker:
            worker.start()
        try:
            yield
        finally:
            if config.start_worker:
                worker.stop()

    application = FastAPI(title="Cash Review API", version="0.1.0", lifespan=lifespan,
                          description="Local visual review assistant. A signal requires human confirmation.")
    application.state.settings = config
    application.add_middleware(CORSMiddleware, allow_origins=list(config.origins),
                               allow_credentials=False, allow_methods=["GET", "POST"],
                               allow_headers=["Authorization", "Content-Type", "X-API-Key"])
    application.add_middleware(BoundaryMiddleware, settings=config)

    def jury_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if not key_is_valid(config, x_api_key or ""):
            raise HTTPException(401, "A valid X-API-Key is required.")

    def readiness() -> dict[str, Any]:
        model = model_readiness()
        reasons = list(model.get("reasons", []))
        if not config.api_key:
            reasons.append("Server CASH_REVIEW_API_KEY is not configured.")
        try:
            registry = json.loads(config.rules_path.read_text(encoding="utf-8-sig"))
            if not isinstance(registry, dict) or not isinstance(registry.get("rules"), list) or not registry["rules"]:
                raise ValueError("Invalid rules")
        except (OSError, ValueError):
            reasons.append("The rule registry is unavailable.")
        return {**model, "ready": bool(model.get("ready") and not reasons), "reasons": reasons,
                "local_only": True, "deadline_seconds": config.deadline_seconds}

    def fetch_job(request: Request, job_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise HTTPException(404, "Job not found or expired.")
        store: JobStore = request.app.state.store
        store.expire_deadlines()
        job = store.get(job_id)
        if not job or job["expires_at"] <= time.time():
            raise HTTPException(404, "Job not found or expired.")
        return job

    def ui_job(request: Request, job_id: str,
               authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
        # Treat unknown jobs and wrong tokens identically.
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "A job access token is required.")
        job = fetch_job(request, job_id)
        if not request.app.state.store.authorize(job, authorization[7:]):
            raise HTTPException(404, "Job not found or expired.")
        return job

    def snapshot(job: dict[str, Any], ui: bool = False) -> dict[str, Any]:
        response: dict[str, Any] = {"job_id": job["id"], "status": job["status"],
                                    "progress": job["progress"], "stage": job["stage"],
                                    "created_at": job["created_at"], "deadline_at": job["deadline_at"],
                                    "expires_at": job["expires_at"]}
        if job["status"] == "done":
            result = json.loads(job["result_json"])
            if ui:
                response["result"] = result
                response["sponsor_reference"] = sponsor_reference(config.reference_labels_path, job["sha256"])
            else:
                response.update(result)
        if job["status"] == "failed":
            response["error"] = {"code": job["error_code"], "message": job["error_message"]}
        return response

    async def accept_upload(request: Request, upload: UploadFile, browser: bool) -> dict[str, Any]:
        if not readiness()["ready"]:
            await upload.close()
            raise HTTPException(503, {"code": "not_ready", "message": "The local detector is not ready. Check /api/health/ready."})
        filename = upload.filename or ""
        if Path(filename).suffix.lower() != ".mov":
            await upload.close()
            raise HTTPException(415, "Choose a MOV video (.mov).")
        store: JobStore = request.app.state.store
        job_id = uuid4().hex
        media_name = f"{job_id}.mov"
        final_path = store.media_path(media_name)
        partial_path = store.media_path(f"{job_id}.part")
        size = 0
        digest = hashlib.sha256()
        header = b""
        try:
            with partial_path.open("xb") as target:
                while chunk := await upload.read(1024 * 1024):
                    if time.monotonic() >= request.state.upload_deadline:
                        raise HTTPException(408, "Upload exceeded the analysis deadline.")
                    size += len(chunk)
                    if size > config.max_upload_bytes:
                        raise HTTPException(413, "Video exceeds the configured size limit.")
                    if len(header) < 16:
                        header += chunk[:16 - len(header)]
                    digest.update(chunk)
                    target.write(chunk)
            if size < 12 or header[4:8] not in {b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip"}:
                raise HTTPException(415, "The upload is not a recognizable MOV container.")
            partial_path.replace(final_path)
            token = secrets.token_urlsafe(32) if browser else None
            try:
                job = store.create(job_id, media_name, size, digest.hexdigest(), config.deadline_seconds,
                                   config.retention_seconds, token, config.token_ttl_seconds,
                                   admitted_at=request.state.admitted_at)
            except QueueFull:
                raise HTTPException(429, "The local analysis queue is full. Retry after a job completes.", headers={"Retry-After": "30"})
            except TimeoutError:
                raise HTTPException(408, "Upload exceeded the analysis deadline.")
            response: dict[str, Any] = {"job_id": job_id}
            if browser:
                response.update({"access_token": token, "token_type": "Bearer",
                                 "token_expires_at": job["token_expires_at"], "status": "processing"})
            return response
        except BaseException:
            partial_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    @application.get("/api/health/live", tags=["health"])
    def health_live() -> dict[str, Any]:
        return {"status": "ok", "service": "cash-review"}

    @application.get("/api/health/ready", tags=["health"])
    def health_ready() -> JSONResponse:
        result = readiness()
        return JSONResponse(result, status_code=200 if result["ready"] else 503)

    @application.get("/api/rules", tags=["review"])
    def rules() -> Any:
        try:
            return json.loads(config.rules_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raise HTTPException(503, "The rule registry is unavailable.")

    @application.post("/api/v1/analyze", status_code=202, dependencies=[Depends(jury_key)], tags=["jury"])
    async def jury_analyze(request: Request, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
        return await accept_upload(request, file, False)

    @application.get("/api/v1/jobs/{job_id}", dependencies=[Depends(jury_key)], tags=["jury"])
    def jury_status(request: Request, job_id: str) -> dict[str, Any]:
        job = fetch_job(request, job_id)
        if job["token_hash"] is not None:
            raise HTTPException(404, "Job not found or expired.")
        return snapshot(job)

    @application.post("/api/ui/analyze", status_code=202, tags=["review"])
    async def browser_analyze(request: Request, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
        return await accept_upload(request, file, True)

    @application.get("/api/ui/jobs/{job_id}", tags=["review"])
    def browser_status(job: Annotated[dict[str, Any], Depends(ui_job)]) -> dict[str, Any]:
        return snapshot(job, True)

    @application.get("/api/ui/jobs/{job_id}/media", tags=["review"])
    def browser_media(request: Request, job: Annotated[dict[str, Any], Depends(ui_job)]) -> FileResponse:
        path = request.app.state.store.media_path(job["media_name"])
        if not path.is_file():
            raise HTTPException(404, "Media not found or expired.")
        return FileResponse(path, media_type="video/quicktime", headers={"Cache-Control": "no-store"})

    @application.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> Any:
        if path.startswith("api/"):
            raise HTTPException(404, "API route not found.")
        root = config.frontend_dir.resolve()
        candidate = (root / path).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"service": "Cash Review", "frontend": "Build frontend/dist to serve the review workspace.",
                             "api_docs": "/docs"})

    return application


app = create_app()
