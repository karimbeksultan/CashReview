import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowSquareOut,
  ArrowsOut,
  BookOpen,
  CaretRight,
  Check,
  CheckCircle,
  CircleNotch,
  Clock,
  CloudArrowUp,
  Code,
  Cpu,
  Eye,
  FileVideo,
  Fingerprint,
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

type Lang = "en" | "ru";
type Page = "review" | "rules" | "system";
type Evidence = { timestamp_sec: number; image_base64: string };
type Finding = {
  type: string;
  timecode_sec: number;
  description: string;
  rule_id?: string;
  confidence?: number;
  evidence_frames?: Evidence[];
};
type SponsorReference = {
  available: boolean;
  verdict?: "violation" | "no_violation" | null;
  type?: string | null;
  source?: string | null;
  timestamps_sec?: number[];
};
type Job = {
  sponsor_reference?: SponsorReference;
  job_id: string;
  status: "processing" | "done" | "failed";
  deadline_at?: number;
  progress?: number;
  stage?: string;
  verdict?: "violation" | "no_violation";
  violations?: Finding[];
  metadata?: Record<string, unknown>;
  error?: { message?: string; code?: string } | string;
  result?: Partial<Job>;
};
type Rule = {
  id: string;
  title: string;
  issuer?: string;
  url?: string;
  section?: string;
  summary?: string;
  applicability?: string;
  limitations?: string | string[];
  enabled_for_legal_claim?: boolean;
  verified?: boolean;
};
type Health = {
  ready?: boolean;
  reasons?: string[];
  engine?: { ready?: boolean; reasons?: string[]; competition_ready?: boolean };
  [key: string]: unknown;
};
const copy = {
  en: {
    workspace: "Review workspace",
    video: "Video review",
    rules: "Rule library",
    system: "System & API",
    case: "ForteBank case · Datathon 2026",
    private: "Private by design",
    privateText: "Video processing stays on your team’s machine.",
    title: "Every finding needs evidence.",
    subtitle:
      "A focused workspace for reviewing cashier operations. Upload a video, inspect the signals, make an informed decision.",
    new: "New review",
    local: "Local analysis",
    available: "Baseline available",
    unavailable: "Model not prepared",
    checking: "Checking service",
    upload: "Start with a video",
    uploadText: "Drop your cashier footage here, or choose a file to review.",
    choose: "Choose video",
    format: "MOV video · up to 64 MB · 10–145 seconds",
    preview: "Explore the interface",
    previewText: "A synthetic example. No case footage.",
    how: "From footage to a considered decision",
    step1: "Upload privately",
    step1Text: "Your video goes directly to the local service.",
    step2: "Find review signals",
    step2Text: "A local baseline scores visual patterns over time.",
    step3: "Review the evidence",
    step3Text: "Inspect source frames, timestamps and rule context.",
    pipeline: "Analysis pipeline",
    device: "On-device inference",
    noCloud: "No cloud AI calls",
    identity: "No face identification",
    evidence: "Source-frame evidence",
    human: "A person makes the decision",
    humanText:
      "The baseline flags patterns for review. It does not establish a rule breach, identify a person or prove compliance.",
    coverage: "Coverage note",
    coverageText:
      "Source labels specify violation / no violation. Event type is not specified. The current baseline flagged all eight held-out clips, including four normal clips.",
    learn: "View rule context",
    selected: "Selected video",
    analyze: "Analyze video",
    replace: "Choose another",
    previewMode: "Synthetic interface preview",
    previewNotice:
      "Illustrative signals and scene. This is not a model result or case footage.",
    exitPreview: "Exit preview",
    findings: "Review signals",
    signal: "Review signal (type not specified)",
    context: "Rule context",
    confidence: "Model score",
    notProbability: "Uncalibrated · not a probability",
    timestamp: "Source timestamp",
    observation: "Observation",
    decision: "Reviewer assessment",
    decisionText:
      "Verify the full action and applicable internal procedure before reaching a conclusion.",
    confirm: "Needs follow-up",
    dismiss: "Mark as reviewed",
    confirmed: "Marked for follow-up",
    dismissed: "Marked as reviewed",
    play: "Play video",
    pause: "Pause video",
    fullscreen: "Full screen",
    processing: "Analyzing on this machine",
    processingText:
      "Keep this page open. Access to this job is held only in this browser tab.",
    done: "Analysis complete",
    none: "No supported signals found",
    noneText:
      "This does not establish compliance. Review coverage and the original video.",
    failed: "Analysis could not complete",
    retry: "Try again",
    errorFormat: "Choose a .mov video.",
    errorSize: "The video exceeds the 64 MB limit.",
    errorNetwork:
      "The local API is unavailable. Start the backend on port 8000.",
    readyText:
      "Prepare the model to enable real analysis. You can explore the synthetic interface meanwhile.",
    libraryTitle: "A source behind every claim.",
    librarySubtitle:
      "Kazakhstan regulatory context, with explicit applicability and limitations. Context is not a finding of noncompliance.",
    source: "Open official source",
    contextOnly: "Context only",
    legal: "Verified rule mapping",
    noRules:
      "Rule library is unavailable. Start the local backend to load the reviewed registry.",
    systemTitle: "Local from end to end.",
    systemSubtitle:
      "Runtime status, model limitations and the exact jury integration contract.",
    runtime: "Runtime status",
    jury: "Jury API",
    juryText:
      "Send the jury key in the X-API-Key header. The key is configured on the server and never embedded in this interface.",
    setup: "Prepare & run",
    setupText:
      "Install the service, prepare model weights, train the baseline using private data, then start the API. See README for the reproducible workflow.",
    offline: "Offline runtime",
    offlineText:
      "After dependencies and weights are prepared, analysis uses no network services.",
    deadline: "Processing deadline",
    deadlineText:
      "300 seconds from admission, including queue time. Expired jobs fail explicitly.",
    privacy: "Private job access",
    privacyText:
      "Browser jobs use a short-lived token scoped to one job. Reloading the page loses access.",
    model: "Baseline limitations",
    modelText:
      "MobileNetV2 visual features + local logistic regression. Held-out check: all 8 clips flagged, including 4 normal clips (50% accuracy, 0% specificity). Experimental; event types are unspecified in source labels.",
    refresh: "Refresh status",
    back: "Back to upload",
    evidenceFrames: "Evidence frames",
    seek: "Jump to signal",
    syntheticObservation:
      "Illustrative activity near the service desk is marked for review. Compare the surrounding sequence and applicable procedure.",
    syntheticRule: "Cash operations · contextual reference",
    language: "Change language",
    dismissError: "Dismiss error",
    uploading: "Uploading privately",
    reviewed: "Review notes are temporary and stay in this tab.",
    zero: "No video leaves this service for cloud AI.",
    loadingRules: "Loading rule library…",
    technical: "Technical details",
    reviewSignals: "signals to inspect",
    key: "Configured server-side",
    expires: "Jobs expire after the configured retention period.",
  },
  ru: {
    workspace: "Рабочая область",
    video: "Проверка видео",
    rules: "Нормативная база",
    system: "Система и API",
    case: "Кейс ForteBank · Дататон 2026",
    private: "Приватность по умолчанию",
    privateText: "Обработка видео остаётся на компьютере команды.",
    title: "Каждый вывод — с доказательством.",
    subtitle:
      "Рабочее пространство для проверки кассовых операций. Загрузите видео, изучите сигналы и примите обоснованное решение.",
    new: "Новая проверка",
    local: "Локальный анализ",
    available: "Базовая модель доступна",
    unavailable: "Модель не подготовлена",
    checking: "Проверка сервиса",
    upload: "Начните с видео",
    uploadText: "Перетащите запись кассовой операции или выберите файл.",
    choose: "Выбрать видео",
    format: "Видео MOV · до 64 МБ · 10–145 секунд",
    preview: "Посмотреть интерфейс",
    previewText: "Синтетический пример. Без видео кейса.",
    how: "От записи к обоснованному решению",
    step1: "Приватная загрузка",
    step1Text: "Видео передаётся напрямую локальному сервису.",
    step2: "Поиск сигналов",
    step2Text: "Локальная модель оценивает визуальные паттерны.",
    step3: "Проверка доказательств",
    step3Text: "Изучите кадры, время и нормативный контекст.",
    pipeline: "Процесс анализа",
    device: "Модель на устройстве",
    noCloud: "Без облачного ИИ",
    identity: "Без идентификации лиц",
    evidence: "Кадры из оригинала",
    human: "Решение принимает человек",
    humanText:
      "Базовая модель выделяет паттерны для проверки. Она не доказывает нарушение, личность или соблюдение правил.",
    coverage: "Ограничения",
    coverageText:
      "Источник содержит метки «нарушение / без нарушения». Тип события не указан. Текущая модель отметила все восемь тестовых видео, включая четыре нормальных.",
    learn: "Нормативный контекст",
    selected: "Выбранное видео",
    analyze: "Анализировать",
    replace: "Выбрать другое",
    previewMode: "Синтетический пример интерфейса",
    previewNotice:
      "Иллюстративные сигналы и сцена. Это не результат модели и не видео кейса.",
    exitPreview: "Закрыть пример",
    findings: "Сигналы для проверки",
    signal: "Сигнал (тип не указан)",
    context: "Нормативный контекст",
    confidence: "Оценка модели",
    notProbability: "Не калибрована · не вероятность",
    timestamp: "Время в оригинале",
    observation: "Наблюдение",
    decision: "Решение проверяющего",
    decisionText:
      "Проверьте полное действие и применимость внутренней процедуры перед выводом.",
    confirm: "Нужна проверка",
    dismiss: "Проверено",
    confirmed: "Отмечено для проверки",
    dismissed: "Отмечено как проверенное",
    play: "Воспроизвести",
    pause: "Пауза",
    fullscreen: "Полный экран",
    processing: "Анализ на этом компьютере",
    processingText:
      "Не закрывайте страницу. Доступ к заданию хранится только в этой вкладке.",
    done: "Анализ завершён",
    none: "Поддерживаемые сигналы не найдены",
    noneText:
      "Это не подтверждает соблюдение правил. Учитывайте покрытие модели и просмотрите оригинал.",
    failed: "Не удалось завершить анализ",
    retry: "Повторить",
    errorFormat: "Выберите видео .mov.",
    errorSize: "Размер видео превышает 64 МБ.",
    errorNetwork: "Локальный API недоступен. Запустите бэкенд на порту 8000.",
    readyText:
      "Подготовьте модель для анализа. Пока можно посмотреть синтетический пример интерфейса.",
    libraryTitle: "Источник за каждым утверждением.",
    librarySubtitle:
      "Нормативный контекст Казахстана с явными ограничениями применимости. Контекст не означает доказанное нарушение.",
    source: "Официальный источник",
    contextOnly: "Только контекст",
    legal: "Проверенное соответствие",
    noRules: "Нормативная база недоступна. Запустите локальный бэкенд.",
    systemTitle: "Полностью локальная обработка.",
    systemSubtitle:
      "Состояние сервиса, ограничения модели и точный контракт API для жюри.",
    runtime: "Состояние сервиса",
    jury: "API для жюри",
    juryText:
      "Передайте ключ в заголовке X-API-Key. Ключ задаётся на сервере и не включён в интерфейс.",
    setup: "Подготовка и запуск",
    setupText:
      "Установите сервис, подготовьте веса, обучите модель на приватных данных и запустите API. Инструкции в README.",
    offline: "Автономная работа",
    offlineText:
      "После подготовки зависимостей и весов анализ не использует сетевые сервисы.",
    deadline: "Срок обработки",
    deadlineText:
      "300 секунд с момента приёма, включая очередь. Просроченные задания завершаются ошибкой.",
    privacy: "Приватный доступ",
    privacyText:
      "Краткосрочный токен открывает только одно задание. Перезагрузка страницы теряет доступ.",
    model: "Ограничения модели",
    modelText:
      "Признаки MobileNetV2 + локальная логистическая регрессия. Все 8 тестовых видео отмечены, включая 4 нормальных (точность 50%, специфичность 0%). Экспериментальная модель; типы событий в источнике не указаны.",
    refresh: "Обновить состояние",
    back: "Назад к загрузке",
    evidenceFrames: "Кадры-доказательства",
    seek: "Перейти к сигналу",
    syntheticObservation:
      "Иллюстративная активность у рабочего стола отмечена для проверки. Сопоставьте полную последовательность и применимую процедуру.",
    syntheticRule: "Кассовые операции · контекст",
    language: "Сменить язык",
    dismissError: "Закрыть ошибку",
    uploading: "Приватная загрузка",
    reviewed: "Заметки временные и остаются в этой вкладке.",
    zero: "Видео не передаётся облачному ИИ.",
    loadingRules: "Загрузка нормативной базы…",
    technical: "Технические сведения",
    reviewSignals: "сигналов для проверки",
    key: "Задаётся на сервере",
    expires: "Задания удаляются по установленному сроку хранения.",
  },
};
const fmtTime = (s: number) =>
  `${Math.floor(s / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(s % 60)
    .toString()
    .padStart(2, "0")}`;
const base =
  (import.meta as unknown as { env: Record<string, string> }).env
    .VITE_API_BASE_URL || "";
class APIError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request(path: string, init?: RequestInit) {
  const r = await fetch(`${base}${path}`, init);
  const data = await r.json().catch(() => ({}));
  if (!r.ok)
    throw new APIError(
      r.status,
      typeof data.detail === "string"
        ? data.detail
        : data.error?.message ||
            data.detail?.message ||
            `Request failed (${r.status})`,
    );
  return data;
}

function SyntheticScene({ active = false }: { active?: boolean }) {
  return (
    <div
      className={`synthetic-scene ${active ? "scene-active" : ""}`}
      aria-label="Synthetic overhead desk illustration"
    >
      <div className="scene-grid" />
      <div className="scene-wall" />
      <div className="scene-desk">
        <div className="desk-pad" />
        <div className="desk-monitor" />
        <div className="desk-keyboard" />
        <div className="desk-tray">
          <i />
          <i />
          <i />
        </div>
        <div className="desk-paper" />
        <div className="desk-terminal" />
      </div>
      <div className="scene-person person-a">
        <i />
        <b />
      </div>
      <div className="scene-person person-b">
        <i />
        <b />
      </div>
      <div className="scene-chair" />
      <div className="scene-door" />
      <div className="scene-detection">
        <span>Review region</span>
      </div>
      <div className="scene-label">SYNTHETIC SCENE · NO CASE FOOTAGE</div>
    </div>
  );
}

export default function App() {
  const [lang, setLang] = useState<Lang>("en");
  const t = copy[lang];
  const [page, setPage] = useState<Page>("review");
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
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
  const [note, setNote] = useState<Record<number, string>>({});
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(90);
  const [elapsed, setElapsed] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const player = useRef<HTMLDivElement>(null);
  const generation = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const ready = health?.ready ?? health?.engine?.ready ?? false;
  const refreshHealth = () => {
    setHealthError(false);
    request("/api/health/ready")
      .then(setHealth)
      .catch(() => {
        setHealthError(true);
        fetch(`${base}/api/health/ready`)
          .then((r) => r.json())
          .then(setHealth)
          .catch(() => setHealth(null));
      });
  };
  useEffect(() => {
    refreshHealth();
    request("/api/rules")
      .then((d) => setRules(Array.isArray(d) ? d : d.rules || []))
      .catch(() => {})
      .finally(() => setRulesLoading(false));
    return () => activeRequest.current?.abort();
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setVideoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!busy && job?.status !== "processing") return;
    const interval = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [busy, job?.status]);
  useEffect(() => {
    if (!demo || !playing) return;
    const timer = setInterval(
      () => setCurrent((s) => (s >= 90 ? 0 : s + 0.25)),
      250,
    );
    return () => clearInterval(timer);
  }, [demo, playing]);
  useEffect(() => {
    if (!job || job.status !== "processing" || !token) return;
    let stopped = false;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const deadline =
      (job.deadline_at
        ? job.deadline_at * 1000
        : Date.now() + Math.max(1, 300 - elapsed) * 1000) + 1000;
    const fail = (code: string, message: string) => {
      stopped = true;
      controller.abort();
      setJob((previous) =>
        previous
          ? { ...previous, status: "failed", error: { code, message } }
          : previous,
      );
    };
    const cutoff = setTimeout(
      () =>
        fail(
          "client_deadline",
          "No completed result was received within the five-minute deadline.",
        ),
      Math.max(0, deadline - Date.now()),
    );
    const poll = async () => {
      if (Date.now() > deadline) {
        fail(
          "client_deadline",
          "No completed result was received within the five-minute deadline.",
        );
        return;
      }
      try {
        const data = await request(`/api/ui/jobs/${job.job_id}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (!stopped) {
          const merged = { ...data, ...data.result };
          setJob(merged);
          if (merged.status === "processing") timer = setTimeout(poll, 1000);
        }
      } catch (e) {
        if (!stopped) {
          if (e instanceof APIError && (e.status === 401 || e.status === 404)) {
            fail("access_expired", e.message);
            return;
          }
          setError(e instanceof Error ? e.message : t.errorNetwork);
          timer = setTimeout(poll, 3000);
        }
      }
    };
    timer = setTimeout(poll, 600);
    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
      clearTimeout(cutoff);
    };
  }, [job?.job_id, job?.status, token, t.errorNetwork]);
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
    setNote({});
    setPlaying(false);
    setCurrent(0);
    setDuration(90);
    setBusy(false);
    setElapsed(0);
    setPage("review");
    if (input.current) input.current.value = "";
  }
  function choose(f?: File) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".mov")) {
      setError(t.errorFormat);
      return;
    }
    if (f.size > 64 * 1024 * 1024) {
      setError(t.errorSize);
      return;
    }
    reset();
    setFile(f);
  }
  async function analyze() {
    if (!file || busy) return;
    setBusy(true);
    setError("");
    setElapsed(0);
    const started = Date.now();
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
      setToken(data.access_token);
      setJob({
        job_id: data.job_id,
        status: "processing",
        progress: 0,
        deadline_at: started / 1000 + 300,
      });
    } catch (e) {
      if (run === generation.current)
        setError(
          controller.signal.aborted
            ? "No completed result was received within the five-minute deadline."
            : e instanceof Error
              ? e.message
              : t.errorNetwork,
        );
    } finally {
      clearTimeout(timeout);
      if (run === generation.current) setBusy(false);
    }
  }
  const findings: Finding[] = demo
    ? [
        {
          type: "visual_review_signal",
          timecode_sec: 34,
          description: t.syntheticObservation,
          rule_id: "CR-001",
          confidence: 0.78,
        },
        {
          type: "visual_review_signal",
          timecode_sec: 67,
          description: t.syntheticObservation,
          rule_id: "CR-001",
          confidence: 0.64,
        },
      ]
    : job?.violations || [];
  const active = findings[selected];
  const rule = rules.find((r) => r.id === active?.rule_id) || rules[0];
  const isResult = demo || job?.status === "done";
  const inProgress = busy || job?.status === "processing";
  function seek(sec: number) {
    setCurrent(sec);
    if (video.current) video.current.currentTime = sec;
  }
  function play() {
    if (demo) setPlaying((s) => !s);
    else if (video.current) {
      if (video.current.paused)
        void video.current
          .play()
          .catch(() =>
            setError(
              "This browser cannot play this MOV codec. Use the evidence frames or a compatible browser.",
            ),
          );
      else video.current.pause();
    }
  }
  const nav = [
    { id: "review" as const, label: t.video, icon: VideoCamera },
    { id: "rules" as const, label: t.rules, icon: BookOpen },
    { id: "system" as const, label: t.system, icon: SlidersHorizontal },
  ];
  return (
    <div className="app">
      <a className="skip-link" href="#content">
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setPage("review");
          }}
          aria-label="Cash Review home"
        >
          <span className="brand-mark">
            <i />
            <i />
            <i />
          </span>
          <span>
            cash<span className="brand-light">review</span>
            <small>Evidence workspace</small>
          </span>
        </a>
        <div className="workspace-switch">
          <div className="workspace-icon">CR</div>
          <div>
            <strong>Cash Review</strong>
            <span>Datathon workspace</span>
          </div>
          <CaretRight size={14} />
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav aria-label={t.workspace}>
          {nav.map((n) => (
            <button
              key={n.id}
              className={`nav-item ${page === n.id ? "active" : ""}`}
              onClick={() => setPage(n.id)}
              aria-current={page === n.id ? "page" : undefined}
            >
              <n.icon size={21} weight={page === n.id ? "fill" : "regular"} />
              <span>{n.label}</span>
              {n.id === "review" && <span className="nav-key">01</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={24} />
            <strong>{t.private}</strong>
            <p>{t.privateText}</p>
            <span>
              <i className="status-dot" />
              {t.noCloud}
            </span>
          </div>
          <div className="partner">
            <span>CASE PARTNER</span>
            <strong>
              forte<span>bank</span>
              <span className="partner-dot">.</span>
            </strong>
          </div>
          <div className="sidebar-footer">
            <span className="avatar">CR</span>
            <div>
              <strong>Team workspace</strong>
              <span>Local environment</span>
            </div>
            <LockKey size={15} />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            {t.workspace}
            <CaretRight size={12} />
            <strong>{nav.find((n) => n.id === page)?.label}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`health-pill ${ready ? "healthy" : ""}`}>
              <i className="status-dot" />
              {!health && !healthError
                ? t.checking
                : ready
                  ? t.available
                  : t.unavailable}
            </span>
            <button
              className="language-button"
              onClick={() => setLang((l) => (l === "en" ? "ru" : "en"))}
              aria-label={t.language}
            >
              <Globe size={17} />
              {lang === "en" ? "EN" : "RU"}
            </button>
          </div>
        </header>
        <main id="content">
          <div className="page-topline">
            <span className="case-tag">
              <span className="mini-mark" />
              {t.case}
            </span>
            <span className="local-tag">
              <HardDrives size={14} />
              {t.local}
            </span>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              <WarningCircle size={20} />
              <span>{error}</span>
              <button onClick={() => setError("")} aria-label={t.dismissError}>
                <X size={18} />
              </button>
            </div>
          )}
          {page === "review" ? (
            <>
              <div className="page-heading">
                <div>
                  <h1>{demo ? t.previewMode : isResult ? t.done : t.title}</h1>
                  <p>
                    {isResult
                      ? demo
                        ? t.previewNotice
                        : `${file?.name || ""} · ${fmtTime(elapsed)}`
                      : t.subtitle}
                  </p>
                </div>
                {(file || demo || job) && (
                  <button
                    className="button secondary new-review"
                    onClick={reset}
                  >
                    <Plus size={17} />
                    {t.new}
                  </button>
                )}
              </div>
              {demo && (
                <div className="demo-banner">
                  <Eye size={18} />
                  <strong>{t.previewMode}</strong>
                  <span>{t.previewNotice}</span>
                  <button onClick={reset}>
                    {t.exitPreview}
                    <X size={15} />
                  </button>
                </div>
              )}
              {!file && !demo && !job ? (
                <>
                  <div className="start-grid">
                    <section
                      className={`upload-panel ${drag ? "dragging" : ""}`}
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
                      <div className="upload-graphic">
                        <div className="graphic-orbit orbit-one" />
                        <div className="graphic-orbit orbit-two" />
                        <div className="video-file">
                          <FileVideo size={39} weight="duotone" />
                          <span>.MOV</span>
                          <div className="file-lines">
                            <i />
                            <i />
                          </div>
                        </div>
                        <div className="upload-plus">
                          <Plus size={16} />
                        </div>
                      </div>
                      <h2>{t.upload}</h2>
                      <p>{t.uploadText}</p>
                      <button
                        className="button primary"
                        onClick={() => input.current?.click()}
                      >
                        <CloudArrowUp size={20} />
                        {t.choose}
                      </button>
                      <span className="file-requirements">{t.format}</span>
                      <div className="upload-security">
                        <LockKey size={13} />
                        {t.zero}
                      </div>
                    </section>
                    <aside className="intro-rail">
                      <section className="pipeline-panel">
                        <div className="section-caption">
                          <span>{t.pipeline}</span>
                          <span className="version">v0.1</span>
                        </div>
                        <div className="pipeline-visual">
                          <div>
                            <FileVideo size={23} />
                          </div>
                          <span />
                          <div className="pipeline-cpu">
                            <Cpu size={24} />
                          </div>
                          <span />
                          <div>
                            <CheckCircle size={23} />
                          </div>
                        </div>
                        <h3>{t.device}</h3>
                        <p>{t.step2Text}</p>
                        <ul className="capability-list">
                          {[t.noCloud, t.identity, t.evidence].map((x) => (
                            <li key={x}>
                              <Check size={15} />
                              {x}
                            </li>
                          ))}
                        </ul>
                        <div className={`model-state ${ready ? "ready" : ""}`}>
                          <i className="status-dot" />
                          <span>{ready ? t.available : t.unavailable}</span>
                          <button
                            onClick={() => setPage("system")}
                            aria-label={t.technical}
                          >
                            <ArrowUpRightIcon />
                          </button>
                        </div>
                      </section>
                      <button
                        className="demo-card"
                        onClick={() => {
                          reset();
                          setDemo(true);
                          setCurrent(34);
                        }}
                      >
                        <span className="demo-play">
                          <Play size={18} weight="fill" />
                        </span>
                        <span>
                          <strong>{t.preview}</strong>
                          <small>{t.previewText}</small>
                        </span>
                        <ArrowRight size={19} />
                      </button>
                    </aside>
                  </div>
                  <section className="how-section">
                    <h2>{t.how}</h2>
                    <div className="steps">
                      {[
                        {
                          title: t.step1,
                          text: t.step1Text,
                          icon: CloudArrowUp,
                        },
                        { title: t.step2, text: t.step2Text, icon: Cpu },
                        { title: t.step3, text: t.step3Text, icon: Eye },
                      ].map((s, i) => (
                        <div className="step" key={s.title}>
                          <span className="step-number">0{i + 1}</span>
                          <div>
                            <h3>{s.title}</h3>
                            <p>{s.text}</p>
                          </div>
                          <s.icon size={22} />
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              ) : (
                <div
                  className={`review-grid ${isResult ? "with-results" : ""}`}
                >
                  <section className="media-column">
                    {isResult && (
                      <DecisionComparison
                        lang={lang}
                        verdict={demo ? "violation" : job?.verdict}
                        reference={job?.sponsor_reference}
                        demo={demo}
                      />
                    )}
                    <div className="media-panel">
                      <div className="panel-header">
                        <span>
                          <FileVideo size={18} />
                          {demo ? "Synthetic desk scene" : file?.name}
                        </span>
                        <span className="media-meta">
                          {demo
                            ? "01:30"
                            : file
                              ? `${(file.size / 1024 / 1024).toFixed(1)} MB`
                              : ""}
                        </span>
                      </div>
                      <div className="video-stage" ref={player}>
                        {demo ? (
                          <SyntheticScene active={playing} />
                        ) : (
                          <video
                            ref={video}
                            src={videoUrl}
                            preload="metadata"
                            onLoadedMetadata={(e) =>
                              setDuration(e.currentTarget.duration)
                            }
                            onTimeUpdate={(e) =>
                              setCurrent(e.currentTarget.currentTime)
                            }
                            onPlay={() => setPlaying(true)}
                            onPause={() => setPlaying(false)}
                            playsInline
                            controls={false}
                          />
                        )}
                        <span className="camera-tag">
                          <span />
                          {demo ? "CAM PREVIEW" : "SOURCE VIDEO"}
                        </span>
                        {inProgress && (
                          <div className="processing-overlay">
                            <CircleNotch className="spin" size={35} />
                            <strong>{busy ? t.uploading : t.processing}</strong>
                            <span>{fmtTime(elapsed)} / 05:00</span>
                            <div className="progress-track">
                              <i
                                style={{
                                  width: `${Math.max(3, job?.progress || 0)}%`,
                                }}
                              />
                            </div>
                            <small>{job?.stage || t.step2Text}</small>
                          </div>
                        )}
                      </div>
                      <div className="player-controls">
                        <button
                          aria-label={playing ? t.pause : t.play}
                          onClick={play}
                        >
                          {playing ? (
                            <Pause size={20} weight="fill" />
                          ) : (
                            <Play size={20} weight="fill" />
                          )}
                        </button>
                        <span>
                          {fmtTime(current)}
                          <i>/</i>
                          {fmtTime(duration)}
                        </span>
                        <input
                          type="range"
                          min="0"
                          max={Number.isFinite(duration) ? duration : 90}
                          step="0.1"
                          value={current}
                          onChange={(e) => seek(Number(e.target.value))}
                          aria-label="Video position"
                        />
                        <button
                          aria-label={t.fullscreen}
                          onClick={() =>
                            void player.current?.requestFullscreen?.()
                          }
                        >
                          <ArrowsOut size={18} />
                        </button>
                      </div>
                    </div>
                    {isResult && (
                      <section className="timeline-panel">
                        <div className="section-caption">
                          <span>{t.findings}</span>
                          <small>
                            {findings.length} {t.reviewSignals}
                          </small>
                        </div>
                        <div className="timeline-track">
                          <div
                            className="timeline-playhead"
                            style={{
                              left: `${Math.min((current / duration) * 100, 100)}%`,
                            }}
                          />
                          {findings.map((f, i) => (
                            <button
                              key={i}
                              className={`timeline-marker ${i === selected ? "selected" : ""}`}
                              style={{
                                left: `${Math.min((f.timecode_sec / duration) * 100, 98)}%`,
                              }}
                              onClick={() => {
                                setSelected(i);
                                seek(f.timecode_sec);
                              }}
                              aria-label={`${t.seek} ${fmtTime(f.timecode_sec)}`}
                            >
                              <span>{fmtTime(f.timecode_sec)}</span>
                            </button>
                          ))}
                        </div>
                        <div className="timeline-labels">
                          <span>00:00</span>
                          <span>{fmtTime(duration / 2)}</span>
                          <span>{fmtTime(duration)}</span>
                        </div>
                      </section>
                    )}
                    {!isResult && !inProgress && (
                      <div className="analyze-footer">
                        <div>
                          <strong>{t.selected}</strong>
                          <span>{t.format}</span>
                        </div>
                        <button
                          className="button primary"
                          disabled={!ready}
                          onClick={analyze}
                        >
                          {t.analyze}
                          <ArrowRight size={18} />
                        </button>
                      </div>
                    )}
                    {!ready && !isResult && !inProgress && (
                      <div className="inline-note">
                        <Info size={19} />
                        <span>{t.readyText}</span>
                        <button onClick={() => setPage("system")}>
                          {t.technical}
                          <ArrowRight size={15} />
                        </button>
                      </div>
                    )}
                    {inProgress && (
                      <p className="tab-notice">
                        <LockKey size={15} />
                        {t.processingText}
                      </p>
                    )}
                    {job?.status === "failed" && (
                      <div className="failure-panel" role="alert">
                        <WarningCircle size={28} />
                        <h2>{t.failed}</h2>
                        <p>
                          {typeof job.error === "string"
                            ? job.error
                            : job.error?.message ||
                              "The worker returned an explicit failure. Check the local server logs."}
                        </p>
                        <button
                          className="button secondary"
                          onClick={() => {
                            setJob(null);
                            setError("");
                          }}
                        >
                          {t.retry}
                        </button>
                      </div>
                    )}
                    {active && (
                      <section className="evidence-panel">
                        <div className="section-caption">
                          <span>{t.evidenceFrames}</span>
                          <span>{fmtTime(active.timecode_sec)}</span>
                        </div>
                        <div className="evidence-grid">
                          {demo
                            ? [0, 1, 2].map((_, i) => (
                                <button
                                  key={i}
                                  className="evidence-thumb"
                                  onClick={() =>
                                    seek(active.timecode_sec + i - 1)
                                  }
                                >
                                  <SyntheticScene />
                                  <span>
                                    {fmtTime(active.timecode_sec + i - 1)}
                                  </span>
                                </button>
                              ))
                            : active.evidence_frames?.map((f, i) => (
                                <button
                                  key={i}
                                  className="evidence-thumb"
                                  onClick={() => seek(f.timestamp_sec)}
                                >
                                  <img
                                    src={`data:image/jpeg;base64,${f.image_base64}`}
                                    alt={`${t.evidence} ${fmtTime(f.timestamp_sec)}`}
                                  />
                                  <span>{fmtTime(f.timestamp_sec)}</span>
                                </button>
                              ))}
                        </div>
                      </section>
                    )}
                  </section>
                  <aside className="findings-column">
                    {isResult ? (
                      <>
                        <div className="findings-header">
                          <h2>{t.findings}</h2>
                          <span>
                            {findings.length.toString().padStart(2, "0")}
                          </span>
                        </div>
                        {findings.length === 0 ? (
                          <div className="empty-findings">
                            <ShieldCheck size={38} />
                            <h3>{t.none}</h3>
                            <p>{t.noneText}</p>
                          </div>
                        ) : (
                          <>
                            <div className="findings-list">
                              {findings.map((f, i) => (
                                <button
                                  key={i}
                                  className={`finding-item ${i === selected ? "active" : ""}`}
                                  onClick={() => {
                                    setSelected(i);
                                    seek(f.timecode_sec);
                                  }}
                                >
                                  <span className="finding-index">
                                    {(i + 1).toString().padStart(2, "0")}
                                  </span>
                                  <span>
                                    <strong>{t.signal}</strong>
                                    <small>
                                      <Clock size={12} />
                                      {fmtTime(f.timecode_sec)}
                                      <span>·</span>
                                      {note[i] === "follow"
                                        ? t.confirmed
                                        : note[i] === "reviewed"
                                          ? t.dismissed
                                          : t.contextOnly}
                                    </small>
                                  </span>
                                  <CaretRight size={16} />
                                </button>
                              ))}
                            </div>
                            {active && (
                              <div className="finding-detail">
                                <div className="finding-detail-top">
                                  <span className="context-badge">
                                    {t.contextOnly}
                                  </span>
                                  <Fingerprint size={19} />
                                </div>
                                <h3>{t.observation}</h3>
                                <p>{active.description}</p>
                                <small className="source-type-note">
                                  {lang === "en"
                                    ? "Event type not specified in source labels."
                                    : "Тип события в исходной разметке не указан."}
                                </small>
                                {typeof active.confidence === "number" && (
                                  <div className="score">
                                    <div>
                                      <span>{t.confidence}</span>
                                      <strong>
                                        {active.confidence.toFixed(2)}
                                      </strong>
                                    </div>
                                    <div className="score-bar">
                                      <i
                                        style={{
                                          width: `${active.confidence * 100}%`,
                                        }}
                                      />
                                    </div>
                                    <small>{t.notProbability}</small>
                                  </div>
                                )}
                                <div className="rule-reference">
                                  <BookOpen size={18} />
                                  <div>
                                    <strong>{t.context}</strong>
                                    <p>
                                      {demo
                                        ? t.syntheticRule
                                        : rule?.title ||
                                          active.rule_id ||
                                          t.contextOnly}
                                    </p>
                                    <button onClick={() => setPage("rules")}>
                                      {t.learn}
                                      <ArrowRight size={14} />
                                    </button>
                                  </div>
                                </div>
                                <div className="reviewer-decision">
                                  <h3>{t.decision}</h3>
                                  <p>{t.decisionText}</p>
                                  <div className="decision-actions">
                                    <button
                                      className={`button small ${note[selected] === "follow" ? "primary" : "secondary"}`}
                                      onClick={() =>
                                        setNote((n) => ({
                                          ...n,
                                          [selected]: "follow",
                                        }))
                                      }
                                    >
                                      <Eye size={16} />
                                      {note[selected] === "follow"
                                        ? t.confirmed
                                        : t.confirm}
                                    </button>
                                    <button
                                      className="text-button"
                                      onClick={() =>
                                        setNote((n) => ({
                                          ...n,
                                          [selected]: "reviewed",
                                        }))
                                      }
                                    >
                                      <Check size={16} />
                                      {note[selected] === "reviewed"
                                        ? t.dismissed
                                        : t.dismiss}
                                    </button>
                                  </div>
                                  <small>{t.reviewed}</small>
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </>
                    ) : (
                      <section className="pipeline-panel compact">
                        <Cpu size={30} />
                        <h3>{t.device}</h3>
                        <p>{t.step2Text}</p>
                        <ul className="capability-list">
                          {[t.noCloud, t.identity, t.evidence].map((x) => (
                            <li key={x}>
                              <Check size={15} />
                              {x}
                            </li>
                          ))}
                        </ul>
                      </section>
                    )}
                  </aside>
                </div>
              )}
              <div className="baseline-note">
                <Info size={18} />
                <div>
                  <strong>{t.coverage}</strong>
                  <p>{t.coverageText}</p>
                </div>
              </div>
              <div className="review-boundary">
                <div className="boundary-icon">
                  <ShieldCheck size={23} />
                </div>
                <div>
                  <strong>{t.human}</strong>
                  <p>{t.humanText}</p>
                </div>
                <span>HUMAN IN THE LOOP</span>
              </div>
            </>
          ) : page === "rules" ? (
            <>
              <div className="page-heading">
                <div>
                  <h1>{t.libraryTitle}</h1>
                  <p>{t.librarySubtitle}</p>
                </div>
              </div>
              <div className="rules-layout">
                <div>
                  {rulesLoading ? (
                    <div className="placeholder-panel">
                      <CircleNotch className="spin" size={26} />
                      {t.loadingRules}
                    </div>
                  ) : !rules.length ? (
                    <div className="placeholder-panel">
                      <BookOpen size={30} />
                      <p>{t.noRules}</p>
                    </div>
                  ) : (
                    rules.map((r) => (
                      <article className="rule-card" key={r.id}>
                        <div className="rule-card-top">
                          <span className="rule-id">{r.id}</span>
                          <span className="context-badge">
                            {r.enabled_for_legal_claim
                              ? t.legal
                              : t.contextOnly}
                          </span>
                        </div>
                        <h2>{r.title}</h2>
                        <span className="rule-issuer">
                          {r.issuer}
                          {r.section ? ` · ${r.section}` : ""}
                        </span>
                        <p>{r.summary}</p>
                        <div className="applicability">
                          <strong>{t.context}</strong>
                          <p>{r.applicability}</p>
                        </div>
                        {r.limitations && (
                          <p className="rule-limitations">
                            <Info size={17} />
                            {Array.isArray(r.limitations)
                              ? r.limitations.join(" ")
                              : r.limitations}
                          </p>
                        )}
                        {r.url && /^https:\/\//.test(r.url) && (
                          <a
                            className="source-link"
                            href={r.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {t.source}
                            <ArrowSquareOut size={16} />
                          </a>
                        )}
                      </article>
                    ))
                  )}
                </div>
                <aside className="coverage-panel">
                  <BookOpen size={29} />
                  <h3>{t.coverage}</h3>
                  <p>{t.coverageText}</p>
                  <button
                    className="text-button"
                    onClick={() => setPage("review")}
                  >
                    <ArrowLeft size={16} />
                    {t.video}
                  </button>
                </aside>
              </div>
            </>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <h1>{t.systemTitle}</h1>
                  <p>{t.systemSubtitle}</p>
                </div>
                <button className="button secondary" onClick={refreshHealth}>
                  {t.refresh}
                </button>
              </div>
              <div className="system-grid">
                <section className="system-panel">
                  <div className="section-caption">
                    <span>{t.runtime}</span>
                    <Cpu size={19} />
                  </div>
                  <div className={`runtime-status ${ready ? "ready" : ""}`}>
                    <i className="status-dot" />
                    {ready ? t.available : t.unavailable}
                  </div>
                  <p>{ready ? t.modelText : t.readyText}</p>
                  <div className="runtime-facts">
                    <div>
                      <span>Inference</span>
                      <strong>Local · CPU</strong>
                    </div>
                    <div>
                      <span>Cloud AI</span>
                      <strong>Disabled</strong>
                    </div>
                    <div>
                      <span>Jury authentication</span>
                      <strong>X-API-Key</strong>
                    </div>
                    <div>
                      <span>Model state</span>
                      <strong>
                        {ready ? "Prepared" : "Preparation required"}
                      </strong>
                    </div>
                  </div>
                  {health?.reasons && (
                    <ul className="health-reasons">
                      {health.reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </section>
                <section className="system-panel api-panel">
                  <div className="section-caption">
                    <span>{t.jury}</span>
                    <Code size={20} />
                  </div>
                  <p>{t.juryText}</p>
                  <div className="endpoint">
                    <b>POST</b>
                    <code>/api/v1/analyze</code>
                  </div>
                  <div className="endpoint">
                    <b className="get">GET</b>
                    <code>/api/v1/jobs/&#123;job_id&#125;</code>
                  </div>
                  <pre>
                    {
                      'curl -X POST http://127.0.0.1:8000/api/v1/analyze -H "X-API-Key: $CASH_REVIEW_API_KEY" -F "file=@clip.mov"'
                    }
                  </pre>
                  <div className="api-footnote">
                    <LockKey size={14} />
                    {t.key}
                  </div>
                </section>
              </div>
              <div className="system-features">
                {[
                  { icon: HardDrives, title: t.offline, text: t.offlineText },
                  { icon: Clock, title: t.deadline, text: t.deadlineText },
                  { icon: LockKey, title: t.privacy, text: t.privacyText },
                ].map((x) => (
                  <section key={x.title}>
                    <x.icon size={23} />
                    <h3>{x.title}</h3>
                    <p>{x.text}</p>
                  </section>
                ))}
              </div>
              <div className="setup-note">
                <Info size={23} />
                <div>
                  <h3>{t.setup}</h3>
                  <p>{t.setupText}</p>
                </div>
              </div>
            </>
          )}
          <footer className="page-footer">
            <span>
              Cash Review <i>/</i> {t.case}
            </span>
            <span>
              <LockKey size={12} />
              {t.expires}
            </span>
          </footer>
        </main>
      </div>
      <input
        ref={input}
        className="sr-only"
        type="file"
        accept=".mov,video/quicktime"
        onChange={(e) => choose(e.target.files?.[0])}
        aria-label={t.choose}
      />
    </div>
  );
}
function ArrowUpRightIcon() {
  return <ArrowSquareOut size={16} />;
}

function DecisionComparison({
  lang,
  verdict,
  reference,
  demo,
}: {
  lang: Lang;
  verdict?: "violation" | "no_violation";
  reference?: SponsorReference;
  demo: boolean;
}) {
  const ru = lang === "ru";
  const label = (value?: string | null) =>
    value === "violation"
      ? ru
        ? "Нарушение"
        : "Violation"
      : value === "no_violation"
        ? ru
          ? "Без нарушения"
          : "No violation"
        : ru
          ? "Не предоставлено"
          : "Not provided";
  const generic = ru
    ? "визуальный сигнал, тип не определён"
    : "visual signal, type unclassified";
  return (
    <section
      className="decision-comparison"
      aria-label={
        ru ? "Модель и исходная метка" : "Model and sponsor decisions"
      }
    >
      <div className="model-decision">
        <span>
          <Cpu size={16} />
          {demo
            ? ru
              ? "Иллюстративное решение"
              : "Illustrative decision"
            : ru
              ? "Решение модели"
              : "Model decision"}
        </span>
        <strong>
          {label(verdict)}{" "}
          <small>
            (
            {verdict === "violation"
              ? generic
              : ru
                ? "сигналов не найдено"
                : "no signal found"}
            )
          </small>
        </strong>
        <p>
          {ru
            ? "Экспериментальный прогноз. Проверьте доказательства."
            : "Experimental prediction. Verify the evidence."}
        </p>
      </div>
      <div className="sponsor-decision">
        <span>
          <BookOpen size={16} />
          {ru ? "Исходная метка спонсора" : "Sponsor reference"}
        </span>
        <strong>
          {label(reference?.available ? reference.verdict : null)}
          {reference?.available && (
            <small>
              {" "}
              ({reference.type || (ru ? "тип не указан" : "type not specified")}
              )
            </small>
          )}
        </strong>
        <p>
          {reference?.available
            ? ru
              ? "Оригинальная разметка спонсора. Не влияет на прогноз."
              : "Original sponsor annotation. Does not influence the prediction."
            : ru
              ? "Для этой загрузки исходная метка отсутствует."
              : "No sponsor annotation is available for this upload."}
        </p>
      </div>
    </section>
  );
}
