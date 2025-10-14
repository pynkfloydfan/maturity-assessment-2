export interface CMMILevelConfig {
  level: number;
  label: string;
  color: string;
}

export const CMMI_LEVEL_CONFIG: CMMILevelConfig[] = [
  { level: 1, label: "Initial", color: "#D73027" },
  { level: 2, label: "Managed", color: "#D78827" },
  { level: 3, label: "Defined", color: "#FEE08B" },
  { level: 4, label: "Quantitatively Managed", color: "#27D730" },
  { level: 5, label: "Optimizing", color: "#3027D7" },
];

export const CMMI_LEVEL_LABELS: Record<number, string> = CMMI_LEVEL_CONFIG.reduce(
  (acc, level) => {
    acc[level.level] = level.label;
    return acc;
  },
  {} as Record<number, string>,
);
