import { describe, expect, it } from "vitest";
import type { TopicAssessmentDetail } from "../../api/types";
import type { SnapshotMap } from "../../types/assessment";
import { computeThemeStats, computeThemeStatsMap, findNextTopicSelection } from "../themeStats";

describe("themeStats utilities", () => {
  const makeTopic = (id: number): TopicAssessmentDetail => ({
    id,
    name: `Topic ${id}`,
    description: "",
    guidance: {},
  } as TopicAssessmentDetail);

  it("computes completion and gap", () => {
    const topics = [makeTopic(1), makeTopic(2), makeTopic(3)];
    const snapshots: SnapshotMap = {
      1: { currentMaturity: 2, currentIsNa: false, desiredMaturity: 3, desiredIsNa: false, comment: "", evidence: [] },
      2: { currentMaturity: 4, currentIsNa: false, desiredMaturity: 4, desiredIsNa: false, comment: "", evidence: [] },
      3: { currentMaturity: null, currentIsNa: true, desiredMaturity: null, desiredIsNa: true, comment: "", evidence: [] },
    };
    const stats = computeThemeStats(topics, snapshots);
    expect(stats.done).toBe(3);
    expect(stats.total).toBe(3);
    expect(stats.percent).toBe(100);
    expect(stats.gap).toBeCloseTo(0.5);
  });

  it("builds map for all themes", () => {
    const topicsByTheme = {
      1: [makeTopic(1)],
      2: [makeTopic(2), makeTopic(3)],
    } satisfies Record<number, TopicAssessmentDetail[]>;
    const snapshots: SnapshotMap = {
      1: { currentMaturity: 2, currentIsNa: false, desiredMaturity: 3, desiredIsNa: false, comment: "", evidence: [] },
      2: { currentMaturity: 3, currentIsNa: false, desiredMaturity: 4, desiredIsNa: false, comment: "", evidence: [] },
      3: { currentMaturity: null, currentIsNa: true, desiredMaturity: null, desiredIsNa: true, comment: "", evidence: [] },
    };
    const statsMap = computeThemeStatsMap(topicsByTheme, snapshots);
    expect(statsMap[1]?.done).toBe(1);
    expect(statsMap[2]?.total).toBe(2);
  });

  it("finds next topic across themes", () => {
    const topicsByTheme = {
      1: [makeTopic(1), makeTopic(2)],
      2: [makeTopic(3)],
    } satisfies Record<number, TopicAssessmentDetail[]>;
    const selection = findNextTopicSelection([1, 2], topicsByTheme, 1, 2);
    expect(selection.themeId).toBe(2);
    expect(selection.topicId).toBe(3);
  });

  it("wraps when reaching the final theme", () => {
    const topicsByTheme = {
      1: [makeTopic(1)],
      2: [makeTopic(2)],
    } satisfies Record<number, TopicAssessmentDetail[]>;
    const selection = findNextTopicSelection([1, 2], topicsByTheme, 2, 2);
    expect(selection.themeId).toBe(1);
    expect(selection.topicId).toBe(1);
  });
});
