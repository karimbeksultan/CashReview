import { useEffect, useRef, useState } from "react";
import {
  CaretLeft,
  CaretRight,
  Check,
  CheckCircle,
  CircleNotch,
  Eye,
  FloppyDisk,
  LockKey,
  MagnifyingGlassMinus,
  MagnifyingGlassPlus,
  Play,
  ShieldCheck,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import type { Copy } from "./copy";
import type {
  Finding,
  FrameSelection,
  HumanReview,
  ReviewInput,
  ReviewDraft,
} from "./types";

export const fmtTime = (value: number) => {
  const s = Number.isFinite(value) ? Math.max(0, value) : 0;
  return `${Math.floor(s / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(s % 60)
    .toString()
    .padStart(2, "0")}`;
};
export const fmtSourceTime = (value: number) => {
  const milliseconds = Number.isFinite(value)
    ? Math.max(0, Math.round(value * 1000))
    : 0;
  const minutes = Math.floor(milliseconds / 60000)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor((milliseconds % 60000) / 1000)
    .toString()
    .padStart(2, "0");
  const fraction =
    (milliseconds % 1000).toString().padStart(3, "0").replace(/0+$/, "") || "0";
  return `${minutes}:${seconds}.${fraction}`;
};
export function SyntheticScene({
  active = false,
  t,
}: {
  active?: boolean;
  t: Copy;
}) {
  return (
    <div
      className={`synthetic-scene ${active ? "scene-active" : ""}`}
      role="img"
      aria-label={t.sceneAlt}
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
        <span>{t.reviewRegion}</span>
      </div>
      <div className="scene-label">{t.sceneLabel}</div>
    </div>
  );
}

export function HumanDecisionPanel({
  t,
  findings,
  review,
  demo,
  onSave,
  draft,
  onDraftChange,
  saving,
}: {
  t: Copy;
  findings: Finding[];
  review?: HumanReview | null;
  demo: boolean;
  onSave: (value: ReviewInput) => Promise<HumanReview>;
  draft: ReviewDraft;
  onDraftChange: (value: ReviewDraft) => void;
  saving: boolean;
}) {
  const { decision, notes, scope, saved } = draft;
  const [error, setError] = useState("");
  const updateDraft = (change: Partial<ReviewDraft>) => {
    onDraftChange({ ...draft, ...change, saved: false });
    setError("");
  };
  async function save() {
    if (!decision) {
      setError(t.decisionRequired);
      return;
    }
    setError("");
    try {
      await onSave({
        decision,
        notes,
        event_index: scope === "all" ? null : Number(scope),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : t.reviewError);
    }
  }
  const choices = [
    { value: "violation" as const, label: t.confirm, icon: WarningCircle },
    { value: "no_violation" as const, label: t.clear, icon: ShieldCheck },
    { value: "needs_review" as const, label: t.more, icon: Eye },
  ];
  return (
    <section className="human-panel" aria-labelledby="human-title">
      <div className="human-panel-heading">
        <span className="human-avatar">
          <Eye size={24} aria-hidden="true" />
        </span>
        <div>
          <h2 id="human-title">{t.human}</h2>
          <span>{review || saved ? t.savedAssessment : t.notReviewed}</span>
        </div>
      </div>
      <p>{t.humanHint}</p>
      <div className="decision-options" role="group" aria-label={t.human}>
        {choices.map((choice) => (
          <button
            key={choice.value}
            className={`decision-option ${decision === choice.value ? "chosen" : ""} decision-${choice.value}`}
            aria-pressed={decision === choice.value}
            disabled={saving}
            onClick={() => {
              updateDraft({ decision: choice.value });
            }}
          >
            <choice.icon size={22} aria-hidden="true" />
            <span>{choice.label}</span>
            {decision === choice.value && (
              <Check size={19} weight="bold" aria-hidden="true" />
            )}
          </button>
        ))}
      </div>
      <label className="field-label" htmlFor="review-scope">
        {t.scope}
      </label>
      <select
        id="review-scope"
        value={scope}
        disabled={saving}
        onChange={(e) => {
          updateDraft({ scope: e.target.value });
        }}
      >
        <option value="all">{t.entire}</option>
        {findings.map((finding, index) => (
          <option key={index} value={index}>
            {t.candidate} {index + 1} — {fmtSourceTime(finding.timecode_sec)}
          </option>
        ))}
      </select>
      <label className="field-label notes-label" htmlFor="review-notes">
        {t.notes}
      </label>
      <textarea
        id="review-notes"
        value={notes}
        disabled={saving}
        maxLength={4000}
        rows={5}
        placeholder={t.notesHint}
        onChange={(e) => {
          updateDraft({ notes: e.target.value });
        }}
      />
      <span className="character-count">
        {notes.length.toLocaleString()} / 4,000
      </span>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <button
        className="button primary save-decision"
        onClick={() => void save()}
        disabled={saving || !decision}
      >
        {saving ? (
          <CircleNotch size={20} className="spin" />
        ) : saved ? (
          <CheckCircle size={20} />
        ) : (
          <FloppyDisk size={20} />
        )}{" "}
        {saving ? t.saving : saved ? t.saved : t.save}
      </button>
      <div className="save-state" role="status">
        {saved ? (demo ? t.savedLocal : t.saved) : decision ? t.unsaved : ""}
      </div>
      <p className="human-boundary">
        <LockKey size={16} aria-hidden="true" />
        {demo ? t.demoBoundary : t.humanBoundary}
      </p>
      <small className="scope-note">{t.scopeNote}</small>
    </section>
  );
}

export function EvidenceDialog({
  selection,
  findings,
  demo,
  t,
  onClose,
  onChange,
  onSeek,
}: {
  selection: FrameSelection | null;
  findings: Finding[];
  demo: boolean;
  t: Copy;
  onClose: () => void;
  onChange: (value: FrameSelection) => void;
  onSeek: (seconds: number) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const frames = findings.flatMap((finding, event) =>
    (finding.evidence_frames || []).map((frame, index) => ({
      ...frame,
      event,
      frame: index,
    })),
  );
  const activeIndex = selection
    ? frames.findIndex(
        (frame) =>
          frame.event === selection.event && frame.frame === selection.frame,
      )
    : -1;
  const active = frames[activeIndex];
  useEffect(() => {
    if (selection && dialog.current && !dialog.current.open) {
      returnFocus.current = document.activeElement as HTMLElement;
      dialog.current.showModal();
      document.body.style.overflow = "hidden";
    } else if (!selection && dialog.current?.open) {
      dialog.current.close();
      document.body.style.overflow = "";
      returnFocus.current?.focus();
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [Boolean(selection)]);
  useEffect(() => {
    setZoom(1);
  }, [activeIndex]);
  useEffect(() => {
    const element = canvas.current;
    if (element) {
      element.scrollLeft = (element.scrollWidth - element.clientWidth) / 2;
      element.scrollTop = (element.scrollHeight - element.clientHeight) / 2;
    }
  }, [zoom]);
  function move(offset: number) {
    const frame =
      frames[(activeIndex + offset + frames.length) % frames.length];
    if (frame) onChange({ event: frame.event, frame: frame.frame });
  }
  return (
    <dialog
      className="evidence-dialog"
      ref={dialog}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === dialog.current) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          move(-1);
        }
        if (e.key === "ArrowRight") {
          e.preventDefault();
          move(1);
        }
      }}
      aria-labelledby="frame-dialog-title"
    >
      <div className="lightbox-shell">
        <header className="lightbox-header">
          <div>
            <span>{t.evidence}</span>
            <h2 id="frame-dialog-title">
              {t.candidate} {(selection?.event ?? 0) + 1} <i>/</i>{" "}
              {fmtSourceTime(active?.timestamp_sec || 0)}
            </h2>
          </div>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label={t.close}
          >
            <X size={26} />
          </button>
        </header>
        <div
          ref={canvas}
          className={`lightbox-canvas ${zoom > 1 ? "is-zoomed" : ""}`}
        >
          <div
            className="lightbox-image"
            style={{ width: `${zoom * 100}%`, height: `${zoom * 100}%` }}
          >
            {demo ? (
              <SyntheticScene t={t} />
            ) : active ? (
              <img
                src={`data:image/jpeg;base64,${active.image_base64}`}
                alt={`${t.evidence} ${fmtSourceTime(active.timestamp_sec)}`}
              />
            ) : null}
          </div>
        </div>
        <footer className="lightbox-footer">
          <div className="frame-navigation">
            <button
              className="icon-button"
              onClick={() => move(-1)}
              aria-label={t.previous}
              disabled={frames.length < 2}
            >
              <CaretLeft size={24} />
            </button>
            <span>
              {t.frame} {activeIndex + 1} {t.of} {frames.length}
            </span>
            <button
              className="icon-button"
              onClick={() => move(1)}
              aria-label={t.next}
              disabled={frames.length < 2}
            >
              <CaretRight size={24} />
            </button>
          </div>
          <div className="zoom-controls">
            <button
              className="icon-button"
              onClick={() => setZoom((value) => Math.max(1, value - 0.5))}
              aria-label={t.zoomOut}
              disabled={zoom === 1}
            >
              <MagnifyingGlassMinus size={22} />
            </button>
            <button className="fit-button" onClick={() => setZoom(1)}>
              {zoom === 1 ? t.fit : `${Math.round(zoom * 100)}%`}
            </button>
            <button
              className="icon-button"
              onClick={() => setZoom((value) => Math.min(3, value + 0.5))}
              aria-label={t.zoomIn}
              disabled={zoom === 3}
            >
              <MagnifyingGlassPlus size={22} />
            </button>
          </div>
          <button
            className="button primary"
            onClick={() => {
              if (active) onSeek(active.timestamp_sec);
              onClose();
            }}
          >
            <Play size={18} />
            {t.jump}
          </button>
        </footer>
      </div>
    </dialog>
  );
}
