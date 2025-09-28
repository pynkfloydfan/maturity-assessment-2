import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useParams } from "react-router-dom";
import { GaugeIcon, ListChecksIcon, SaveIcon } from "../icons";
import { useThemeTopics } from "../hooks/useThemeTopics";
import { useSessionContext } from "../context/SessionContext";
import { useDimensions } from "../hooks/useDimensions";
import { useThemes } from "../hooks/useThemes";
import { apiPost } from "../api/client";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";
import type { RatingScaleItem, RatingUpdatePayload, TopicDetail } from "../api/types";

const CMMI_LEVEL_LABELS: Record<number, string> = {
  1: "Initial",
  2: "Managed",
  3: "Defined",
  4: "Quantitatively Managed",
  5: "Optimizing",
};

type TopicSnapshot = Pick<RatingUpdatePayload, "rating_level" | "is_na" | "comment">;

export default function TopicsPage() {
  const params = useParams<{ dimensionId: string; themeId: string }>();
  const dimensionId = params.dimensionId ? Number.parseInt(params.dimensionId, 10) : NaN;
  const themeId = params.themeId ? Number.parseInt(params.themeId, 10) : NaN;
  const { activeSessionId } = useSessionContext();
  const { dimensions } = useDimensions();
  const { data, loading, error, refresh } = useThemeTopics({
    themeId: Number.isNaN(themeId) ? null : themeId,
    sessionId: activeSessionId,
  });
  const { themes: dimensionThemes } = useThemes(Number.isNaN(dimensionId) ? null : dimensionId);

  const [initialState, setInitialState] = useState<Record<number, TopicSnapshot>>({});
  const [topicState, setTopicState] = useState<Record<number, TopicSnapshot>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const buildSnapshot = useCallback((topics: TopicDetail[]): Record<number, TopicSnapshot> => {
    return topics.reduce<Record<number, TopicSnapshot>>((acc, topic) => {
      acc[topic.id] = {
        rating_level: topic.is_na ? null : topic.rating_level ?? null,
        is_na: topic.is_na,
        comment: topic.comment ?? "",
      };
      return acc;
    }, {});
  }, []);

  useEffect(() => {
    if (!data) return;
    const snapshot = buildSnapshot(data.topics);
    const clone = Object.fromEntries(
      Object.entries(snapshot).map(([key, value]) => [Number(key), { ...value }]),
    ) as Record<number, TopicSnapshot>;
    setInitialState(snapshot);
    setTopicState(clone);
  }, [data, buildSnapshot]);

  const updateTopicState = useCallback((topicId: number, updates: Partial<TopicSnapshot>) => {
    setTopicState((prev) => ({
      ...prev,
      [topicId]: {
        rating_level: prev[topicId]?.rating_level ?? null,
        is_na: prev[topicId]?.is_na ?? false,
        comment: prev[topicId]?.comment ?? "",
        ...updates,
      },
    }));
    setSaveError(null);
    setSaveMessage(null);
  }, []);

  const isTopicDirty = useCallback(
    (topicId: number) => {
      const initial = initialState[topicId];
      const current = topicState[topicId];
      if (!current) return false;
      if (!initial) return true;
      return (
        (initial.rating_level ?? null) !== (current.rating_level ?? null) ||
        initial.is_na !== current.is_na ||
        (initial.comment ?? "") !== (current.comment ?? "")
      );
    },
    [initialState, topicState],
  );

  const hasChanges = useMemo(() => {
    if (!data) return false;
    return data.topics.some((topic) => isTopicDirty(topic.id));
  }, [data, isTopicDirty]);

  const handleSave = useCallback(async () => {
    if (!activeSessionId || !data) return;
    const updates: RatingUpdatePayload[] = data.topics
      .filter((topic) => isTopicDirty(topic.id))
      .map((topic) => {
        const current = topicState[topic.id] ?? initialState[topic.id];
        return {
          topic_id: topic.id,
          rating_level: current?.is_na ? null : current?.rating_level ?? null,
          is_na: current?.is_na ?? false,
          comment: current?.comment?.trim() ? current?.comment.trim() : null,
        };
      });

    if (updates.length === 0) return;

    try {
      setSaving(true);
      setSaveError(null);
      await apiPost(`/api/sessions/${activeSessionId}/ratings`, {
        session_id: activeSessionId,
        updates,
      });
      await refresh();
      setSaveMessage("Ratings saved");
      if (typeof window !== "undefined") {
        window.setTimeout(() => setSaveMessage(null), 4000);
      }
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save ratings");
    } finally {
      setSaving(false);
    }
  }, [activeSessionId, data, isTopicDirty, topicState, refresh]);

  const dimension = dimensions.find((item) => item.id === dimensionId);
  const theme = data?.theme;
  const breadcrumbItems = useMemo(() => {
    const trail: { label: string; path?: string }[] = [{ label: "Dimensions", path: "/" }];
    if (dimension) {
      trail.push({ label: dimension.name, path: `/dimensions/${dimension.id}/themes` });
    }
    if (theme) {
      trail.push({ label: theme.name });
    }
    return trail;
  }, [dimension, theme]);
  usePageBreadcrumb(breadcrumbItems);

  if (!dimensionId || Number.isNaN(dimensionId) || !themeId || Number.isNaN(themeId)) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10 text-[#61758a]">
        Invalid theme path. Please navigate from the dimensions view.
      </div>
    );
  }

  if (!activeSessionId) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-10 text-center">
          <h2 className="mb-2 text-xl font-semibold text-[#121417]">Select a session</h2>
          <p className="text-[#61758a]">
            Choose or create an assessment session from the header before rating topics.
          </p>
        </div>
      </div>
    );
  }

  const topicCount = data?.topics.length ?? 0;
  const statusText = saving ? "Saving…" : hasChanges ? "Unsaved changes" : "Up to date";
  const ratingMetrics = useMemo(() => {
    if (!data || !data.topics.length) {
      return { total: data?.topics.length ?? 0, rated: 0, coverage: 0, average: null as number | null };
    }
    let rated = 0;
    let sum = 0;
    data.topics.forEach((topic) => {
      if (topic.is_na) {
        return;
      }
      if (topic.rating_level == null) {
        return;
      }
      rated += 1;
      sum += topic.rating_level;
    });
    const coverage = data.topics.length ? Math.round((rated / data.topics.length) * 100) : 0;
    const average = rated ? sum / rated : null;
    return { total: data.topics.length, rated, coverage, average };
  }, [data]);
  const coverageDisplay = loading || ratingMetrics.total === 0 ? "–" : `${ratingMetrics.coverage}%`;
  const averageDisplay = loading || ratingMetrics.average == null ? "–" : ratingMetrics.average.toFixed(1);

  const themeDescription = useMemo(() => {
    if (!theme) {
      return null;
    }
    const primary = theme.description?.trim();
    if (primary) {
      return primary;
    }
    const fallback = dimensionThemes
      .find((item) => item.id === theme.id)
      ?.description?.trim();
    return fallback ?? null;
  }, [theme, dimensionThemes]);

  const dimensionDescription = dimension?.description?.trim() ?? null;

  const guidanceSummary = (() => {
    if (!data?.generic_guidance?.length) {
      return null;
    }
    const preferred = data.generic_guidance.find((entry) => entry.level === 3);
    const candidate = (preferred ?? data.generic_guidance[0])?.description?.trim();
    return candidate || null;
  })();

  const heroDescriptionText =
    themeDescription ?? guidanceSummary ?? dimensionDescription ??
    "Assess supporting topics for this theme and capture structured ratings.";

  const heroDescriptionParagraphs = useMemo(() => {
    return heroDescriptionText
      .split(/\r?\n+/)
      .map((segment) => segment.trim())
      .filter(Boolean);
  }, [heroDescriptionText]);

  return (
    <div className="page-section">
      {theme && (
        <div className="page-hero">
          <div className="pill">{dimension ? dimension.name : "Theme"}</div>
          <div>
            <h1>{theme.name}</h1>
            {heroDescriptionParagraphs.map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
          <div className="status-card">
            <div className="status-item">
              <span className="status-item__icon">
                <ListChecksIcon />
              </span>
              <div className="status-label">Topics</div>
              <div className="status-value">{loading ? "–" : topicCount}</div>
            </div>
            <div className="status-item status-item--metrics">
              <span className="status-item__icon">
                <GaugeIcon />
              </span>
              <div>
                <div className="status-label">Coverage &amp; Score</div>
                <div className="status-value">{coverageDisplay} · {averageDisplay}</div>
                <div className="status-note">Coverage · Avg score</div>
              </div>
            </div>
            <div className="status-item status-item--actions">
              <div className="status-item__header">
                <span className="status-item__icon">
                  <SaveIcon />
                </span>
                <div className="status-label">Status</div>
                <div
                  className={`status-value${hasChanges && !saving ? " status-value--dirty" : ""}`}
                >
                  {statusText}
                </div>
              </div>
              <button
                type="button"
                className={`${hasChanges && !saving ? "btn-primary" : "btn-secondary"} status-action`}
                onClick={handleSave}
                disabled={!hasChanges || saving}
              >
                {saving ? "Saving…" : (
                  <>
                    <SaveIcon />
                    Save changes
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className={`topic-layout${data?.generic_guidance?.length ? "" : " topic-layout--single"}`}>
        <div className="topic-main">
          <div className="page-toolbar">
            <div className="page-toolbar__summary">
              Session #{activeSessionId} · {topicCount} topics
            </div>
            <div className="page-toolbar__actions">
              {saveError && <span className="text-sm text-red-600">{saveError}</span>}
              {saveMessage && <span className="text-sm text-green-600">{saveMessage}</span>}
            </div>
          </div>

          {loading && <div className="text-sm text-[#61758a]">Loading topics…</div>}
          {error && <div className="text-sm text-red-600">{error}</div>}
          {!loading && !error && data && data.topics.length === 0 && (
            <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-8 text-center text-[#61758a]">
              No topics were found for this theme.
            </div>
          )}
          {!loading && !error && data && data.topics.length > 0 && (
            <section className="flex flex-col gap-4">
              {data.topics.map((topic) => {
                const current = topicState[topic.id] ?? initialState[topic.id] ?? {
                  rating_level: topic.is_na ? null : topic.rating_level ?? null,
                  is_na: topic.is_na,
                  comment: topic.comment ?? "",
                };
                const dirty = isTopicDirty(topic.id);
                return (
                  <TopicAssessmentCard
                    key={topic.id}
                    topic={topic}
                    ratingScale={data.rating_scale}
                    state={current}
                    updateState={updateTopicState}
                    dirty={dirty}
                  />
                );
              })}
            </section>
          )}
        </div>

        {data?.generic_guidance?.length ? (
          <aside className="topic-sidebar">
            <div className="topic-sidebar__card">
              <h2 className="topic-sidebar__title">Theme-level guidance</h2>
              <ul className="topic-sidebar__list">
                {data.generic_guidance.map((item) => {
                  const levelLabel = CMMI_LEVEL_LABELS[item.level];
                  const heading = levelLabel
                    ? `Level ${item.level} - ${levelLabel}`
                    : `Level ${item.level}`;
                  return (
                    <li key={item.level} className="topic-sidebar__item">
                      <span className="topic-sidebar__level">{heading}</span>
                      <span className="topic-sidebar__copy">{item.description}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </aside>
        ) : null}
      </div>
    </div>
  );
}

interface TopicAssessmentCardProps {
  topic: TopicDetail;
  ratingScale: RatingScaleItem[];
  state: TopicSnapshot;
  dirty: boolean;
  updateState: (topicId: number, updates: Partial<TopicSnapshot>) => void;
}

function TopicAssessmentCard({ topic, ratingScale, state, updateState, dirty }: TopicAssessmentCardProps) {
  const sortedScale = [...ratingScale].sort((a, b) => a.level - b.level);

  const handleSelect = (level: number | null) => {
    if (level === null) {
      updateState(topic.id, { is_na: true, rating_level: null });
    } else {
      updateState(topic.id, { is_na: false, rating_level: level });
    }
  };

  const handleCommentChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    updateState(topic.id, { comment: event.target.value });
  };

  return (
    <article className="topic-card" data-dirty={dirty ? "true" : "false"}>
      <header className="topic-card__header">
        <div className="topic-card__support">
          <div>
            <h2 className="topic-card__title">{topic.name}</h2>
            {topic.description && <p className="text-sm leading-6 text-[#4d5c6e]">{topic.description}</p>}
          </div>
          {dirty && (
            <span className="topic-card__chip">
              <SaveIcon />
              Unsaved
            </span>
          )}
        </div>
      </header>
      <div className="flex flex-col gap-6 md:flex-row">
        <div className="flex flex-1 flex-col gap-4">
          <fieldset className="flex flex-wrap gap-3" aria-label="Rating">
            <legend className="sr-only">Select a rating</legend>
            <label className={`flex items-center gap-2 rounded-md border ${state.is_na ? "border-[#0d80f2] bg-[#eaf3fe]" : "border-[#dfe4ed] bg-[#f9fbfd]"} px-3 py-2 text-sm`}>
              <input
                type="radio"
                name={`topic-${topic.id}`}
                value="na"
                checked={state.is_na}
                onChange={() => handleSelect(null)}
              />
              <span>N/A</span>
            </label>
            {sortedScale.map((scale) => (
              <label
                key={scale.level}
                className={`flex items-center gap-2 rounded-md border ${!state.is_na && state.rating_level === scale.level ? "border-[#0d80f2] bg-[#eaf3fe]" : "border-[#dfe4ed] bg-[#f9fbfd]"} px-3 py-2 text-sm`}
              >
                <input
                  type="radio"
                  name={`topic-${topic.id}`}
                  value={scale.level}
                  checked={!state.is_na && state.rating_level === scale.level}
                  onChange={() => handleSelect(scale.level)}
                />
                <span className="font-medium">{scale.level}</span>
                <span className="text-[#61758a]">{scale.label}</span>
              </label>
            ))}
          </fieldset>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-[#121417]" htmlFor={`comment-${topic.id}`}>
              Comment (optional)
            </label>
            <textarea
              id={`comment-${topic.id}`}
              className="min-h-[96px] w-full resize-vertical rounded-md border border-[#dfe4ed] px-3 py-2 text-sm text-[#121417] focus:border-[#0d80f2] focus:outline-none"
              value={state.comment}
              onChange={handleCommentChange}
              placeholder="Capture supporting evidence or context for this rating."
            />
          </div>
        </div>
        <aside className="md:w-72">
          <details className="group rounded-lg border border-[#dfe4ed] bg-[#f9fbfd] p-3" open>
            <summary className="cursor-pointer text-sm font-semibold text-[#121417]">Guidance by rating</summary>
            <div className="mt-3 flex flex-col gap-3 text-sm text-[#4d5c6e]">
              {sortedScale.map((scale) => {
                const guidance = topic.guidance?.[scale.level] ?? [];
                return (
                  <div key={scale.level}>
                    <div className="font-semibold text-[#121417]">Level {scale.level} · {scale.label}</div>
                    {scale.description && <p className="text-xs text-[#61758a]">{scale.description}</p>}
                    {guidance.length > 0 ? (
                      <ul className="mt-1 list-disc pl-5">
                        {guidance.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-1 text-xs text-[#61758a]">No topic-specific guidance provided for this level.</p>
                    )}
                  </div>
                );
              })}
            </div>
          </details>
        </aside>
      </div>
    </article>
  );
}
