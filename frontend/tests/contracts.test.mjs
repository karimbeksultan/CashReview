import assert from "node:assert/strict";
import test from "node:test";
import {
  parseUiJob,
  parseHumanReview,
  InvalidResultError,
  reviewValidationStatus,
  limitReviewNotes,
} from "../src/contracts.ts";

const id = "test-job";
const negative = {
  job_id: id,
  status: "done",
  result: { verdict: "no_violation", violations: [] },
};
const positive = {
  job_id: id,
  status: "done",
  result: {
    verdict: "violation",
    violations: [
      {
        type: "review_signal",
        description: "Visible sequence to inspect",
        timecode_sec: 12.5,
        evidence_frames: [
          { timestamp_sec: 12.5, image_base64: "synthetic-contract-bytes" },
        ],
      },
    ],
    metadata: { duration_sec: 20 },
  },
};
test("valid completed results and processing/failure retain their distinct states", () => {
  assert.equal(parseUiJob(negative, id, "invalid").verdict, "no_violation");
  assert.equal(
    parseUiJob(positive, id, "invalid").violations[0].timecode_sec,
    12.5,
  );
  assert.equal(
    parseUiJob({ job_id: id, status: "processing" }, id, "invalid").status,
    "processing",
  );
  assert.equal(
    parseUiJob(
      { job_id: id, status: "failed", error: { message: "decoder failed" } },
      id,
      "invalid",
    ).status,
    "failed",
  );
});
test("missing or contradictory completed data cannot become a negative result", () => {
  for (const result of [
    { verdict: "no_violation" },
    { violations: [] },
    { verdict: "violation", violations: [] },
    { verdict: "no_violation", violations: positive.result.violations },
  ]) {
    assert.throws(
      () => parseUiJob({ job_id: id, status: "done", result }, id, "invalid"),
      InvalidResultError,
    );
  }
});
test("foreign jobs, missing evidence and out-of-source timestamps fail closed", () => {
  assert.throws(
    () => parseUiJob(negative, "another-job", "invalid"),
    InvalidResultError,
  );
  for (const patch of [
    { evidence_frames: [] },
    { timecode_sec: -1 },
    { timecode_sec: 21 },
    { evidence_frames: [{ timestamp_sec: 21, image_base64: "x" }] },
  ]) {
    assert.throws(
      () =>
        parseUiJob(
          {
            ...positive,
            result: {
              ...positive.result,
              violations: [{ ...positive.result.violations[0], ...patch }],
            },
          },
          id,
          "invalid",
        ),
      InvalidResultError,
    );
  }
});
test("only a complete server review receipt can be displayed as saved", () => {
  const review = {
    decision: "needs_review",
    notes: "Check sequence",
    event_index: null,
    updated_at: 12345,
  };
  assert.deepEqual(parseHumanReview(review, "invalid"), review);
  for (const value of [
    null,
    {},
    { ...review, decision: "done" },
    { ...review, updated_at: NaN },
    { ...review, event_index: -1 },
  ])
    assert.throws(() => parseHumanReview(value, "invalid"), InvalidResultError);
});

test("server review limit counts Unicode codepoints rather than UTF-16 units", () => {
  const review = {
    decision: "needs_review",
    notes: "😀".repeat(4000),
    event_index: null,
    updated_at: 12345,
  };
  assert.equal(review.notes.length, 8000);
  assert.deepEqual(parseHumanReview(review, "invalid"), review);
  assert.equal(
    parseUiJob({ ...negative, human_review: review }, id, "invalid").status,
    "done",
  );
  assert.throws(
    () => parseHumanReview({ ...review, notes: review.notes + "a" }, "invalid"),
    InvalidResultError,
  );
});

test("upload quality notice uses the current service's reported status", () => {
  assert.equal(
    reviewValidationStatus(null, { validation_status: "failed_baseline" }),
    "failed_baseline",
  );
  assert.equal(reviewValidationStatus(null, null), undefined);
  assert.equal(
    reviewValidationStatus(null, { validation_status: "validated" }),
    "validated",
  );
});

test("historical job quality never inherits a replacement service's status", () => {
  for (const serviceStatus of ["validated", "failed_baseline"]) {
    const runtime = { validation_status: serviceStatus };
    for (const status of ["failed_baseline", "validated", "selection_only"]) {
      const historical = {
        ...negative,
        metadata: { validation_status: status },
      };
      assert.equal(reviewValidationStatus(historical, runtime), status);
    }
    assert.equal(reviewValidationStatus(negative, runtime), undefined);
    assert.equal(
      reviewValidationStatus(
        { ...negative, metadata: { validation_status: null } },
        runtime,
      ),
      undefined,
    );
  }
});

test("mixed Unicode editor input and over-limit paste produce a valid server receipt", () => {
  const boundary = "a".repeat(3999) + "😀";
  const pasted = boundary + "extra😀";
  const review = {
    decision: "needs_review",
    notes: limitReviewNotes(pasted),
    event_index: null,
    updated_at: 12345,
  };
  assert.equal(limitReviewNotes(boundary), boundary);
  assert.equal(review.notes, boundary);
  assert.equal(Array.from(review.notes).length, 4000);
  assert.equal(review.notes.length, 4001);
  assert.deepEqual(parseHumanReview(review, "invalid"), review);
  assert.throws(
    () => parseHumanReview({ ...review, notes: pasted }, "invalid"),
    InvalidResultError,
  );
});
