import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowSquareOut,
  ArrowsOut,
  BookOpen,
  Check,
  CheckCircle,
  CircleNotch,
  Clock,
  CloudArrowUp,
  Code,
  Cpu,
  Eye,
  FileVideo,
  Globe,
  HardDrives,
  Info,
  LockKey,
  Pause,
  Play,
  Plus,
  ShieldCheck,
  SlidersHorizontal,
  VideoCamera,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import { copy } from "./copy";
import { InvalidResultError, parseHumanReview, parseUiJob } from "./contracts";
import {
  EvidenceDialog,
  fmtTime,
  fmtSourceTime,
  HumanDecisionPanel,
  SyntheticScene,
} from "./ReviewTools";
import type {
  Finding,
  FrameSelection,
  Health,
  HumanReview,
  Job,
  Lang,
  Page,
  ReviewInput,
  ReviewDraft,
  Rule,
} from "./types";

const base =
  (import.meta as unknown as { env: Record<string, string> }).env
    .VITE_API_BASE_URL || "";
const neutralText = (value?: string) =>
  (value || "").replace(/ForteBank/gi, "организации");
class HttpError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${base}${path}`, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new HttpError(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.message ||
            data.error?.message ||
            `Request failed (${response.status})`,
      response.status,
    );
  return data;
}
const demoFindings: Finding[] = [
  {
    type: "visual_review_signal",
    timecode_sec: 34,
    description:
      "Illustrative activity near the service desk is selected for human review. Inspect the full sequence before deciding.",
    rule_id: "CR-001",
    confidence: 0.78,
    evidence_frames: [33.5, 34, 34.5].map((timestamp_sec) => ({
      timestamp_sec,
      image_base64: "",
    })),
  },
  {
    type: "visual_review_signal",
    timecode_sec: 67,
    description:
      "A second illustrative moment is marked for review. The scene does not establish a rule breach.",
    rule_id: "CR-001",
    confidence: 0.64,
    evidence_frames: [66.5, 67, 67.5].map((timestamp_sec) => ({
      timestamp_sec,
      image_base64: "",
    })),
  },
];
const emptyReviewDraft = (): ReviewDraft => ({
  decision: "",
  notes: "",
  scope: "all",
  saved: false,
});

export default function App() {
  const [lang, setLang] = useState<Lang>("en");
  const t = copy[lang];
  const [page, setPage] = useState<Page>("review");
  const [health, setHealth] = useState<Health | null>(null);
  const [checking, setChecking] = useState(true);
  const [rules, setRules] = useState<Rule[]>([]);
  const [rulesLoading, setRulesLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [demo, setDemo] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const [selected, setSelected] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(90);
  const [elapsed, setElapsed] = useState(0);
  const [frameSelection, setFrameSelection] = useState<FrameSelection | null>(
    null,
  );
  const [demoReview, setDemoReview] = useState<HumanReview | null>(null);
  const [reviewDraft, setReviewDraft] = useState<ReviewDraft>(emptyReviewDraft);
  const [reviewSaving, setReviewSaving] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const player = useRef<HTMLDivElement>(null);
  const generation = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const uploadStarted = useRef(0);
  const runtime = health?.engine || health;
  const ready = health?.ready ?? runtime?.ready ?? false;
  const uploadLimit =
    typeof health?.max_upload_bytes === "number" &&
    Number.isFinite(health.max_upload_bytes) &&
    health.max_upload_bytes > 0
      ? health.max_upload_bytes
      : 64 * 1024 * 1024;
  const uploadLimitLabel = (uploadLimit / 1024 / 1024).toLocaleString(lang, {
    maximumFractionDigits: 1,
  });
  const formatLabel = t.format.replace("64", uploadLimitLabel);
  const findings = demo
    ? demoFindings.map((finding, index) => ({
        ...finding,
        description: index === 0 ? t.demoObservationOne : t.demoObservationTwo,
      }))
    : job?.violations || [];
  const active = findings[selected];
  const rule = rules.find((value) => value.id === active?.rule_id);
  const isResult = demo || job?.status === "done";
  const inProgress = busy || job?.status === "processing";
  const experimental =
    demo ||
    (job?.metadata?.validation_status ?? runtime?.validation_status) !==
      "validated";
  const refreshHealth = useCallback(async () => {
    setChecking(true);
    try {
      const response = await fetch(`${base}/api/health/ready`, {
        signal: AbortSignal.timeout(10000),
      });
      setHealth(await response.json());
    } catch {
      setHealth(null);
    } finally {
      setChecking(false);
    }
  }, []);
  useEffect(() => {
    void refreshHealth();
    request("/api/rules", { signal: AbortSignal.timeout(10000) })
      .then((data) =>
        setRules(
          Array.isArray(data)
            ? data
            : Array.isArray(data.rules)
              ? data.rules
              : [],
        ),
      )
      .catch(() => setRules([]))
      .finally(() => setRulesLoading(false));
    return () => activeRequest.current?.abort();
  }, [refreshHealth]);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => {
    if (page !== "review") setPlaying(false);
  }, [page]);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setVideoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!inProgress) return;
    const timer = setInterval(
      () =>
        setElapsed(
          Math.max(0, Math.floor((Date.now() - uploadStarted.current) / 1000)),
        ),
      1000,
    );
    return () => clearInterval(timer);
  }, [inProgress]);
  useEffect(() => {
    if (!demo || !playing) return;
    const timer = setInterval(
      () => setCurrent((value) => (value >= 90 ? 0 : value + 0.25)),
      250,
    );
    return () => clearInterval(timer);
  }, [demo, playing]);
  useEffect(() => {
    if (!job || job.status !== "processing" || !token) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const deadline = job.deadline_at
      ? job.deadline_at * 1000 + 3000
      : uploadStarted.current + 303000;
    const poll = async () => {
      if (Date.now() > deadline) {
        setJob((value) =>
          value
            ? {
                ...value,
                status: "failed",
                error: { message: t.retrievalError },
              }
            : value,
        );
        return;
      }
      try {
        const data = await request(`/api/ui/jobs/${job.job_id}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(
              Math.max(1, Math.min(15000, deadline - Date.now())),
            ),
          ]),
        });
        if (!stopped) {
          const next = parseUiJob(data, job.job_id, t.invalidResult);
          setJob(next);
          if (next.status === "done") {
            const sourceDuration = next.metadata?.duration_sec;
            if (
              typeof sourceDuration === "number" &&
              Number.isFinite(sourceDuration) &&
              sourceDuration > 0
            )
              setDuration(sourceDuration);
            if (next.human_review)
              setReviewDraft({
                decision: next.human_review.decision,
                notes: next.human_review.notes,
                scope:
                  next.human_review.event_index == null
                    ? "all"
                    : String(next.human_review.event_index),
                saved: true,
              });
          }
          if (data.status === "processing") timer = setTimeout(poll, 1000);
        }
      } catch (e) {
        if (stopped) return;
        if (
          e instanceof InvalidResultError ||
          (e instanceof HttpError && [401, 403, 404].includes(e.status))
        )
          setJob((value) =>
            value
              ? { ...value, status: "failed", error: { message: e.message } }
              : value,
          );
        else timer = setTimeout(poll, 2500);
      }
    };
    timer = setTimeout(poll, 500);
    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [job?.job_id, job?.status, token, t.retrievalError, t.invalidResult]);
  const seek = useCallback(
    (seconds: number) => {
      const next = Math.max(
        0,
        Math.min(seconds, Number.isFinite(duration) ? duration : seconds),
      );
      setCurrent(next);
      if (video.current) video.current.currentTime = next;
    },
    [duration],
  );
  const play = useCallback(() => {
    if (demo) setPlaying((value) => !value);
    else if (video.current) {
      if (video.current.paused)
        void video.current.play().catch(() => setError(t.unsupported));
      else video.current.pause();
    }
  }, [demo, t.unsupported]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        page !== "review" ||
        (!file && !demo) ||
        frameSelection ||
        e.altKey ||
        e.ctrlKey ||
        e.metaKey ||
        /INPUT|TEXTAREA|SELECT|BUTTON/.test(
          (e.target as HTMLElement).tagName,
        ) ||
        (e.target as HTMLElement).isContentEditable
      )
        return;
      if (e.code === "Space") {
        e.preventDefault();
        play();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        seek(current - 5);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        seek(current + 5);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [page, file, demo, frameSelection, current, play, seek]);
  function reset() {
    generation.current++;
    activeRequest.current?.abort();
    setDemo(false);
    setFile(null);
    setVideoUrl("");
    setJob(null);
    setToken("");
    setError("");
    setSelected(0);
    setPlaying(false);
    setCurrent(0);
    setDuration(90);
    setBusy(false);
    setElapsed(0);
    setFrameSelection(null);
    setDemoReview(null);
    setReviewDraft(emptyReviewDraft());
    setReviewSaving(false);
    setPage("review");
    if (input.current) input.current.value = "";
  }
  function choose(value?: File) {
    if (!value) return;
    if (!value.name.toLowerCase().endsWith(".mov")) {
      setError(t.formatError);
      return;
    }
    if (value.size > uploadLimit) {
      setError(t.sizeError.replace("64", uploadLimitLabel));
      return;
    }
    reset();
    setFile(value);
  }
  async function analyze() {
    if (!file || busy) return;
    setBusy(true);
    setJob(null);
    setError("");
    setElapsed(0);
    uploadStarted.current = Date.now();
    const run = generation.current;
    const controller = new AbortController();
    activeRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 300000);
    try {
      const body = new FormData();
      body.append("file", file);
      const data = await request("/api/ui/analyze", {
        method: "POST",
        body,
        signal: controller.signal,
      });
      if (run !== generation.current) return;
      if (
        typeof data.job_id !== "string" ||
        !data.job_id ||
        typeof data.access_token !== "string" ||
        !data.access_token
      )
        throw new InvalidResultError(t.invalidResult);
      setToken(data.access_token);
      setJob({ job_id: data.job_id, status: "processing", progress: 0 });
    } catch (e) {
      if (run === generation.current)
        setError(
          e instanceof HttpError || e instanceof InvalidResultError
            ? e.message
            : t.networkError,
        );
    } finally {
      clearTimeout(timeout);
      if (run === generation.current) setBusy(false);
    }
  }
  async function saveReview(value: ReviewInput) {
    if (demo) {
      const result = {
        ...value,
        event_index: value.event_index ?? null,
        updated_at: Date.now() / 1000,
      };
      setDemoReview(result);
      setReviewDraft({
        decision: result.decision,
        notes: result.notes,
        scope: result.event_index == null ? "all" : String(result.event_index),
        saved: true,
      });
      return result;
    }
    if (!job || !token) throw new Error(t.reviewError);
    const savingJobId = job.job_id;
    const savingGeneration = generation.current;
    setReviewSaving(true);
    try {
      const response = await request(`/api/ui/jobs/${job.job_id}/review`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(value),
        signal: AbortSignal.timeout(20000),
      });
      const savedReview = parseHumanReview(
        response.human_review,
        t.reviewError,
      );
      setJob((previous) =>
        previous &&
        previous.job_id === savingJobId &&
        generation.current === savingGeneration
          ? { ...previous, human_review: savedReview }
          : previous,
      );
      if (generation.current === savingGeneration)
        setReviewDraft({
          decision: savedReview.decision,
          notes: savedReview.notes,
          scope:
            savedReview.event_index == null
              ? "all"
              : String(savedReview.event_index),
          saved: true,
        });
      return savedReview;
    } finally {
      if (generation.current === savingGeneration) setReviewSaving(false);
    }
  }
  function jumpToVideo(seconds: number) {
    seek(seconds);
    player.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "center",
    });
  }
  const nav = [
    { id: "review" as const, label: t.review, icon: VideoCamera },
    { id: "sources" as const, label: t.sources, icon: BookOpen },
    { id: "system" as const, label: t.system, icon: SlidersHorizontal },
  ];
  const validation = runtime?.validation_summary;
  const reportedMetrics = validation
    ? Object.entries(validation).filter(
        ([key, value]) =>
          [
            "accuracy",
            "precision",
            "recall",
            "specificity",
            "f1",
            "balanced_accuracy",
          ].includes(key) &&
          typeof value === "number" &&
          Number.isFinite(value) &&
          value >= 0 &&
          value <= 1,
      )
    : [];
  const warnings = Array.isArray(job?.metadata?.warnings)
    ? job.metadata.warnings.filter(
        (value): value is string => typeof value === "string",
      )
    : runtime?.limitations || [];
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        {t.skipContent}
      </a>
      <header className="app-header">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setPage("review");
          }}
          aria-label={t.home}
        >
          <span className="brand-symbol">
            <i />
            <i />
            <i />
          </span>
          <span>Cash Review</span>
        </a>
        <nav className="main-nav" aria-label={t.navigation}>
          {nav.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "active" : ""}
              onClick={() => setPage(item.id)}
              aria-current={page === item.id ? "page" : undefined}
            >
              <item.icon size={20} aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="header-tools">
          <span className={`service-state ${ready ? "is-ready" : ""}`}>
            <i />
            {checking ? t.checking : ready ? t.ready : t.unready}
          </span>
          <button
            className="language-button"
            onClick={() => setLang((value) => (value === "en" ? "ru" : "en"))}
            aria-label={t.language}
          >
            <Globe size={19} />
            {lang.toUpperCase()}
          </button>
        </div>
      </header>
      <main
        id="main"
        className={`workspace ${isResult && page === "review" ? "results-workspace" : ""}`}
      >
        {error && (
          <div className="error-banner" role="alert">
            <WarningCircle size={24} />
            <p>{error}</p>
            <button
              className="icon-button"
              onClick={() => setError("")}
              aria-label={t.dismiss}
            >
              <X size={20} />
            </button>
          </div>
        )}
        {page === "review" ? (
          <>
            <div className={`page-heading ${isResult ? "result-heading" : ""}`}>
              <div>
                {!isResult && !file && (
                  <span className="quiet-label">
                    <ShieldCheck size={17} />
                    {t.local}
                  </span>
                )}
                <h1>{isResult ? t.summary : file ? t.selected : t.title}</h1>
                <p>
                  {isResult
                    ? `${demo ? t.previewMode : file?.name || t.review}`
                    : t.intro}
                </p>
              </div>
              {(file || demo || job) && (
                <button className="button secondary" onClick={reset}>
                  <Plus size={20} />
                  {t.new}
                </button>
              )}
            </div>
            {demo && (
              <div className="preview-banner">
                <Eye size={22} />
                <strong>{t.previewMode}</strong>
                <span>{t.previewNotice}</span>
                <button onClick={reset}>
                  {t.exitPreview}
                  <X size={17} />
                </button>
              </div>
            )}
            {!file && !demo && !job ? (
              <>
                <div className="start-layout">
                  <section
                    className={`upload-zone ${drag ? "dragging" : ""}`}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setDrag(true);
                    }}
                    onDragLeave={() => setDrag(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setDrag(false);
                      choose(e.dataTransfer.files[0]);
                    }}
                  >
                    <div className="upload-symbol">
                      <FileVideo size={48} weight="duotone" />
                      <span>
                        <Plus size={20} weight="bold" />
                      </span>
                    </div>
                    <h2>{t.upload}</h2>
                    <p>{t.uploadHint}</p>
                    <button
                      className="button primary large"
                      onClick={() => input.current?.click()}
                    >
                      <CloudArrowUp size={22} />
                      {t.choose}
                    </button>
                    <span className="file-format">{formatLabel}</span>
                    <div className="upload-privacy">
                      <LockKey size={16} />
                      {t.private}
                    </div>
                  </section>
                  <aside className="start-aside">
                    <h2>{t.human}</h2>
                    <p>{t.humanHint}</p>
                    <div className="workflow-list">
                      {[
                        {
                          title: t.analysisStep,
                          text: t.analysisStepText,
                          icon: Cpu,
                        },
                        {
                          title: t.inspectStep,
                          text: t.inspectStepText,
                          icon: ArrowsOut,
                        },
                        {
                          title: t.humanStep,
                          text: t.humanStepText,
                          icon: Eye,
                        },
                      ].map((item, index) => (
                        <div key={item.title}>
                          <span>{index + 1}</span>
                          <div>
                            <h3>{item.title}</h3>
                            <p>{item.text}</p>
                          </div>
                          <item.icon size={23} aria-hidden="true" />
                        </div>
                      ))}
                    </div>
                    <button
                      className="preview-button"
                      onClick={() => {
                        reset();
                        setDemo(true);
                        setCurrent(34);
                      }}
                    >
                      <Play size={22} weight="fill" />
                      <span>
                        <strong>{t.preview}</strong>
                        <small>{t.previewHint}</small>
                      </span>
                      <ArrowRight size={22} />
                    </button>
                  </aside>
                </div>
                <div className="privacy-strip">
                  <ShieldCheck size={22} />
                  <span>{t.offlineText}</span>
                  <span>
                    <Check size={17} />
                    {t.noIdentity}
                  </span>
                </div>
              </>
            ) : (
              <>
                {isResult && (
                  <section
                    className={`verdict-banner ${job?.verdict === "no_violation" && !demo ? "no-concern" : "has-concern"}`}
                    aria-label={t.model}
                  >
                    <div className="verdict-icon">
                      {job?.verdict === "no_violation" && !demo ? (
                        <ShieldCheck size={38} />
                      ) : (
                        <WarningCircle size={38} />
                      )}
                    </div>
                    <div>
                      <div className="verdict-label">
                        <span>{t.model}</span>
                        {experimental && (
                          <span className="experimental-tag">
                            {t.experimental}
                          </span>
                        )}
                      </div>
                      <h2>
                        {job?.verdict === "no_violation" && !demo
                          ? t.noConcern
                          : t.concern}
                      </h2>
                      <p>
                        {job?.verdict === "no_violation" && !demo
                          ? t.negativeNote
                          : t.predictionNote}
                      </p>
                    </div>
                    <div className="verdict-count">
                      <strong>{findings.length}</strong>
                      <span>{t.count}</span>
                    </div>
                  </section>
                )}
                <div
                  className={`review-layout ${isResult ? "with-results" : ""}`}
                >
                  <div className="evidence-workspace">
                    <section className="video-panel" ref={player}>
                      <div className="panel-header">
                        <h2>
                          <FileVideo size={21} />
                          {t.source}
                        </h2>
                        <span>
                          {demo
                            ? "01:30"
                            : file
                              ? `${(file.size / 1024 / 1024).toFixed(1)} MiB`
                              : ""}
                        </span>
                      </div>
                      <div
                        className={`video-stage ${isResult ? "result-video" : ""}`}
                      >
                        {demo ? (
                          <SyntheticScene active={playing} t={t} />
                        ) : (
                          <video
                            ref={video}
                            src={videoUrl}
                            preload="metadata"
                            onLoadedMetadata={(e) => {
                              const element = e.currentTarget;
                              if (
                                Number.isFinite(element.duration) &&
                                element.duration > 0
                              ) {
                                setDuration(element.duration);
                                element.currentTime = Math.min(
                                  current,
                                  element.duration,
                                );
                              }
                              setPlaying(!element.paused);
                            }}
                            onError={() => setError(t.unsupported)}
                            onTimeUpdate={(e) =>
                              setCurrent(e.currentTarget.currentTime)
                            }
                            onPlay={() => setPlaying(true)}
                            onPause={() => setPlaying(false)}
                            playsInline
                            controls={false}
                          />
                        )}
                        <span className="video-origin-label">
                          {demo ? t.previewMode : t.sourceTime}
                        </span>
                        {inProgress && (
                          <div className="processing-card" role="status">
                            <CircleNotch size={29} className="spin" />
                            <div>
                              <strong>
                                {busy ? t.uploading : t.processing}
                              </strong>
                              <span>{job?.stage || t.processHint}</span>
                            </div>
                            <span className="elapsed-time">
                              {fmtTime(elapsed)} / 05:00
                            </span>
                            <div
                              className={`progress-track ${busy ? "indeterminate" : ""}`}
                            >
                              <i
                                style={{
                                  width: busy
                                    ? undefined
                                    : `${Math.min(100, Math.max(0, job?.progress || 0))}%`,
                                }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="player-controls">
                        <button
                          className="icon-button play-button"
                          aria-label={playing ? t.pause : t.play}
                          onClick={play}
                        >
                          {playing ? (
                            <Pause size={23} weight="fill" />
                          ) : (
                            <Play size={23} weight="fill" />
                          )}
                        </button>
                        <span className="player-time">
                          {fmtTime(current)} <i>/</i> {fmtTime(duration)}
                        </span>
                        <input
                          type="range"
                          min="0"
                          max={Number.isFinite(duration) ? duration : 90}
                          step="0.1"
                          value={Number.isFinite(current) ? current : 0}
                          onChange={(e) => seek(Number(e.target.value))}
                          aria-label={t.videoPosition}
                        />
                        <button
                          className="icon-button"
                          aria-label={t.fullScreen}
                          onClick={() =>
                            void player.current?.requestFullscreen?.()
                          }
                        >
                          <ArrowsOut size={22} />
                        </button>
                      </div>
                      <div className="player-keyboard">{t.keyboard}</div>
                    </section>
                    {!isResult && !inProgress && (
                      <div className="analysis-action">
                        <div>
                          <strong>{file?.name}</strong>
                          <span>{formatLabel}</span>
                        </div>
                        <button
                          className="button primary large"
                          disabled={!ready}
                          onClick={() => void analyze()}
                        >
                          <Cpu size={22} />
                          {t.analyze}
                        </button>
                      </div>
                    )}
                    {!ready && !isResult && !inProgress && (
                      <div className="inline-notice">
                        <Info size={22} />
                        <p>{t.notReadyText}</p>
                        <button onClick={() => setPage("system")}>
                          {t.moreDetails}
                          <ArrowRight size={18} />
                        </button>
                      </div>
                    )}
                    {inProgress && (
                      <p className="tab-notice">
                        <LockKey size={16} />
                        {t.tabHint}
                      </p>
                    )}
                    {job?.status === "failed" && (
                      <div className="failure-panel" role="alert">
                        <WarningCircle size={36} />
                        <h2>{t.failed}</h2>
                        <p>
                          {typeof job.error === "string"
                            ? job.error
                            : job.error?.message || t.networkError}
                        </p>
                        <button
                          className="button secondary"
                          onClick={() => {
                            setJob(null);
                            setToken("");
                            setError("");
                          }}
                        >
                          {t.retry}
                        </button>
                      </div>
                    )}
                    {isResult && (
                      <section className="candidate-section">
                        <div className="section-heading">
                          <div>
                            <h2>{t.candidates}</h2>
                            <p>{t.evidenceHint}</p>
                          </div>
                          <span className="count-label">{findings.length}</span>
                        </div>
                        {findings.length === 0 ? (
                          <div className="empty-state">
                            <ShieldCheck size={38} />
                            <h3>{t.noEvent}</h3>
                            <p>{t.noEventText}</p>
                          </div>
                        ) : (
                          <>
                            <div
                              className="candidate-tabs"
                              role="group"
                              aria-label={t.candidates}
                            >
                              {findings.map((finding, index) => (
                                <button
                                  key={index}
                                  className={
                                    selected === index ? "selected" : ""
                                  }
                                  onClick={() => {
                                    setSelected(index);
                                    seek(finding.timecode_sec);
                                  }}
                                  aria-pressed={selected === index}
                                >
                                  <span>
                                    {t.candidate} {index + 1}
                                  </span>
                                  <strong>
                                    <Clock size={18} />
                                    {fmtSourceTime(finding.timecode_sec)}
                                  </strong>
                                </button>
                              ))}
                            </div>
                            {active && (
                              <article className="candidate-detail">
                                <div className="candidate-title">
                                  <div>
                                    <h3>
                                      {t.candidate} {selected + 1}
                                    </h3>
                                    <span className="event-type">
                                      {t.modelType}:{" "}
                                      {active.type === "visual_review_signal"
                                        ? t.genericType
                                        : neutralText(active.type).replaceAll(
                                            "_",
                                            " ",
                                          )}
                                    </span>
                                  </div>
                                  <button
                                    className="timestamp-button"
                                    onClick={() =>
                                      jumpToVideo(active.timecode_sec)
                                    }
                                  >
                                    <Play size={18} weight="fill" />
                                    {fmtSourceTime(active.timecode_sec)}
                                    <span>{t.jump}</span>
                                  </button>
                                </div>
                                <div className="evidence-frames">
                                  {active.evidence_frames?.map(
                                    (frame, index) => (
                                      <button
                                        className="evidence-frame"
                                        key={index}
                                        onClick={() =>
                                          setFrameSelection({
                                            event: selected,
                                            frame: index,
                                          })
                                        }
                                        aria-label={`${t.evidence} ${fmtSourceTime(frame.timestamp_sec)} — ${t.fullScreen}`}
                                      >
                                        <div>
                                          {demo ? (
                                            <SyntheticScene t={t} />
                                          ) : (
                                            <img
                                              src={`data:image/jpeg;base64,${frame.image_base64}`}
                                              alt={`${t.evidence} ${fmtSourceTime(frame.timestamp_sec)}`}
                                              loading="lazy"
                                            />
                                          )}
                                          <span className="frame-expand">
                                            <ArrowsOut size={21} />
                                          </span>
                                        </div>
                                        <span>
                                          <Clock size={17} />
                                          {fmtSourceTime(frame.timestamp_sec)}
                                          <small>
                                            {t.frame} {index + 1}
                                          </small>
                                        </span>
                                      </button>
                                    ),
                                  )}
                                </div>
                                <div className="observation-block">
                                  <div>
                                    <span className="field-label">
                                      {t.observation}
                                    </span>
                                    <p>
                                      {demo && lang === "ru"
                                        ? "Иллюстративный момент выбран для ручной проверки. Изучите полную последовательность перед решением."
                                        : neutralText(active.description)}
                                    </p>
                                  </div>
                                  {typeof active.confidence === "number" && (
                                    <div className="model-score">
                                      <span>{t.score}</span>
                                      <strong>
                                        {active.confidence.toFixed(2)}
                                      </strong>
                                      <small>{t.scoreHint}</small>
                                    </div>
                                  )}
                                </div>
                                <div className="candidate-source">
                                  <BookOpen size={22} />
                                  <div>
                                    <span>{t.context}</span>
                                    <p>
                                      {rule
                                        ? neutralText(rule.title)
                                        : t.sourceUnavailable}
                                    </p>
                                    <small>
                                      {rule?.enabled_for_legal_claim
                                        ? t.ruleEnabled
                                        : t.contextOnly}
                                    </small>
                                  </div>
                                  <button
                                    className="text-button"
                                    onClick={() => setPage("sources")}
                                  >
                                    {t.viewSource}
                                    <ArrowSquareOut size={18} />
                                  </button>
                                </div>
                              </article>
                            )}
                          </>
                        )}
                      </section>
                    )}
                  </div>
                  {isResult ? (
                    <aside className="human-column">
                      <HumanDecisionPanel
                        key={demo ? "demo" : job?.job_id}
                        t={t}
                        findings={findings}
                        review={demo ? demoReview : job?.human_review}
                        demo={demo}
                        onSave={saveReview}
                        draft={reviewDraft}
                        onDraftChange={setReviewDraft}
                        saving={reviewSaving}
                      />
                      <div className="review-safety-note">
                        <ShieldCheck size={22} />
                        <p>{t.predictionNote}</p>
                      </div>
                    </aside>
                  ) : (
                    <aside className="processing-aside">
                      <Cpu size={32} />
                      <h2>{t.analysisStep}</h2>
                      <p>{t.analysisStepText}</p>
                      <div>
                        <CheckCircle size={20} />
                        {t.private}
                      </div>
                      <div>
                        <CheckCircle size={20} />
                        {t.noIdentity}
                      </div>
                    </aside>
                  )}
                </div>
              </>
            )}
          </>
        ) : page === "sources" ? (
          <>
            <div className="page-heading">
              <div>
                <span className="quiet-label">
                  <BookOpen size={18} />
                  {t.sources}
                </span>
                <h1>{t.libraryTitle}</h1>
                <p>{t.libraryIntro}</p>
              </div>
            </div>
            <div className="sources-layout">
              <div>
                {rulesLoading ? (
                  <div className="empty-state">
                    <CircleNotch size={28} className="spin" />
                  </div>
                ) : rules.length ? (
                  rules.map((item) => (
                    <article className="source-card" key={item.id}>
                      <div className="source-card-heading">
                        <span>{item.id}</span>
                        <span className="context-tag">
                          {item.enabled_for_legal_claim
                            ? t.ruleEnabled
                            : t.contextOnly}
                        </span>
                      </div>
                      <h2>{neutralText(item.title)}</h2>
                      <p className="source-issuer">
                        {neutralText(item.issuer)}
                        {item.section ? ` — ${neutralText(item.section)}` : ""}
                      </p>
                      <p>{neutralText(item.summary)}</p>
                      <h3>{t.applicability}</h3>
                      <p>{neutralText(item.applicability)}</p>
                      {item.limitations && (
                        <details>
                          <summary>{t.limitations}</summary>
                          <ul>
                            {(Array.isArray(item.limitations)
                              ? item.limitations
                              : [item.limitations]
                            ).map((text, index) => (
                              <li key={index}>{neutralText(text)}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                      {item.url && /^https:\/\//.test(item.url) && (
                        <a
                          className="source-link"
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {t.sourceLink}
                          <ArrowSquareOut size={19} />
                        </a>
                      )}
                    </article>
                  ))
                ) : (
                  <div className="empty-state">
                    <BookOpen size={36} />
                    <p>{t.noSources}</p>
                  </div>
                )}
              </div>
              <aside className="source-guidance">
                <ShieldCheck size={30} />
                <h2>{t.contextOnly}</h2>
                <p>{t.predictionNote}</p>
                <button
                  className="text-button"
                  onClick={() => setPage("review")}
                >
                  <ArrowLeft size={18} />
                  {t.review}
                </button>
              </aside>
            </div>
          </>
        ) : (
          <>
            <div className="page-heading">
              <div>
                <span className="quiet-label">
                  <HardDrives size={18} />
                  {t.local}
                </span>
                <h1>{t.systemTitle}</h1>
                <p>{t.systemIntro}</p>
              </div>
              <button
                className="button secondary"
                onClick={() => void refreshHealth()}
              >
                <SlidersHorizontal size={19} />
                {t.refresh}
              </button>
            </div>
            <div className="system-layout">
              <section className="system-card">
                <h2>
                  <Cpu size={24} />
                  {t.runtime}
                </h2>
                <div className={`runtime-status ${ready ? "is-ready" : ""}`}>
                  <i />
                  {checking ? t.checking : ready ? t.ready : t.unready}
                </div>
                <dl>
                  <div>
                    <dt>{t.modelVersion}</dt>
                    <dd>{runtime?.model_version || t.unknown}</dd>
                  </div>
                  <div>
                    <dt>{t.modelKind}</dt>
                    <dd>
                      {runtime?.model_kind?.replaceAll("_", " ") || t.unknown}
                    </dd>
                  </div>
                </dl>
                {experimental && (
                  <div className="experimental-notice">
                    <Info size={20} />
                    <p>{t.modelWarning}</p>
                  </div>
                )}
                {health?.reasons?.length ? (
                  <ul className="health-reasons">
                    {health.reasons.map((reason, index) => (
                      <li key={index}>{neutralText(reason)}</li>
                    ))}
                  </ul>
                ) : null}
                <h3>{t.validation}</h3>
                {reportedMetrics.length ? (
                  <dl className="validation-metrics">
                    {reportedMetrics.map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{((value as number) * 100).toFixed(1)}%</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p>{t.noMetrics}</p>
                )}
              </section>
              <section className="system-card api-card">
                <h2>
                  <Code size={24} />
                  {t.api}
                </h2>
                <p>{t.apiText}</p>
                <div className="endpoint">
                  <b>POST</b>
                  <code>/api/v1/analyze</code>
                </div>
                <div className="endpoint">
                  <b>GET</b>
                  <code>/api/v1/jobs/&#123;job_id&#125;</code>
                </div>
                <pre>
                  {
                    'curl -X POST http://127.0.0.1:8000/api/v1/analyze \\\n  -H "X-API-Key: $CASH_REVIEW_API_KEY" \\\n  -F "file=@clip.mov"'
                  }
                </pre>
              </section>
            </div>
            <div className="system-features">
              {[
                { title: t.offline, text: t.offlineText, icon: HardDrives },
                { title: t.deadline, text: t.deadlineText, icon: Clock },
                { title: t.privacy, text: t.privacyText, icon: LockKey },
              ].map((item) => (
                <section key={item.title}>
                  <item.icon size={26} />
                  <h2>{item.title}</h2>
                  <p>{item.text}</p>
                </section>
              ))}
            </div>
            {warnings.length > 0 && (
              <section className="model-limitations">
                <h2>{t.modelLimits}</h2>
                <ul>
                  {warnings.map((warning, index) => (
                    <li key={index}>{neutralText(warning)}</li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
        <footer className="app-footer">
          <span>Cash Review</span>
          <p>{t.footer}</p>
          <span>
            <LockKey size={15} />
            {t.local}
          </span>
        </footer>
      </main>
      <input
        ref={input}
        className="sr-only"
        type="file"
        accept=".mov,video/quicktime"
        onChange={(e) => choose(e.target.files?.[0])}
        aria-label={t.choose}
      />
      <EvidenceDialog
        selection={frameSelection}
        findings={findings}
        demo={demo}
        t={t}
        onClose={() => setFrameSelection(null)}
        onChange={setFrameSelection}
        onSeek={jumpToVideo}
      />
    </div>
  );
}
