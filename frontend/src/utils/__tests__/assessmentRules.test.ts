import { describe, expect, it } from "vitest";
import type { TopicSnapshot } from "../../types/assessment";
import {
  allowedDesiredLevels,
  applyCurrentSelection,
  applyDesiredSelection,
  getProgressState,
  isSnapshotComplete,
  mapShortcut,
} from "../assessmentRules";

const blankSnapshot = (): TopicSnapshot => ({
  currentMaturity: null,
  currentIsNa: false,
  desiredMaturity: null,
  desiredIsNa: false,
  comment: "",
  evidence: [],
});

describe("assessmentRules helpers", () => {
  it("enforces desired to stay at or above current", () => {
    const start = { ...blankSnapshot(), currentMaturity: 2 };
    const next = applyDesiredSelection(start, 1, false, [1, 2, 3, 4, 5], false);
    expect(next.desiredMaturity).toBe(2);
  });

  it("forces desired to N/A when current is N/A and treatNaAsZero disabled", () => {
    const start = { ...blankSnapshot(), currentIsNa: true, desiredIsNa: true };
    const levels = [1, 2, 3];
    expect(allowedDesiredLevels(start, levels, false)).toEqual([]);
    const attempted = applyDesiredSelection(start, 2, false, levels, false);
    expect(attempted).toEqual(start);
  });

  it("disallows desired N/A unless current is N/A or treatNaAsZero enabled", () => {
    const start = { ...blankSnapshot(), currentMaturity: 3, desiredMaturity: 4 };
    const attempt = applyDesiredSelection(start, null, true, [1, 2, 3, 4, 5], false);
    expect(attempt).toEqual(start);
    const treated = applyDesiredSelection(start, null, true, [1, 2, 3, 4, 5], true);
    expect(treated.desiredIsNa).toBe(true);
  });

  it("updates desired when current rating increases", () => {
    const start = { ...blankSnapshot(), desiredMaturity: 2 };
    const next = applyCurrentSelection(start, 4, false);
    expect(next.currentMaturity).toBe(4);
    expect(next.desiredMaturity).toBe(4);
  });

  it("detects completion and progress states", () => {
    const pending = blankSnapshot();
    expect(isSnapshotComplete(pending)).toBe(false);
    expect(getProgressState(pending)).toBe("not_started");
    const currentOnly = { ...pending, currentMaturity: 2 };
    expect(getProgressState(currentOnly)).toBe("in_progress");
    const done = { ...currentOnly, desiredMaturity: 3 };
    expect(isSnapshotComplete(done)).toBe(true);
    expect(getProgressState(done)).toBe("complete");
  });

  it("maps keyboard shortcuts for ratings", () => {
    expect(mapShortcut("n", false)).toEqual({ target: "current", value: null, isNa: true });
    expect(mapShortcut("N", true)).toEqual({ target: "desired", value: null, isNa: true });
    expect(mapShortcut("3", false)).toEqual({ target: "current", value: 3, isNa: false });
    expect(mapShortcut("5", true)).toEqual({ target: "desired", value: 5, isNa: false });
    expect(mapShortcut("x", false)).toBeNull();
  });
});
