"""Bounded local workers; results publish only under the current claim token."""

import base64
from concurrent.futures import Future, ThreadPoolExecutor
import importlib
import logging
import math
import multiprocessing
from pathlib import Path
import threading
import time
from typing import Any

from .config import Settings
from .store import JobStore

logger = logging.getLogger(__name__)


def get_engine() -> Any:
    return importlib.import_module("cash_review.engine")


def model_readiness() -> dict[str, Any]:
    try:
        result = get_engine().readiness()
        if not isinstance(result, dict) or not isinstance(result.get("ready"), bool):
            return {"ready": False, "reasons": ["Invalid model readiness response."]}
        return result
    except Exception:
        return {"ready": False, "reasons": ["Local detector dependencies or artifacts are unavailable."]}


def jpeg_dimensions(raw: bytes) -> tuple[int, int]:
    """Read JPEG frame dimensions without invoking a native image decoder."""
    offset = 2
    frame_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset < len(raw):
        if raw[offset] != 0xFF:
            raise ValueError("Invalid JPEG header")
        while offset < len(raw) and raw[offset] == 0xFF:
            offset += 1
        if offset >= len(raw):
            break
        marker = raw[offset]
        offset += 1
        if marker in {0xD8, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if marker in {0xD9, 0xDA} or offset + 2 > len(raw):
            break
        length = int.from_bytes(raw[offset:offset + 2], "big")
        if length < 2 or offset + length > len(raw):
            raise ValueError("Invalid JPEG segment")
        if marker in frame_markers:
            if length < 8:
                raise ValueError("Invalid JPEG frame")
            height = int.from_bytes(raw[offset + 3:offset + 5], "big")
            width = int.from_bytes(raw[offset + 5:offset + 7], "big")
            if width < 1 or height < 1 or max(width, height) > 4096 or width * height > 8_000_000:
                raise ValueError("Evidence dimensions exceed the safety limit")
            return width, height
        offset += length
    raise ValueError("JPEG dimensions are unavailable")


def validate_result(result: Any, decode_images: bool = True) -> dict[str, Any]:
    """Reject incomplete evidence instead of publishing a misleading verdict."""
    if not isinstance(result, dict) or result.get("verdict") not in {"no_violation", "violation"}:
        raise ValueError("Invalid analysis verdict")
    violations = result.get("violations")
    if not isinstance(violations, list) or len(violations) > 100:
        raise ValueError("Invalid violations")
    if (result["verdict"] == "violation") != bool(violations):
        raise ValueError("Verdict does not match evidence")
    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("Invalid metadata")
    duration = metadata.get("duration_sec")
    if duration is not None and (type(duration) not in {float, int} or not math.isfinite(duration) or duration <= 0):
        raise ValueError("Invalid video duration")
    normalized = []
    encoded_bytes = 0
    for event in violations:
        if not isinstance(event, dict):
            raise ValueError("Invalid event")
        timestamp = event.get("timecode_sec")
        if type(timestamp) not in {float, int} or not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("Invalid event timestamp")
        if duration is not None and timestamp > duration + 0.25:
            raise ValueError("Event outside video")
        for key in ("type", "description", "rule_id"):
            if not isinstance(event.get(key), str) or not event[key].strip():
                raise ValueError("Missing event grounding")
        frames = event.get("evidence_frames")
        if frames is None and isinstance(event.get("frames"), list):
            frames = [{"timestamp_sec": timestamp, "image_base64": value} for value in event["frames"]]
        if not isinstance(frames, list) or not 1 <= len(frames) <= 3:
            raise ValueError("Every event needs one to three evidence frames")
        for frame in frames:
            if not isinstance(frame, dict) or not isinstance(frame.get("image_base64"), str):
                raise ValueError("Invalid evidence frame")
            if len(frame["image_base64"]) > 4 * 1024 * 1024:
                raise ValueError("Evidence frame too large")
            encoded_bytes += len(frame["image_base64"])
            if encoded_bytes > 16 * 1024 * 1024:
                raise ValueError("Evidence result too large")
            stamp = frame.get("timestamp_sec")
            if type(stamp) not in {float, int} or not math.isfinite(stamp) or stamp < 0:
                raise ValueError("Invalid frame timestamp")
            if duration is not None and stamp > duration + 0.25:
                raise ValueError("Frame outside video")
            raw = base64.b64decode(frame["image_base64"], validate=True)
            if not raw.startswith(b"\xff\xd8") or not raw.endswith(b"\xff\xd9"):
                raise ValueError("Evidence must be JPEG")
            jpeg_dimensions(raw)
            if decode_images:
                import cv2
                import numpy as np
                decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_REDUCED_COLOR_2)
                if decoded is None or decoded.size == 0:
                    raise ValueError("Evidence JPEG could not be decoded safely")
        confidence = event.get("confidence")
        if confidence is not None and (type(confidence) not in {float, int} or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            raise ValueError("Invalid event confidence")
        normalized.append({**{k: v for k, v in event.items() if k != "frames"}, "evidence_frames": frames})
    return {"verdict": result["verdict"], "violations": normalized, "metadata": metadata}


def _analysis_process(connection: Any, source: str, deadline: float) -> None:
    """Spawn target: native decoding/model work never runs in the API process."""
    try:
        result = get_engine().analyze_video(Path(source), deadline,
                    lambda percent, stage: connection.send(("progress", int(percent), str(stage)[:120])))
        # Native JPEG validation shares the detector's killable process/deadline.
        connection.send(("result", validate_result(result)))
    except TimeoutError:
        connection.send(("error", "deadline_exceeded"))
    except ValueError:
        connection.send(("error", "invalid_video"))
    except Exception:
        connection.send(("error", "analysis_failed"))
    finally:
        connection.close()


def run_analysis(source: Path, deadline: float, progress: Any,
                 stop_event: threading.Event | None = None, child_target: Any = None) -> dict[str, Any]:
    """Hard-stop a blocked decoder at the admission deadline, then free the slot."""
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=child_target or _analysis_process,
                              args=(child, str(source), deadline), name="cash-review-detector", daemon=True)
    try:
        process.start()
        child.close()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or (stop_event is not None and stop_event.is_set()):
                raise TimeoutError("analysis_deadline_exceeded")
            if parent.poll(min(0.1, remaining)):
                try:
                    message = parent.recv()
                except EOFError:
                    raise RuntimeError("analysis_process_ended") from None
                if message[0] == "progress":
                    progress(message[1], message[2])
                elif message[0] == "result":
                    return message[1]
                elif message[0] == "error":
                    if message[1] == "deadline_exceeded":
                        raise TimeoutError()
                    if message[1] == "invalid_video":
                        raise ValueError("invalid_video")
                    raise RuntimeError("analysis_failed")
            elif not process.is_alive():
                raise RuntimeError("analysis_process_ended")
    finally:
        parent.close()
        child.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()


class Worker:
    def __init__(self, store: JobStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=settings.worker_concurrency, thread_name_prefix="cash-review")
        self.active: dict[str, tuple[str, Future[Any]]] = {}
        self.thread = threading.Thread(target=self._loop, name="cash-review-scheduler", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _loop(self) -> None:
        last_cleanup = 0.0
        while not self.stop_event.is_set():
            try:
                self.store.expire_deadlines()
                for job_id, (token, future) in list(self.active.items()):
                    if future.done():
                        del self.active[job_id]
                    else:
                        self.store.heartbeat(job_id, token, self.settings.lease_seconds)
                while len(self.active) < self.settings.worker_concurrency:
                    job = self.store.claim(self.settings.lease_seconds)
                    if job is None:
                        break
                    future = self.executor.submit(self._run, job)
                    self.active[job["id"]] = (job["claim_token"], future)
                if time.monotonic() - last_cleanup > 60:
                    self.store.cleanup()
                    last_cleanup = time.monotonic()
            except Exception:
                # No input, file path or exception detail is logged.
                logger.error("Worker queue maintenance failed.")
            self.stop_event.wait(0.25)

    def _run(self, job: dict[str, Any]) -> None:
        job_id, token = job["id"], job["claim_token"]
        try:
            remaining = job["deadline_at"] - time.time()
            if remaining <= 0:
                self.store.expire_deadlines()
                return
            result = run_analysis(
                self.store.media_path(job["media_name"]),
                time.monotonic() + remaining,
                lambda percent, stage: self.store.progress(job_id, token, percent, stage),
                self.stop_event,
            )
            self.store.finish(job_id, token, validate_result(result, decode_images=False))
            self.store.expire_deadlines()
        except TimeoutError:
            self.store.fail(job_id, token, "deadline_exceeded", "Analysis exceeded the five-minute deadline.")
        except ValueError:
            self.store.fail(job_id, token, "invalid_video", "The video could not be decoded or its analysis evidence was invalid.")
        except Exception:
            self.store.fail(job_id, token, "analysis_failed", "Local analysis could not complete. Please retry with a valid MOV video.")
        finally:
            self.store.expire_deadlines()
