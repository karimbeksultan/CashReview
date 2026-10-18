import assert from "node:assert/strict";
import test from "node:test";
import { buildReviewReport } from "../src/report.ts";

const generatedAt = new Date("2026-10-18T06:32:00.000Z");
const finding = {
  type: "visual_review_signal",
  description: "PRIVATE_MODEL_DESCRIPTION",
  timecode_sec: 33.5,
  confidence: 0.875,
  evidence_frames: [
    { timestamp_sec: 33.5, image_base64: "PRIVATE_IMAGE_BYTES" },
  ],
};
const saved = {
  decision: "needs_review",
  notes: "Saved note\nПроверить последовательность 😀",
  event_index: 0,
  updated_at: 1_760_768_000,
};
const job = {
  job_id: "PRIVATE_JOB_IDENTIFIER",
  status: "done",
  verdict: "violation",
  violations: [finding],
  metadata: { model_kind: "local_cpu_v1", model_version: "v1.0" },
  human_review: saved,
};
const options = {
  lang: "en",
  job,
  fileName: "synthetic.mp4",
  demo: false,
  generatedAt,
};

test("unqualified positive and negative results export the same neutral assessment as the UI", () => {
  for (const verdict of ["violation", "no_violation"])
    for (const metadata of [
      {},
      { quality_validated: true, validation_status: "failed_baseline" },
      { quality_validated: "true", validation_status: "validated" },
      { quality_validated: false, validation_status: "validated" },
      { validation_status: "validated" },
    ]) {
      const report = buildReviewReport({
        ...options,
        job: { ...job, verdict, metadata },
      });
      assert.match(
        report,
        /Automatic assessment: Unavailable — human review required/,
      );
      assert.doesNotMatch(
        report,
        /Automatic assessment: (?:Concern signal|No concern signal)/,
      );
    }
});

test("qualified conclusions require the existing job guard and preserve its positive/negative meanings", () => {
  for (const [verdict, label] of [
    ["violation", "Concern signal"],
    ["no_violation", "No concern signal"],
  ]) {
    const report = buildReviewReport({
      ...options,
      job: {
        ...job,
        verdict,
        metadata: { quality_validated: true, validation_status: "validated" },
      },
    });
    assert.ok(report.includes(`Automatic assessment: ${label}\n`));
  }
});

test("only a saved server assessment is included; unsaved editor or demo state cannot replace it", () => {
  const report = buildReviewReport({
    ...options,
    demoReview: { ...saved, notes: "UNSAVED_DEMO_NOTE" },
    reviewDraft: { notes: "UNSAVED_EDITOR_NOTE", saved: false },
  });
  assert.match(report, /Saved server receipt/);
  assert.ok(report.includes(saved.notes));
  assert.match(report, /Scope: Candidate 1, 00:33.500/);
  assert.match(report, /Unsaved editor changes are excluded/);
  assert.doesNotMatch(report, /UNSAVED_/);
  assert.match(
    buildReviewReport({
      ...options,
      job: { ...job, human_review: null },
      reviewDraft: { notes: "UNSAVED_EDITOR_NOTE" },
    }),
    /No saved human assessment/,
  );
  assert.throws(() =>
    buildReviewReport({
      ...options,
      job: {
        ...job,
        human_review: {
          decision: "needs_review",
          notes: "UNSAVED_EDITOR_NOTE",
        },
      },
    }),
  );
});

test("report whitelisting never accesses images or copies credentials, descriptions, job IDs or arbitrary metadata", () => {
  const event = { ...finding };
  Object.defineProperty(event, "evidence_frames", {
    get() {
      throw new Error("images must not be accessed");
    },
  });
  const report = buildReviewReport({
    ...options,
    job: {
      ...job,
      token: "PRIVATE_TOKEN",
      authorization: "Bearer PRIVATE_AUTH",
      violations: [event],
      result: { token: "PRIVATE_NESTED_TOKEN" },
      metadata: {
        ...job.metadata,
        source_path: "PRIVATE_PATH",
        secret: "PRIVATE_METADATA",
        image_base64: "PRIVATE_METADATA_IMAGE",
      },
    },
  });
  for (const privateValue of [
    "PRIVATE_TOKEN",
    "PRIVATE_AUTH",
    "PRIVATE_NESTED_TOKEN",
    "PRIVATE_PATH",
    "PRIVATE_METADATA",
    "PRIVATE_IMAGE_BYTES",
    "PRIVATE_MODEL_DESCRIPTION",
    "PRIVATE_JOB_IDENTIFIER",
  ])
    assert.ok(!report.includes(privateValue));
  assert.match(report, /Model: local_cpu_v1/);
  assert.match(report, /Model version: v1.0/);
  assert.match(report, /Action type is unclassified/);
  assert.match(report, /Uncalibrated model score: 0.875/);
});

test("synthetic reports ignore real-job data and distinguish browser-only saved assessment", () => {
  const report = buildReviewReport({
    ...options,
    demo: true,
    fileName: "PRIVATE_REAL_FILE.mp4",
    job: { ...job, human_review: { ...saved, notes: "PRIVATE_REAL_REVIEW" } },
    demoFindings: [{ ...finding, timecode_sec: 59.9996 }],
    demoReview: { ...saved, notes: "Saved synthetic review" },
  });
  assert.match(report, /SYNTHETIC EXAMPLE/);
  assert.match(report, /Automatic assessment: Illustration only/);
  assert.match(report, /Saved browser-only synthetic assessment/);
  assert.match(report, /01:00.000/);
  assert.doesNotMatch(
    report,
    /PRIVATE_REAL|Saved server receipt|Model: local_cpu_v1/,
  );
});

test("RU and EN retain precise source time and deterministic UTC receipts independent of locale", () => {
  const en = buildReviewReport(options);
  const ru = buildReviewReport({ ...options, lang: "ru" });
  for (const report of [en, ru]) {
    assert.ok(report.includes("2026-10-18T06:32:00.000Z"));
    assert.ok(report.includes(new Date(saved.updated_at * 1000).toISOString()));
    assert.ok(report.includes("00:33.500"));
  }
  assert.match(ru, /Недоступна — требуется проверка человеком/);
  assert.match(ru, /Несохранённые изменения редактора исключены/);
  assert.match(ru, /Тип действия не классифицирован/);
});

test("incomplete or malformed report fields fail closed and do not mutate the result", () => {
  const before = structuredClone(job);
  for (const status of ["processing", "failed"])
    assert.throws(() =>
      buildReviewReport({ ...options, job: { ...job, status } }),
    );
  for (const bad of [NaN, Infinity, -1])
    assert.throws(() =>
      buildReviewReport({
        ...options,
        job: { ...job, violations: [{ ...finding, timecode_sec: bad }] },
      }),
    );
  assert.throws(() =>
    buildReviewReport({
      ...options,
      job: { ...job, human_review: { ...saved, event_index: 1 } },
    }),
  );
  assert.throws(() =>
    buildReviewReport({ ...options, generatedAt: new Date(NaN) }),
  );
  assert.deepEqual(job, before);
});

test("filenames are reduced to a bounded single basename and arbitrary model strings are not echoed", () => {
  const report = buildReviewReport({
    ...options,
    fileName: "C:\\private-folder\\review\nfile.mp4",
    job: {
      ...job,
      metadata: {
        model_kind: "data:PRIVATE_PAYLOAD",
        model_version: "C:/PRIVATE_MODEL_PATH",
      },
    },
  });
  assert.match(report, /File: review file.mp4\n/);
  assert.doesNotMatch(
    report,
    /private-folder|PRIVATE_PAYLOAD|PRIVATE_MODEL_PATH/,
  );
});
