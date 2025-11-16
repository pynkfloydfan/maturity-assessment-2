import type { TopicAssessmentDetail } from "../api/types";
import type { SnapshotMap, TopicSnapshot } from "../types/assessment";

export interface ThemeStats {
  done: number;
  total: number;
  percent: number;
  gap: number;
}

export interface TopicSelection {
  themeId: number | null;
  topicId: number | null;
}

function isSnapshotComplete(snapshot: TopicSnapshot | undefined): boolean {
  if (!snapshot) return false;
  if (snapshot.currentIsNa) {
    return snapshot.desiredIsNa;
  }
  return (
    typeof snapshot.currentMaturity === "number" &&
    (snapshot.desiredIsNa || typeof snapshot.desiredMaturity === "number")
  );
}

export function computeThemeStats(topics: TopicAssessmentDetail[], snapshots: SnapshotMap): ThemeStats {
  const total = topics.length;
  let done = 0;
  const currentValues: number[] = [];
  const desiredValues: number[] = [];

  topics.forEach((topic) => {
    const snapshot = snapshots[topic.id];
    if (!snapshot) {
      return;
    }
    if (isSnapshotComplete(snapshot)) {
      done += 1;
    }
    if (!snapshot.currentIsNa && typeof snapshot.currentMaturity === "number") {
      currentValues.push(snapshot.currentMaturity);
    }
    if (!snapshot.desiredIsNa && typeof snapshot.desiredMaturity === "number") {
      desiredValues.push(snapshot.desiredMaturity);
    }
  });

  const average = (values: number[]) =>
    values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

  const avgCurrent = average(currentValues);
  const avgDesired = average(desiredValues);
  const gap = Number.isFinite(avgDesired - avgCurrent) ? avgDesired - avgCurrent : 0;

  return {
    done,
    total,
    percent: total ? Math.round((done / total) * 100) : 0,
    gap,
  };
}

export function computeThemeStatsMap(
  topicsByTheme: Record<number, TopicAssessmentDetail[]>,
  snapshots: SnapshotMap,
): Record<number, ThemeStats> {
  const entries = Object.entries(topicsByTheme).map(([themeId, topics]) => [
    Number(themeId),
    computeThemeStats(topics, snapshots),
  ] as const);
  return Object.fromEntries(entries);
}

export function findNextTopicSelection(
  themeOrder: number[],
  topicsByTheme: Record<number, TopicAssessmentDetail[]>,
  currentThemeId: number | null,
  currentTopicId: number | null,
): TopicSelection {
  if (!themeOrder.length) {
    return { themeId: null, topicId: null };
  }

  const startingThemeId = currentThemeId ?? themeOrder[0];
  const currentThemeTopics = topicsByTheme[startingThemeId] ?? [];

  if (currentTopicId != null) {
    const idx = currentThemeTopics.findIndex((topic) => topic.id === currentTopicId);
    if (idx >= 0 && idx < currentThemeTopics.length - 1) {
      return { themeId: startingThemeId, topicId: currentThemeTopics[idx + 1].id };
    }
  }

  const startingThemeIndex = themeOrder.indexOf(startingThemeId);
  for (let offset = 1; offset <= themeOrder.length; offset += 1) {
    const nextIndex = (startingThemeIndex + offset) % themeOrder.length;
    const nextThemeId = themeOrder[nextIndex];
    const topics = topicsByTheme[nextThemeId] ?? [];
    if (!topics.length) {
      continue;
    }
    return { themeId: nextThemeId, topicId: topics[0].id };
  }

  return { themeId: null, topicId: null };
}
