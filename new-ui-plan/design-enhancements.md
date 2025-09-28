# UI Modernisation Plan

Goal: refresh the application’s visual language and UX (with a focus on the
Dimensions and Settings experiences) so it feels like a modern, editorial-style
product that makes better use of widescreen layouts.

## 0. Design Foundations

| Item | Decision |
| --- | --- |
| Design tone | Soft editorial, approachable yet professional |
| Typography | Introduce a modern web stack (e.g. `"Inter", "Work Sans", "-apple-system", sans-serif`) with a clear type scale (12/14/16/20/24/32/40) |
| Colour tokens | Establish CSS variables for Brand, Primary, and Secondary palettes (naming examples: `--color-brand-crimson`, `--color-primary-teal`, `--color-neutral-graphite`) |
| Layout grid | Max-width 1440–1600px container, centred, with 24–32px section spacing |
| Components | Card system with 3D depth (soft shadows, rounded radii), consistent spacing rhythm (8px base), iconography support |

## 1. Global Layout & Navigation

1. Convert the existing header into a persistent top bar + optional left sidebar stub (for larger screens) to anchor navigation and active state.
2. Ensure the top bar contains brand mark (minimal), active session selector, global actions (Settings, Help), and quick status badges (e.g. last sync/seed timestamp) as optional future enhancements.
3. Implement CSS grid helpers (`.app-shell`, `.top-nav`, `.content-area`) that keep page content within a centred max-width container but fill widescreen devices gracefully.

## 2. Dimension / Theme / Topic Pages

1. **Dimensions grid**
   - Fixed 3×3 layout at ≥1440px, 2×N on medium screens, 1 column on narrow viewports.
   - Card height fixed (~420px) with imagery (16:9) and content below.
   - Include microcopy (dimension category if available) and stats (e.g. theme count, rated topics).
   - Add subtle gradient or brand accent on hover.
2. **Themes page**
   - Two-column layout (card + detail panel optional) or maintain card grid with improved imagery grid.
   - Include new filters or “jump to theme” combobox for faster navigation.
3. **Topics / Rating view**
   - Maintain editorial tone by adding right-side info drawer (CMMI descriptions) with accent background.
   - Introduce sticky action bar (Save, Discard) for 1920px screens.

## 3. Settings Experience

1. Intro panel with quick status (active backend, session counts, last seed timestamp).
2. Two-column layout:
   - Left: Database configuration + seeding controls.
   - Right: Session management (create/combine), data exports/imports, optional upcoming items.
3. Add cards (with icons) for future features:
   - Data export history / download logs.
   - Asset/theming controls (e.g. upload custom logos, pick colour theme).
   - “System health” – latest migration applied, pending actions.
4. Provide immediate feedback (inline success/error banners) and disable buttons during long-running tasks.

## 4. Visual Assets & Illustrations

1. Introduce an icon library (Phosphor or Lucide) for card headers and bullet highlights.
2. Allow optional landing-panel illustration on top of each page (themes consistent with palette).
3. Keep imagery assets under `app/web/static/images/...`; document recommended dimensions (current suggestion 720×480px) and naming.

## 5. Implementation Steps

1. Set up a shared `theme.css` (or tokens) exporting CSS custom properties for the palette.
2. Swap typography globally via `:root` definitions and apply to headings, body, captions.
3. Rebuild Dimensions page to use new card component and grid helpers (with responsive breakpoints and spacing).
4. Update Themes page using the same component library and adjust imagery fallback.
5. Refactor Settings page into two columns with cards, the new accent colours, and richer feedback UI.
6. Add “quick status” widget (seed/migration info) if data is available.
7. Update README/design documentation to explain token location and how to customise colours/images.

## 6. Open Questions / To Validate Later

- Confirm whether we should surface brand palette accents elsewhere (e.g. session timeline, charts) after the baseline redesign.
- Consider dark mode or accessibility adjustments once primary refresh is complete.
- Evaluate adding behaviour for session quick-switching in the new top bar.

## 7. Deliverables Checklist

- [x] Global theme tokens file (colours, typography, spacing).
- [x] Updated layout shell (top nav + content container).
- [x] Dimension card component + responsive grid.
- [x] Themes page refactor using card grid.
- [x] Settings page two-column redesign with status cards.
- [ ] Documentation updates (README + future design notes).
- [ ] Visual polish: shadows, hover states, badge styles.
- [ ] Optional: new icons/illustrations (depends on asset selection).

## Suggestion for design improvements

- Introduce lightweight filtering or sorting (e.g. “show highest risk” toggle) on the Dimensions view so the refreshed cards support prioritisation workflows during workshops.
- Add contextual tooltips to the new status badges, clarifying how coverage and average scores are calculated, to help first-time facilitators explain the metrics in meetings.
- Explore a compact session overview drawer in the header that reuses the new iconography and shadows to surface recent activity without leaving the current page.
