import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useParams } from "react-router-dom";
import Breadcrumb from "./shared/Breadcrumb";
import { useThemeTopics } from "../hooks/useThemeTopics";
import { useSessionContext } from "../context/SessionContext";
import { useDimensions } from "../hooks/useDimensions";
import { apiPost } from "../api/client";
import type { RatingScaleItem, RatingUpdatePayload, TopicDetail } from "../api/types";

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

  const dimension = dimensions.find((item) => item.id === dimensionId);
  const theme = data?.theme;
  const breadcrumbItems = [
    { label: "Dimensions", path: "/" },
    dimension ? { label: dimension.name, path: `/dimensions/${dimension.id}/themes` } : undefined,
    theme ? { label: theme.name } : undefined,
  ].filter(Boolean) as { label: string; path?: string }[];

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <Breadcrumb items={breadcrumbItems} />
      {theme && (
        <header className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold text-[#121417]">{theme.name}</h1>
          {theme.description && <p className="max-w-3xl text-base leading-6 text-[#4d5c6e]">{theme.description}</p>}
        </header>
      )}
      {data?.generic_guidance?.length ? (
        <aside className="rounded-xl border border-[#dfe4ed] bg-white p-4 text-sm text-[#4d5c6e] shadow-sm">
          <h2 className="mb-2 text-base font-semibold text-[#121417]">Theme-level guidance</h2>
          <ul className="flex flex-wrap gap-3">
            {data.generic_guidance.map((item) => (
              <li key={item.level} className="rounded-lg border border-[#e5e8eb] bg-[#f9fbfd] px-3 py-2">
                <span className="block text-xs font-medium uppercase tracking-wide text-[#61758a]">
                  Level {item.level}
                </span>
                <span className="text-sm text-[#4d5c6e]">{item.description}</span>
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm text-[#61758a]">
          Session #{activeSessionId} · {data?.topics.length ?? 0} topics
        </div>
        <div className="flex items-center gap-3">
          {saveError && <span className="text-sm text-red-600">{saveError}</span>}
          {saveMessage && <span className="text-sm text-green-600">{saveMessage}</span>}
          <button
            type="button"
            className="rounded-md bg-[#0d80f2] px-4 py-2 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-[#a9c7ec]"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
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
    <article className="rounded-xl border border-[#e5e8eb] bg-white p-6 shadow-sm">
      <header className="mb-4 flex flex-col gap-2">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-[#121417]">{topic.name}</h2>
            {topic.description && <p className="mt-1 text-sm leading-5 text-[#4d5c6e]">{topic.description}</p>}
          </div>
          {dirty && <span className="text-xs font-medium uppercase tracking-wide text-[#0d80f2]">Unsaved</span>}
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
