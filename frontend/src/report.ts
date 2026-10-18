import { automaticDecision, parseHumanReview } from "./contracts.ts";
import type { Finding, HumanReview, Job, Lang } from "./types";

export type ReviewReportOptions = {
  lang: Lang;
  job: Job | null;
  fileName?: string | null;
  demo: boolean;
  demoFindings?: readonly Finding[];
  demoReview?: HumanReview | null;
  generatedAt?: Date;
};

const copy = {
  en: {
    title: "Cash Review — review report",
    synthetic: "SYNTHETIC EXAMPLE — illustrative mode",
    syntheticBoundary:
      "The scene and candidate signals are synthetic. This is an interface example.",
    real: "Completed video review",
    generated: "Generated (UTC)",
    file: "File",
    unknown: "Not reported",
    model: "Model",
    version: "Model version",
    automatic: "Automatic assessment",
    unavailable: "Unavailable — human review required",
    illustrative: "Illustration only",
    concern: "Concern signal",
    clear: "No concern signal",
    qualification:
      "Automatic assessment uses this job's recorded qualification. Unvalidated results require human review.",
    candidates: "Candidate moments",
    generic:
      "Generic visual review signals. Action type is unclassified; timestamps are review anchors, not validated event intervals.",
    none: "No candidate moments were returned. This does not establish that the video is clear.",
    score: "Uncalibrated model score",
    scoreBoundary:
      "Scores are not calibrated probabilities or proof of an action or legal violation.",
    human: "Saved human assessment",
    noReview: "No saved human assessment.",
    source: "Assessment source",
    server: "Saved server receipt",
    local: "Saved browser-only synthetic assessment",
    decision: "Human decision",
    humanConcern: "Concern confirmed by reviewer",
    humanClear: "No concern recorded by reviewer",
    more: "Needs more review",
    scope: "Scope",
    entire: "Entire video",
    candidate: "Candidate",
    savedAt: "Saved (UTC)",
    notes: "Saved reviewer notes",
    noNotes: "No notes",
    provenance:
      "Only the last saved assessment is included. Unsaved editor changes are excluded. Human assessment is separate from the immutable model result.",
    contents:
      "This text report contains no video, evidence images, access token or arbitrary job metadata.",
    incomplete: "A report requires a completed result.",
    invalid:
      "The result cannot be exported because its report fields are invalid.",
  },
  ru: {
    title: "Cash Review — отчёт о проверке",
    synthetic: "СИНТЕТИЧЕСКИЙ ПРИМЕР — иллюстративный режим",
    syntheticBoundary:
      "Сцена и кандидатные сигналы синтетические. Это пример работы интерфейса.",
    real: "Завершённая проверка видео",
    generated: "Отчёт сформирован (UTC)",
    file: "Файл",
    unknown: "Не указано",
    model: "Модель",
    version: "Версия модели",
    automatic: "Автоматическая оценка",
    unavailable: "Недоступна — требуется проверка человеком",
    illustrative: "Только иллюстрация",
    concern: "Сигнал для проверки",
    clear: "Сигнал отсутствия признаков",
    qualification:
      "Автоматическая оценка использует квалификацию модели из метаданных самого задания. Невалидированные результаты требуют проверки человеком.",
    candidates: "Моменты для проверки",
    generic:
      "Общие визуальные сигналы. Тип действия не классифицирован; временные отметки служат ориентирами для просмотра, а не подтверждёнными интервалами события.",
    none: "Кандидатные моменты не возвращены. Это не подтверждает отсутствие признаков на видео.",
    score: "Некалиброванная оценка модели",
    scoreBoundary:
      "Оценки не являются калиброванными вероятностями или доказательством действия либо правового нарушения.",
    human: "Сохранённая оценка человека",
    noReview: "Сохранённой оценки человека нет.",
    source: "Источник оценки",
    server: "Сохранённая серверная запись",
    local: "Сохранённая в браузере оценка синтетического примера",
    decision: "Решение проверяющего",
    humanConcern: "Проверяющий подтвердил признаки",
    humanClear: "Проверяющий не отметил признаков",
    more: "Нужна допроверка",
    scope: "Область решения",
    entire: "Всё видео",
    candidate: "Момент",
    savedAt: "Сохранено (UTC)",
    notes: "Сохранённые заметки проверяющего",
    noNotes: "Заметок нет",
    provenance:
      "Включена только последняя сохранённая оценка. Несохранённые изменения редактора исключены. Оценка человека отделена от неизменяемого результата модели.",
    contents:
      "Текстовый отчёт не содержит видео, кадров свидетельств, токена доступа или произвольных метаданных задания.",
    incomplete: "Для отчёта требуется завершённый результат.",
    invalid: "Отчёт нельзя сформировать: поля результата некорректны.",
  },
};

function sourceTime(seconds: number, message: string): string {
  if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86_400)
    throw new Error(message);
  const milliseconds = Math.round(seconds * 1000);
  const minutes = Math.floor(milliseconds / 60_000);
  const remainder = ((milliseconds % 60_000) / 1000).toFixed(3);
  return `${String(minutes).padStart(2, "0")}:${remainder.padStart(6, "0")}`;
}

function utc(date: Date, message: string): string {
  if (!Number.isFinite(date.getTime())) throw new Error(message);
  return date.toISOString();
}

function modelName(value: unknown, fallback: string): string {
  return typeof value === "string" &&
    value.length <= 120 &&
    /^[\p{L}\p{N}][\p{L}\p{N}_. +()-]*$/u.test(value)
    ? value
    : fallback;
}

/** Pure, local formatter. Never reads a draft, serializes a job, or accesses images. */
export function buildReviewReport({
  lang,
  job,
  fileName,
  demo,
  demoFindings = [],
  demoReview = null,
  generatedAt = new Date(),
}: ReviewReportOptions): string {
  const t = copy[lang];
  if (!demo && job?.status !== "done") throw new Error(t.incomplete);
  const findings = demo ? demoFindings : job?.violations;
  if (!Array.isArray(findings) || findings.length > 1000)
    throw new Error(t.invalid);
  const assessment = demo ? undefined : automaticDecision(job);
  const assessmentText = demo
    ? t.illustrative
    : assessment === "violation"
      ? t.concern
      : assessment === "no_violation"
        ? t.clear
        : t.unavailable;
  const name =
    typeof fileName === "string"
      ? Array.from(fileName.split(/[\\/]/).pop() || "")
          .slice(0, 240)
          .join("")
          .replace(/[\u0000-\u001f\u007f-\u009f]/g, " ")
          .trim()
      : "";
  const lines = [
    t.title,
    demo ? t.synthetic : t.real,
    `${t.generated}: ${utc(generatedAt, t.invalid)}`,
    `${t.file}: ${demo ? t.synthetic : name || t.unknown}`,
  ];
  if (demo) lines.push(t.syntheticBoundary);
  else
    lines.push(
      `${t.model}: ${modelName(job?.metadata?.model_kind, t.unknown)}`,
      `${t.version}: ${modelName(job?.metadata?.model_version, t.unknown)}`,
    );
  lines.push(
    `${t.automatic}: ${assessmentText}`,
    ...(demo ? [] : [t.qualification]),
    "",
    `${t.candidates}: ${findings.length}`,
    t.generic,
  );
  if (!findings.length) lines.push(t.none);
  for (const [index, finding] of findings.entries()) {
    if (!finding || typeof finding.timecode_sec !== "number")
      throw new Error(t.invalid);
    lines.push(`${index + 1}. ${sourceTime(finding.timecode_sec, t.invalid)}`);
    if (finding.confidence != null) {
      if (
        typeof finding.confidence !== "number" ||
        !Number.isFinite(finding.confidence)
      )
        throw new Error(t.invalid);
      lines.push(`   ${t.score}: ${finding.confidence.toFixed(3)}`);
    }
  }
  lines.push(t.scoreBoundary, "", t.human);
  const rawReview = demo ? demoReview : job?.human_review;
  if (!rawReview) lines.push(t.noReview);
  else {
    const review = parseHumanReview(rawReview, t.invalid);
    if (review.event_index !== null && review.event_index >= findings.length)
      throw new Error(t.invalid);
    const decision =
      review.decision === "violation"
        ? t.humanConcern
        : review.decision === "no_violation"
          ? t.humanClear
          : t.more;
    const scope =
      review.event_index === null
        ? t.entire
        : `${t.candidate} ${review.event_index + 1}, ${sourceTime(findings[review.event_index].timecode_sec, t.invalid)}`;
    lines.push(
      `${t.source}: ${demo ? t.local : t.server}`,
      `${t.decision}: ${decision}`,
      `${t.scope}: ${scope}`,
      `${t.savedAt}: ${utc(new Date(review.updated_at * 1000), t.invalid)}`,
      `${t.notes}:`,
      review.notes.replace(/\u0000/g, "") || t.noNotes,
    );
  }
  lines.push("", t.provenance, t.contents);
  return lines.join("\n") + "\n";
}
