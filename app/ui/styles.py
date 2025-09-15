import streamlit as st

# Consolidated CSS with theme tokens + dark-mode fix for scorecards
BASE_CSS = """
<style>
:root{
  --space-2:.5rem; --space-3:.75rem; --space-4:1rem; --space-6:1.5rem;
  --radius:12px; --brand:#204e8a; --muted:#666; --border:#e6e6e6;

  /* Card tokens (light default) */
  --card-bg:#ffffff; --card-fg:#111827; --card-sub:#6b7280; --card-border:#e5e7eb;
  --pill-bg:#F4F4F4; --pill-fg:#111827;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark){
  :root{
    --card-bg:#111827; --card-fg:#f3f4f6; --card-sub:#cbd5e1; --card-border:#374151;
    --pill-bg:#1f2937; --pill-fg:#f3f4f6;
  }
}

/* General spacing polish */
.stAppMainBlockContainer { padding-top: 0.5rem; }
div.block-container { padding-top: 1rem; }

/* Sticky mini toolbar */
.mini-toolbar{
  position: sticky; top: 0; z-index: 1000; background: #fff;
  border-bottom: 1px solid #eee; padding: .5rem .25rem .6rem; margin: 0 0 .75rem 0;
}
.mini-toolbar .crumbs{ font-weight:600; }
.mini-toolbar .pill{
  background:var(--pill-bg); color:var(--pill-fg);
  border-radius:999px; padding:.25rem .6rem; font-size:.9rem; display:inline-block; white-space:nowrap;
}

/* Cards & drawer */
.theme-workspace { display:grid; grid-template-columns:minmax(520px,1fr) minmax(320px,36%); gap:var(--space-4); align-items:start; }
.topic-list { display:flex; flex-direction:column; gap: var(--space-3); }
.topic-card { border:1px solid var(--border); border-radius:var(--radius); padding: var(--space-4); background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.04); }
.topic-card h3 { margin:0 0 .5rem 0; font-size:1.05rem; }
.topic-card .hint { color: var(--muted); font-size:.9rem; margin:.25rem 0 0 0; }
.drawer { position:sticky; top:1rem; max-height:82vh; overflow:auto; border-left:1px solid #eee; padding-left: var(--space-4); }
.drawer h2 { margin-top:0; font-size:1.1rem; }
.level-title { margin:.75rem 0 .25rem; }
.level-title.is-current { font-weight:700; }

/* Scorecards (theme aware) */
.score-card{
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  color: var(--card-fg);
}
.score-val{ font-size: 2.2rem; font-weight: 700; color: var(--card-fg) !important; }
.score-sub{ color: var(--card-sub) !important; font-size: 0.85rem; }

/* Misc */
.progress-pill{ background:var(--pill-bg); color:var(--pill-fg); padding:4px 10px; border-radius:999px; font-size:0.85rem; }
button:focus, select:focus, textarea:focus { outline:3px solid rgba(32,78,138,.35); outline-offset:2px; }
</style>
"""


def inject() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
