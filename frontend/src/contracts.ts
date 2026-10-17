import type { Finding, Health, HumanReview, Job } from "./types";

export class InvalidResultError extends Error {}
const record = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === "object" && !Array.isArray(value);
const timestamp = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0;

export function reviewValidationStatus(
  job: Job | null,
  runtime: Health | null | undefined,
): string | undefined {
  // A saved result belongs to its recorded model, even if the service changed.
  const status = job
    ? job.metadata?.validation_status
    : runtime?.validation_status;
  return typeof status === "string" ? status : undefined;
}

export function limitReviewNotes(value: string): string {
  return Array.from(value).slice(0, 4000).join("");
}

export function parseUiJob(
  value: unknown,
  expectedId: string,
  message: string,
): Job {
  if (!record(value)) throw new InvalidResultError(message);
  const merged = { ...value, ...(record(value.result) ? value.result : {}) };
  if (
    merged.job_id !== expectedId ||
    !["processing", "done", "failed"].includes(String(merged.status))
  )
    throw new InvalidResultError(message);
  if (merged.status === "done") {
    if (
      !["violation", "no_violation"].includes(String(merged.verdict)) ||
      !Array.isArray(merged.violations)
    )
      throw new InvalidResultError(message);
    if ((merged.verdict === "violation") !== Boolean(merged.violations.length))
      throw new InvalidResultError(message);
    const duration = record(merged.metadata)
      ? merged.metadata.duration_sec
      : undefined;
    for (const rawEvent of merged.violations) {
      if (
        !record(rawEvent) ||
        typeof rawEvent.type !== "string" ||
        !rawEvent.type.trim() ||
        typeof rawEvent.description !== "string" ||
        !rawEvent.description.trim() ||
        !timestamp(rawEvent.timecode_sec)
      )
        throw new InvalidResultError(message);
      const event = rawEvent as unknown as Finding;
      if (
        !Array.isArray(event.evidence_frames) ||
        event.evidence_frames.length < 1 ||
        event.evidence_frames.length > 3
      )
        throw new InvalidResultError(message);
      if (timestamp(duration) && event.timecode_sec > duration + 0.25)
        throw new InvalidResultError(message);
      for (const frame of event.evidence_frames) {
        if (
          !record(frame) ||
          !timestamp(frame.timestamp_sec) ||
          typeof frame.image_base64 !== "string" ||
          !frame.image_base64.trim()
        )
          throw new InvalidResultError(message);
        if (timestamp(duration) && frame.timestamp_sec > duration + 0.25)
          throw new InvalidResultError(message);
      }
    }
  }
  if (merged.human_review != null)
    merged.human_review = parseHumanReview(merged.human_review, message);
  return merged as Job;
}

export function parseHumanReview(value: unknown, message: string): HumanReview {
  if (
    !record(value) ||
    !["violation", "no_violation", "needs_review"].includes(
      String(value.decision),
    ) ||
    typeof value.notes !== "string" ||
    Array.from(value.notes).length > 4000 ||
    !timestamp(value.updated_at) ||
    !(
      value.event_index === null ||
      (typeof value.event_index === "number" &&
        Number.isInteger(value.event_index) &&
        value.event_index >= 0)
    )
  )
    throw new InvalidResultError(message);
  return value as HumanReview;
}
