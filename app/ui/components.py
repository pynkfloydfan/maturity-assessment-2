from __future__ import annotations

import streamlit as st

from app.utils.resilience_radar import hex_to_rgb  # reuse for luminance calc


def _luminance(hex_color: str) -> float:
    r, g, b = hex_to_rgb(hex_color)

    def srgb(u):
        x = u / 255.0
        return x / 12.92 if x <= 0.03928 * 255 else ((x + 0.055) / 1.055) ** 2.4

    R, G, B = srgb(r), srgb(g), srgb(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B


def _auto_fg_for(bg_hex: str) -> str:
    return "#111111" if _luminance(bg_hex) > 0.5 else "#FFFFFF"


def scorecard(value_str: str, subtitle: str, *, bg_hex: str | None = None) -> None:
    style = ""
    if bg_hex:
        fg = _auto_fg_for(bg_hex)
        style = f' style="background:{bg_hex};color:{fg}"'
    st.markdown(
        f"""
        <div class="score-card"{style}>
            <div class="score-val">{value_str}</div>
            <div class="score-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def guidance_preview_for(
    tid: int, level_or_na, guidance_index: dict[int, dict[int, list[str]]]
) -> str:
    """Return a short single-line hint for current level (first bullet)."""
    if isinstance(level_or_na, int):
        bullets = guidance_index.get(tid, {}).get(level_or_na, [])
        return f"{level_or_na} — {bullets[0]}" if bullets else ""
    return ""


def topic_card(
    *,
    topic_id: int,
    topic_title: str,
    default_value,  # "N/A" or int
    default_comment: str,
    guidance_index: dict[int, dict[int, list[str]]],
    rating_key: str,
    comment_key: str,
    on_focus_key: str,
    help_text: str = "Choose N/A if not applicable.",
) -> None:
    """Render a single topic card with rating + comment and a 'Full guidance' focus button."""
    from app.ui.rate_topics import RATING_OPTIONS  # avoid circular import at module load time

    preview = guidance_preview_for(topic_id, default_value, guidance_index)

    st.markdown(
        f'<article class="topic-card" aria-labelledby="t{topic_id}">', unsafe_allow_html=True
    )
    st.markdown(f'<h3 id="t{topic_id}">{topic_title}</h3>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<label for="rate">CMMI rating</label>', unsafe_allow_html=True)
        st.select_slider(
            "CMMI (N/A–5)",
            options=RATING_OPTIONS,
            value=default_value,
            key=rating_key,
            help=help_text,
        )
        if preview:
            st.markdown(f'<p class="hint">{preview}</p>', unsafe_allow_html=True)
    with c2:
        st.markdown('<label for="comment">Comment</label>', unsafe_allow_html=True)
        st.text_area("Comment", value=default_comment, key=comment_key, height=70)

    if st.button("Full guidance", key=f"focus_{topic_id}", help="Show full guidance at right"):
        st.session_state[on_focus_key] = topic_id

    st.markdown("</article>", unsafe_allow_html=True)
