import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
} from "react";
import { Navigate, useParams } from "react-router-dom";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { ScrollArea } from "./ui/scroll-area";
import { Separator } from "./ui/separator";
import { Textarea } from "./ui/textarea";
import { SaveIcon } from "../icons";
import { useNavigationBlocker } from "../hooks/useNavigationBlocker";
import { useDimensionAssessment } from "../hooks/useDimensionAssessment";
import { useAcronymHighlighter } from "../hooks/useAcronymHighlighter";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";
import { useSessionContext } from "../context/SessionContext";
import { apiPost } from "../api/client";
import type { RatingScaleItem, ThemeAssessmentBlock, TopicAssessmentDetail } from "../api/types";
import { computeThemeStatsMap, findNextTopicSelection } from "../utils/themeStats";
import type { ThemeStats } from "../utils/themeStats";
import type { TopicSnapshot, SnapshotMap } from "../types/assessment";
import {
  allowedDesiredLevels,
  applyCurrentSelection,
  applyDesiredSelection,
  getProgressState,
  isSnapshotComplete,
  mapShortcut,
} from "../utils/assessmentRules";
import { getGradientStyle, getRatingChipStyle } from "../utils/ratingColors";

type SnapshotMapState = SnapshotMap;

function buildSnapshot(topic: TopicAssessmentDetail): TopicSnapshot {
  return {
    currentMaturity: topic.current_is_na ? null : topic.current_maturity ?? null,
    currentIsNa: topic.current_is_na,
    desiredMaturity: topic.desired_is_na ? null : topic.desired_maturity ?? null,
    desiredIsNa: topic.desired_is_na,
    comment: topic.comment ?? "",
    evidence: topic.evidence_links ?? [],
  };
}

function extractSnapshotLevels(snapshot?: TopicSnapshot) {
  const current =
    snapshot && !snapshot.currentIsNa && typeof snapshot.currentMaturity === "number"
      ? snapshot.currentMaturity
      : null;
  const desired =
    snapshot && !snapshot.desiredIsNa && typeof snapshot.desiredMaturity === "number"
      ? snapshot.desiredMaturity
      : null;
  return { current, desired };
}

function gradientForSnapshot(snapshot?: TopicSnapshot) {
  const { current, desired } = extractSnapshotLevels(snapshot);
  if (current == null || desired == null) {
    return undefined;
  }
  return getGradientStyle(current, desired);
}

interface RatingControlProps {
  label: string;
  value: number | null;
  isNa: boolean;
  ratingScale: RatingScaleItem[];
  allowNa: boolean;
  disabled: boolean;
  allowedLevels?: number[];
  onSelect: (next: number | null, isNa: boolean) => void;
  showLabel?: boolean;
  naDisabled?: boolean;
}

function RatingControl({
  label,
  value,
  isNa,
  ratingScale,
  allowNa,
  disabled,
  allowedLevels,
  onSelect,
  showLabel = true,
  naDisabled = false,
}: RatingControlProps) {
  return (
    <div className="space-y-3">
      {showLabel && <div className="text-sm font-medium text-foreground">{label}</div>}
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={label}>
        {allowNa && (
          <button
            type="button"
            role="radio"
            aria-checked={isNa}
            className={`rounded-full border px-3 py-1 text-sm transition ${
              isNa
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-muted/40 hover:bg-muted/60"
            } ${naDisabled ? "cursor-not-allowed opacity-40" : ""}`}
            onClick={() => onSelect(null, true)}
            disabled={disabled || naDisabled}
          >
            N/A
          </button>
        )}
        {ratingScale.map((item) => {
          const level = item.level;
          const selected = level === value && !isNa;
          const levelDisabled = disabled || (Array.isArray(allowedLevels) && !allowedLevels.includes(level));
          const selectedStyle = selected ? getRatingChipStyle(level) : undefined;
          return (
            <button
              key={item.level}
              type="button"
              role="radio"
              aria-checked={selected}
              className={`rounded-full border border-border px-3 py-1 text-sm transition ${
                selected ? "shadow-sm" : "bg-background hover:bg-muted/60"
              } ${levelDisabled ? "cursor-not-allowed opacity-50" : ""}`}
              disabled={levelDisabled}
              onClick={() => onSelect(level, false)}
              style={selectedStyle}
            >
              {level}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface DimensionAssessmentPageProps {
  enableTreatNAasZero?: boolean;
}

export default function DimensionAssessmentPage({ enableTreatNAasZero = false }: DimensionAssessmentPageProps = {}) {
  const params = useParams<{ dimensionId: string }>();
  const dimensionId = params.dimensionId ? Number.parseInt(params.dimensionId, 10) : NaN;

  if (!params.dimensionId || Number.isNaN(dimensionId)) {
    return <Navigate to="/" replace />;
  }

  const highlight = useAcronymHighlighter();
  const renderDescriptionWithBreaks = useCallback(
    (text: string) => {
      return text.split(/\r?\n/).map((segment, index) => (
        <Fragment key={`topic-description-line-${index}`}>
          {index > 0 && <br />}
          {highlight(segment)}
        </Fragment>
      ));
    },
    [highlight],
  );
  const { activeSessionId } = useSessionContext();
  const { data, loading, error, refresh } = useDimensionAssessment(dimensionId, activeSessionId);
  const [initialSnapshots, setInitialSnapshots] = useState<SnapshotMapState>({});
  const [snapshots, setSnapshots] = useState<SnapshotMapState>({});
  const [activeThemeId, setActiveThemeId] = useState<number | null>(null);
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const breadcrumbItems = useMemo(() => {
    if (!data?.dimension) return [{ label: "Dimensions", path: "/" }];
    return [
      { label: "Dimensions", path: "/" },
      { label: data.dimension.name },
    ];
  }, [data]);
  usePageBreadcrumb(breadcrumbItems);

  const themeList = data?.themes ?? [];
  const orderedThemeIds = useMemo(() => themeList.map((theme) => theme.id), [themeList]);

  const topicsByTheme = useMemo(() => {
    const mapping: Record<number, TopicAssessmentDetail[]> = {};
    themeList.forEach((theme) => {
      mapping[theme.id] = theme.topics ?? [];
    });
    return mapping;
  }, [themeList]);

  const topicLookup = useMemo(() => {
    const map = new Map<number, TopicAssessmentDetail>();
    themeList.forEach((theme) => {
      theme.topics.forEach((topic) => map.set(topic.id, topic));
    });
    return map;
  }, [themeList]);

  useEffect(() => {
    if (!data) {
      setInitialSnapshots({});
      setSnapshots({});
      setSelectedTopicId(null);
      return;
    }
    const snapshotMap: SnapshotMapState = {};
    data.themes.forEach((theme) => {
      theme.topics.forEach((topic) => {
        snapshotMap[topic.id] = buildSnapshot(topic);
      });
    });
    setInitialSnapshots(snapshotMap);
    setSnapshots(snapshotMap);
  }, [data]);

  useEffect(() => {
    if (!themeList.length) {
      setActiveThemeId(null);
      setSelectedTopicId(null);
      return;
    }
    setActiveThemeId((prev) => {
      if (prev && themeList.some((theme) => theme.id === prev)) {
        return prev;
      }
      return themeList[0].id;
    });
  }, [themeList]);

  const activeThemeTopics = activeThemeId ? topicsByTheme[activeThemeId] ?? [] : [];

  useEffect(() => {
    if (!activeThemeId || !activeThemeTopics.length) {
      setSelectedTopicId(null);
      return;
    }
    setSelectedTopicId((prev) => {
      if (prev && activeThemeTopics.some((topic) => topic.id === prev)) {
        return prev;
      }
      const firstUnrated = activeThemeTopics.find((topic) => !isSnapshotComplete(snapshots[topic.id]));
      return firstUnrated?.id ?? activeThemeTopics[0].id;
    });
  }, [activeThemeId, activeThemeTopics, snapshots]);

  const filteredTopics = useMemo(() => activeThemeTopics, [activeThemeTopics]);

  useEffect(() => {
    if (!selectedTopicId) return;
    if (filteredTopics.some((topic) => topic.id === selectedTopicId)) return;
    if (filteredTopics.length) {
      setSelectedTopicId(filteredTopics[0].id);
    }
  }, [filteredTopics, selectedTopicId]);

  const themeStatsMap = useMemo(() => computeThemeStatsMap(topicsByTheme, snapshots), [topicsByTheme, snapshots]);

  const statsProvider = useCallback(
    (themeId: number): ThemeStats => {
      const stats = themeStatsMap[themeId];
      if (stats) return stats;
      const total = topicsByTheme[themeId]?.length ?? 0;
      return { done: 0, total, percent: 0, gap: 0 };
    },
    [themeStatsMap, topicsByTheme],
  );

  const topicLookupMap = topicLookup;
  const selectedTopic = selectedTopicId ? topicLookupMap.get(selectedTopicId) ?? null : null;
  const selectedSnapshot = selectedTopicId ? snapshots[selectedTopicId] : undefined;
  const ratingScale = data?.rating_scale ?? [];
  const ratingLevels = useMemo(
    () => ratingScale.map((item) => item.level).sort((a, b) => a - b),
    [ratingScale],
  );
  const desiredAllowedLevels = useMemo(
    () => allowedDesiredLevels(selectedSnapshot, ratingLevels, enableTreatNAasZero),
    [selectedSnapshot, ratingLevels, enableTreatNAasZero],
  );

  const topicsForProgress = useMemo(
    () => Object.values(topicsByTheme).flat(),
    [topicsByTheme],
  );

  const topicProgress = useMemo(() => {
    if (!topicsForProgress.length) {
      return { total: 0, complete: 0, inProgress: 0, notStarted: 0, percent: 0 };
    }
    let complete = 0;
    let inProgress = 0;
    let notStarted = 0;
    topicsForProgress.forEach((topic) => {
      const snapshot = snapshots[topic.id];
      if (isSnapshotComplete(snapshot)) complete += 1;
      else if (snapshot && (snapshot.comment.trim().length || snapshot.evidence.length)) inProgress += 1;
      else notStarted += 1;
    });
    const percent = Math.round((complete / topicsForProgress.length) * 100);
    return { total: topicsForProgress.length, complete, inProgress, notStarted, percent };
  }, [snapshots, topicsForProgress]);

  const isReadOnly = !activeSessionId;

  const handleThemeSelect = useCallback(
    (themeId: number) => {
      if (themeId === activeThemeId) return;
      setActiveThemeId(themeId);
      const themeTopics = topicsByTheme[themeId] ?? [];
      if (themeTopics.length) {
        const firstUnrated = themeTopics.find((topic) => !isSnapshotComplete(snapshots[topic.id]));
        setSelectedTopicId(firstUnrated?.id ?? themeTopics[0].id);
      } else {
        setSelectedTopicId(null);
      }
    },
    [activeThemeId, snapshots, topicsByTheme],
  );

  const updateSnapshot = useCallback(
    (topicId: number, updater: (prev: TopicSnapshot) => TopicSnapshot) => {
      setSnapshots((previous) => {
        const existing = previous[topicId] ?? {
          currentMaturity: null,
          currentIsNa: false,
          desiredMaturity: null,
          desiredIsNa: false,
          comment: "",
          evidence: [],
        };
        return {
          ...previous,
          [topicId]: updater(existing),
        };
      });
      setSaveError(null);
      setSaveMessage(null);
    },
    [],
  );

  const handleCurrentChange = useCallback(
    (topicId: number, value: number | null, isNa: boolean) => {
      updateSnapshot(topicId, (prev) => applyCurrentSelection(prev, value, isNa));
    },
    [updateSnapshot],
  );

  const handleDesiredChange = useCallback(
    (topicId: number, value: number | null, isNa: boolean) => {
      updateSnapshot(topicId, (prev) =>
        applyDesiredSelection(prev, value, isNa, ratingLevels, enableTreatNAasZero),
      );
    },
    [enableTreatNAasZero, ratingLevels, updateSnapshot],
  );

  const handleCommentChange = useCallback(
    (topicId: number, event: ChangeEvent<HTMLTextAreaElement>) => {
      updateSnapshot(topicId, (prev) => ({ ...prev, comment: event.target.value }));
    },
    [updateSnapshot],
  );

  const handleEvidenceChange = useCallback(
    (topicId: number, event: ChangeEvent<HTMLTextAreaElement>) => {
      const value = event.target.value;
      const links = value
        .split(/\r?\n/)
        .map((item) => item.trim())
        .filter(Boolean);
      updateSnapshot(topicId, (prev) => ({ ...prev, evidence: links }));
    },
    [updateSnapshot],
  );

  const isTopicDirty = useCallback(
    (topicId: number) => {
      const initial = initialSnapshots[topicId];
      const current = snapshots[topicId];
      if (!initial && !current) return false;
      if (!initial || !current) return true;
      if (initial.currentIsNa !== current.currentIsNa) return true;
      if ((initial.currentMaturity ?? null) !== (current.currentMaturity ?? null)) return true;
      if (initial.desiredIsNa !== current.desiredIsNa) return true;
      if ((initial.desiredMaturity ?? null) !== (current.desiredMaturity ?? null)) return true;
      if (initial.comment.trim() !== current.comment.trim()) return true;
      if (initial.evidence.length !== current.evidence.length) return true;
      for (let i = 0; i < initial.evidence.length; i += 1) {
        if (initial.evidence[i] !== current.evidence[i]) return true;
      }
      return false;
    },
    [initialSnapshots, snapshots],
  );

  const hasChanges = useMemo(() => {
    return topicsForProgress.some((topic) => isTopicDirty(topic.id));
  }, [isTopicDirty, topicsForProgress]);

  const navigationBlocker = useNavigationBlocker(hasChanges);

  const handleSave = useCallback(async (): Promise<boolean> => {
    if (!data || !activeSessionId) return false;
    const updates = topicsForProgress
      .filter((topic) => isTopicDirty(topic.id))
      .map((topic) => {
        const snapshot = snapshots[topic.id];
        const progressState = getProgressState(snapshot);
        return {
          topic_id: topic.id,
          current_maturity: snapshot.currentIsNa ? null : snapshot.currentMaturity,
          desired_maturity: snapshot.desiredIsNa ? null : snapshot.desiredMaturity,
          current_is_na: snapshot.currentIsNa,
          desired_is_na: snapshot.desiredIsNa,
          comment: snapshot.comment.trim() ? snapshot.comment.trim() : null,
          evidence_links: snapshot.evidence,
          progress_state: progressState,
        };
      });

    if (updates.length === 0) {
      return false;
    }

    try {
      setSaving(true);
      setSaveError(null);
      await apiPost(`/api/sessions/${activeSessionId}/ratings`, {
        session_id: activeSessionId,
        updates,
      });
      await refresh();
      setSaveMessage("Changes saved");
      return true;
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save changes");
      return false;
    } finally {
      setSaving(false);
    }
  }, [activeSessionId, data, isTopicDirty, refresh, snapshots, topicsForProgress]);

  const handleSaveAndNext = useCallback(async () => {
    const saved = await handleSave();
    if (!saved) return;
    const nextSelection = findNextTopicSelection(orderedThemeIds, topicsByTheme, activeThemeId, selectedTopicId);
    if (nextSelection.themeId != null) {
      setActiveThemeId(nextSelection.themeId);
      setSelectedTopicId(nextSelection.topicId);
    }
  }, [activeThemeId, handleSave, orderedThemeIds, selectedTopicId, topicsByTheme]);

  useEffect(() => {
    if (!selectedTopic || isReadOnly) return;
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) {
        return;
      }

      const action = mapShortcut(event.key, event.shiftKey);
      if (!action) {
        return;
      }
      event.preventDefault();
      if (action.target === "current") {
        handleCurrentChange(selectedTopic.id, action.value, action.isNa);
      } else {
        handleDesiredChange(selectedTopic.id, action.value, action.isNa);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleCurrentChange, handleDesiredChange, isReadOnly, selectedTopic]);

  const renderTopicList = () => {
    if (!activeThemeId) {
      return <div className="text-sm text-muted-foreground">Select a theme to view its topics.</div>;
    }
    if (!filteredTopics.length) {
      return (
        <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
          No topics found in this theme.
        </div>
      );
    }

    return filteredTopics.map((topic) => {
      const snapshot = snapshots[topic.id];
      const gradientStyle = gradientForSnapshot(snapshot);
      const badgeLabel = isSnapshotComplete(snapshot) ? `${snapshot.currentIsNa ? "N/A" : snapshot.currentMaturity ?? "–"}→${
        snapshot.desiredIsNa ? "N/A" : snapshot.desiredMaturity ?? "–"
      }` : "Unrated";
      return (
        <button
          key={topic.id}
          type="button"
          onClick={() => setSelectedTopicId(topic.id)}
          className={`w-full rounded-lg border px-3 py-3 text-left transition shadow-sm ${
            selectedTopicId === topic.id
              ? "border-primary bg-primary/10"
              : "border-border bg-background hover:border-primary/40 hover:bg-muted/40"
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="text-sm font-medium leading-snug text-foreground">{highlight(topic.name)}</div>
            <Badge
              variant={isSnapshotComplete(snapshot) ? "default" : "secondary"}
              style={gradientStyle}
            >
              {badgeLabel}
            </Badge>
          </div>
          {topic.description && (
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">{highlight(topic.description)}</p>
          )}
        </button>
      );
    });
  };

  const renderThemeList = () => {
    if (!themeList.length) {
      return <div className="text-sm text-muted-foreground">No themes available.</div>;
    }
    return themeList.map((theme) => {
      const stats = statsProvider(theme.id);
      const isActive = theme.id === activeThemeId;
      return (
        <button
          key={theme.id}
          type="button"
          onClick={() => handleThemeSelect(theme.id)}
          className={`theme-pillar ${isActive ? "theme-pillar--active" : ""}`}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="font-semibold text-sm text-foreground">{highlight(theme.name)}</div>
            <Badge variant={stats.done === stats.total && stats.total > 0 ? "default" : "secondary"}>
              {stats.done}/{stats.total}
            </Badge>
          </div>
          {theme.description && (
            <p className="theme-pillar__description">{highlight(theme.description)}</p>
          )}
          <div className="theme-pillar__metrics">
            <div className="theme-pillar__progress">
              <Progress value={stats.percent} />
            </div>
            <span className="theme-pillar__gap">Δ {stats.gap.toFixed(1)}</span>
          </div>
        </button>
      );
    });
  };

  return (
    <div className="flex h-full flex-col gap-4">
      <header className="border-b border-border bg-background px-6 py-4 shadow-sm">
        <div className="flex w-full flex-wrap items-stretch gap-4">
          <div className="flex min-w-[260px] flex-1 flex-col gap-2">
            <div className="text-3xl font-semibold text-foreground">
              {data?.dimension ? highlight(data.dimension.name) : "Dimension assessment"}
            </div>
            <div className="mt-2 flex items-center gap-3 text-sm text-muted-foreground">
              <span>
                {topicProgress.complete}/{topicProgress.total} complete
              </span>
              <div className="w-48">
                <Progress value={topicProgress.percent} />
              </div>
              <span>{topicProgress.percent}%</span>
            </div>
          </div>
          {data?.dimension?.description && (
            <div className="flex-1 min-w-[260px] rounded-xl border border-border bg-muted/40 p-4 text-sm leading-relaxed text-muted-foreground">
              {highlight(data.dimension.description)}
            </div>
          )}
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={handleSave}
              disabled={isReadOnly || saving || !hasChanges}
            >
              <SaveIcon />
              Save
            </Button>
            <Button onClick={handleSaveAndNext} disabled={isReadOnly || saving || !hasChanges}>
              <SaveIcon />
              Save &amp; Next
            </Button>
            {navigationBlocker.pending && (
              <Button variant="secondary" onClick={navigationBlocker.proceed}>
                Leave without saving
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-1 flex-col gap-6 px-4 pb-6 md:px-6 assessment-expanded">
        <div className="space-y-4">
          {error && <div className="info-banner error">{error}</div>}
          {!activeSessionId && (
            <div className="info-banner warning">
              Select or create an assessment session in the header to enable editing.
            </div>
          )}
          {saving && <div className="info-banner">Saving changes…</div>}
          {saveMessage && <div className="info-banner success">{saveMessage}</div>}
          {saveError && <div className="info-banner error">{saveError}</div>}
        </div>

        <div className="assessment-layout">
          <aside className="assessment-theme-rail">
            <div className="theme-rail-header">
              <div className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Themes</div>
              <div className="text-xs text-muted-foreground">{themeList.length} total</div>
            </div>
            <ScrollArea className="theme-rail-scroll">
              <div className="flex flex-col gap-4">{renderThemeList()}</div>
            </ScrollArea>
          </aside>
          <aside className="assessment-rail">
            <div className="assessment-rail-header">
              <div className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Topics</div>
              <div className="text-xs text-muted-foreground">
                {activeThemeId ? `${filteredTopics.length} total` : "Select a theme"}
              </div>
            </div>
            <ScrollArea className="assessment-rail-scroll">
              <div className="flex flex-col gap-4">{renderTopicList()}</div>
            </ScrollArea>
          </aside>

          <main className="assessment-main">
            <Card className="border-none shadow-none">
              <CardHeader className="pb-3">
                <CardTitle className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {selectedTopic ? highlight(selectedTopic.theme_name) : "Topic"}
                    </div>
                    <div className="text-xl font-semibold text-foreground">
                      {selectedTopic ? highlight(selectedTopic.name) : "Select a topic"}
                    </div>
                  </div>
                  <Badge
                    variant={isSnapshotComplete(selectedSnapshot) ? "default" : "secondary"}
                    style={gradientForSnapshot(selectedSnapshot)}
                  >
                    {selectedSnapshot
                      ? selectedSnapshot.currentIsNa
                        ? "N/A"
                        : `${selectedSnapshot.currentMaturity ?? "–"}→${
                            selectedSnapshot.desiredIsNa ? "N/A" : selectedSnapshot.desiredMaturity ?? "–"
                          }`
                      : "Unrated"}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-8">
                {!selectedTopic && (
                  <div className="text-sm text-muted-foreground">
                    Choose a topic from the list to begin the assessment.
                  </div>
                )}

                {selectedTopic && (
                  <Fragment>
                    <div>
                      <details className="group rounded-lg border border-border bg-muted/30 px-4 py-3">
                        <summary className="flex cursor-pointer items-center justify-between text-sm text-muted-foreground">
                          <span>What it is</span>
                          <span className="flex items-center gap-1 text-xs uppercase tracking-wide">
                            Expand
                            <span className="transition-transform group-open:rotate-90">›</span>
                          </span>
                        </summary>
                        {selectedTopic.description ? (
                          <div className="mt-3 text-sm leading-relaxed text-muted-foreground">
                            {renderDescriptionWithBreaks(selectedTopic.description)}
                          </div>
                        ) : (
                          <div className="mt-3 text-sm text-muted-foreground/80">No description provided.</div>
                        )}
                      </details>
                    </div>

                    <div className="rating-grid">
                      <div className="rating-box">
                        <div className="text-sm font-semibold text-foreground">Current rating</div>
                        <RatingControl
                          label="Current rating"
                          value={selectedSnapshot?.currentMaturity ?? null}
                          isNa={selectedSnapshot?.currentIsNa ?? false}
                          ratingScale={ratingScale}
                          allowNa
                          disabled={isReadOnly}
                          showLabel={false}
                          onSelect={(next, isNa) => handleCurrentChange(selectedTopic.id, next, isNa)}
                        />
                      </div>
                      <div className="rating-box">
                        <div className="text-sm font-semibold text-foreground">Desired rating</div>
                        <RatingControl
                          label="Desired rating"
                          value={selectedSnapshot?.desiredMaturity ?? null}
                          isNa={selectedSnapshot?.desiredIsNa ?? false}
                          ratingScale={ratingScale}
                          allowNa={false}
                          disabled={isReadOnly}
                          allowedLevels={desiredAllowedLevels}
                          showLabel={false}
                          onSelect={(next, isNa) => handleDesiredChange(selectedTopic.id, next, isNa)}
                        />
                      </div>
                    </div>

                    <Separator />

                    <div className="details-grid">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground" htmlFor="topic-comment">
                          Comments / evidence (optional)
                        </label>
                        <Textarea
                          id="topic-comment"
                          value={selectedSnapshot?.comment ?? ""}
                          onChange={(event) => handleCommentChange(selectedTopic.id, event)}
                          className="comment-textarea"
                          placeholder="Capture supporting evidence or context for this rating."
                          disabled={isReadOnly}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground" htmlFor="topic-evidence">
                          Evidence links
                        </label>
                        <Textarea
                          id="topic-evidence"
                          value={selectedSnapshot ? selectedSnapshot.evidence.join("\n") : ""}
                          onChange={(event) => handleEvidenceChange(selectedTopic.id, event)}
                          className="evidence-textarea"
                          placeholder="One link per line"
                          disabled={isReadOnly}
                        />
                      </div>
                    </div>
                  </Fragment>
                )}
              </CardContent>
            </Card>
          </main>

          <aside className="assessment-guidance">
            <div className="mb-3 text-sm font-semibold text-foreground">Guidance by rating</div>
            <p className="mb-4 text-xs text-muted-foreground">
              Selecting a level highlights the matching guidance.
            </p>
            <ScrollArea className="assessment-guidance-scroll">
              <div className="flex flex-col gap-4">{(() => {
              if (!selectedTopic) {
                return <div className="text-sm text-muted-foreground">Select a topic to view guidance.</div>;
              }
              if (!ratingScale.length) {
                return <div className="text-sm text-muted-foreground">Rating scale not configured.</div>;
              }
              const snapshot = snapshots[selectedTopic.id];
              return ratingScale.map((item) => {
                const isCurrent = snapshot && !snapshot.currentIsNa && snapshot.currentMaturity === item.level;
                const isDesired = snapshot && !snapshot.desiredIsNa && snapshot.desiredMaturity === item.level;
                const guidance = selectedTopic.guidance[item.level] ?? [];
                const baseBadgeStyle = getRatingChipStyle(item.level);
                const badgeStyle = baseBadgeStyle
                  ? isCurrent || isDesired
                    ? baseBadgeStyle
                    : {
                        borderColor: baseBadgeStyle.borderColor,
                        color: baseBadgeStyle.borderColor,
                        backgroundColor: "transparent",
                        opacity: 0.85,
                      }
                  : undefined;
                return (
                  <div
                    key={item.level}
                    className={`rounded-xl border p-4 shadow-sm transition ${
                      isCurrent || isDesired ? "border-primary bg-primary/10" : "border-border bg-card"
                    }`}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className="min-w-10 justify-center"
                        style={badgeStyle}
                      >
                        {item.level}
                      </Badge>
                      <span className="text-sm font-semibold text-foreground">
                        {highlight(`Level ${item.level} — ${item.label}`)}
                      </span>
                    </div>
                    {item.description && (
                      <p className="text-xs text-muted-foreground">{highlight(item.description)}</p>
                    )}
                    <div className="mt-2 space-y-2 text-sm text-muted-foreground">
                      {guidance.length > 0 ? (
                        guidance.map((text, index) => (
                          <p key={index} className="leading-snug">
                            {highlight(text)}
                          </p>
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          No topic-specific guidance is available for this level.
                        </p>
                      )}
                    </div>
                  </div>
                );
              });
            })()}</div>
            </ScrollArea>
          </aside>
        </div>
      </div>
    </div>
  );
}
