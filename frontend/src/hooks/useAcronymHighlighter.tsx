import { Fragment, useCallback, type ReactNode } from "react";
import type { Acronym } from "../api/types";
import { useAcronymContext } from "../context/AcronymContext";
import { Tooltip, TooltipContent, TooltipTrigger } from "../components/ui/tooltip";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderWithAcronyms(text: string, acronyms: Acronym[]): ReactNode {
  if (!text || !acronyms.length) {
    return text;
  }

  const lookup = new Map<string, Acronym>();
  const tokens: string[] = [];

  acronyms.forEach((entry) => {
    const key = entry.acronym;
    if (!lookup.has(key)) {
      lookup.set(key, entry);
      tokens.push(escapeRegExp(key));
    }
  });

  if (!tokens.length) {
    return text;
  }

  const pattern = new RegExp(`\\b(${tokens.join("|")})\\b`, "g");
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let matchIndex = 0;

  text.replace(pattern, (match, _group, offset) => {
    const index = typeof offset === "number" ? offset : text.indexOf(match, lastIndex);
    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index));
    }

    const entry = lookup.get(match);
    if (entry) {
      nodes.push(
        <Tooltip key={`acronym-${match}-${index}-${matchIndex}`}>
          <TooltipTrigger asChild>
            <span className="acronym-highlight">{match}</span>
          </TooltipTrigger>
          <TooltipContent side="top" align="center" className="max-w-xs space-y-1 text-left">
            <div className="font-semibold text-primary-foreground">{entry.full_term}</div>
            {entry.meaning && <p className="text-sm leading-5 text-primary-foreground/90">{entry.meaning}</p>}
          </TooltipContent>
        </Tooltip>,
      );
    } else {
      nodes.push(match);
    }

    lastIndex = index + match.length;
    matchIndex += 1;
    return match;
  });

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  if (nodes.length === 1) {
    return nodes[0];
  }

  return nodes.map((node, index) => <Fragment key={`chunk-${index}`}>{node}</Fragment>);
}

export function useAcronymHighlighter() {
  const { acronyms } = useAcronymContext();

  return useCallback(
    (text: string | null | undefined) => {
      if (text == null) {
        return text ?? "";
      }
      return renderWithAcronyms(text, acronyms);
    },
    [acronyms],
  );
}
