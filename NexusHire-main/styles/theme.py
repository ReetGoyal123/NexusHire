# styles/theme.py
# Injects global CSS into Streamlit pages — "Slate & Teal" palette:
# neutral slate surfaces, teal accent, no blue/purple.

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg: #f7f8fa;
  --surface: #ffffff;
  --surface2: #f1f3f5;
  --surface3: #eef0f2;
  --border: rgba(15,23,42,0.08);
  --border2: #e5e8eb;
  --accent: #0f766e;
  --accent2: #14b8a6;
  --accent3: #16a34a;
  --warn: #b45309;
  --danger: #dc2626;
  --text: #1a1f2b;
  --muted: #94a3b8;
  --muted2: #64748b;
  --sidebar-bg: #0f172a;
}

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }

[data-testid="stSidebar"] {
  background: var(--sidebar-bg) !important;
  border-right: none !important;
  min-width: 256px !important;
  max-width: 256px !important;
}
[data-testid="stSidebarNav"] { display: none; }

.stTextInput > div > div > input,
.stSelectbox > div > div {
  background: var(--surface) !important;
  border: 1.5px solid var(--border2) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(15,118,110,0.10) !important;
}
.stTextInput > label {
  font-size: 13px !important;
  font-weight: 500 !important;
  color: var(--muted2) !important;
  margin-bottom: 4px !important;
}

.stButton > button,
.stFormSubmitButton > button {
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 10px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  padding: 10px 22px !important;
  transition: all 0.2s !important;
  box-shadow: 0 2px 8px rgba(15,118,110,0.18) !important;
  letter-spacing: 0.1px !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
  background: #0d5c56 !important;
  box-shadow: 0 4px 16px rgba(15,118,110,0.30) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:active,
.stFormSubmitButton > button:active {
  transform: translateY(0px) !important;
}
.stButton > button:disabled,
.stFormSubmitButton > button:disabled {
  background: var(--border2) !important;
  color: var(--muted) !important;
  box-shadow: none !important;
}
/* Streamlit renders button labels through the same markdown <p> used for
   body text elsewhere on the page, and div[data-testid="stMarkdownContainer"]
   p below sets a muted gray on every such <p> with !important — that rule is
   more specific than the button's own color, so it was winning and making
   button labels the same low-contrast gray as regular text instead of white
   (near-invisible against the teal background until :hover changed the
   background enough to reveal it). Covers both .stButton (st.button) and
   .stFormSubmitButton (st.form_submit_button) — Streamlit renders these as
   two different components with separate wrapper classes, so both need it. */
.stButton > button p,
.stButton > button div[data-testid="stMarkdownContainer"] p,
.stFormSubmitButton > button p,
.stFormSubmitButton > button div[data-testid="stMarkdownContainer"] p {
  color: #fff !important;
}
.stButton > button:disabled p,
.stButton > button:disabled div[data-testid="stMarkdownContainer"] p,
.stFormSubmitButton > button:disabled p,
.stFormSubmitButton > button:disabled div[data-testid="stMarkdownContainer"] p {
  color: var(--muted) !important;
}
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
  border-radius: 6px !important;
}
.stProgress { height: 8px !important; }
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface3) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  border: 1.5px solid var(--border2) !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  color: var(--muted2) !important;
}
.stTabs [aria-selected="true"] {
  background: var(--surface) !important;
  color: var(--text) !important;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08) !important;
}
.stFileUploader > div {
  background: var(--surface) !important;
  border: 2px dashed rgba(15,118,110,0.25) !important;
  border-radius: 12px !important;
}
.stFileUploader label {
  font-size: 13px !important;
  color: var(--muted2) !important;
}
.stAlert {
  border-radius: 10px !important;
  font-size: 13px !important;
}
.stSuccess {
  background: rgba(22,163,74,0.08) !important;
  border: 1px solid rgba(22,163,74,0.2) !important;
  color: #14532d !important;
}
.stWarning {
  background: rgba(180,83,9,0.08) !important;
  border: 1px solid rgba(180,83,9,0.2) !important;
}
div[data-testid="stMarkdownContainer"] p {
  color: var(--muted2) !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
}
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d8dce1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #c2c8d0; }
</style>
"""

SHARED_CARD_CSS = """
<style>
/* ── STAT CARD ── */
.nx-card {
  border-radius: 14px;
  padding: 20px 22px;
  border: 1px solid var(--border);
  background: var(--surface);
  position: relative;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  margin-bottom: 12px;
}
.nx-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.08); }
.nx-card-accent { position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.nx-card-title { font-size: 12px; color: var(--muted); font-weight: 600; letter-spacing: 0.3px; margin-bottom: 8px; text-transform: uppercase; }
.nx-card-value { font-family: 'Space Grotesk', sans-serif; font-size: 30px; font-weight: 800; letter-spacing: -0.5px; }
.nx-card-sub { font-size: 12px; color: var(--muted2); margin-top: 6px; }
.nx-card-sub.up { color: #16a34a; }
.nx-card-sub.down { color: #dc2626; }
.nx-card-sub.warn { color: #b45309; }
.nx-card-icon { position: absolute; top: 18px; right: 18px; font-size: 22px; opacity: 0.7; }

/* ── STATUS PILL ── */
.pill { display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }
.pill-green { background: rgba(22,163,74,0.1); color: #16a34a; }
.pill-red   { background: rgba(220,38,38,0.1);  color: #dc2626; }
.pill-amber { background: rgba(180,83,9,0.1); color: #b45309; }
.pill-teal  { background: rgba(15,118,110,0.1); color: #0f766e; }

/* ── SECTION HEADER ── */
.nx-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.nx-section-title { font-family: 'Space Grotesk', sans-serif; font-size: 16px; font-weight: 700; color: var(--text); }
.nx-badge { font-size: 11px; font-weight: 700; background: rgba(15,118,110,0.10); color: #0f766e; padding: 3px 10px; border-radius: 20px; }

/* ── CARD WRAPPER ── */
.lc-card {
  background: #ffffff;
  border: 1.5px solid #e5e8eb;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  margin-bottom: 16px;
  transition: box-shadow 0.2s;
}
.lc-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.lc-card-header {
  padding: 16px 22px;
  border-bottom: 1px solid #eef0f2;
  display: flex; align-items: center; justify-content: space-between;
}
.lc-card-title {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700; font-size: 15px; color: #1a1f2b;
}
.lc-card-body { padding: 20px 22px; }
.lc-badge {
  font-size: 11px; font-weight: 700;
  background: rgba(15,118,110,0.08); color: #0f766e;
  padding: 3px 10px; border-radius: 20px;
}

/* ── AI CHAT BUBBLES ── */
.ai-bubble {
  background: #f0faf8;
  border-left: 3px solid #0f766e;
  border-radius: 0 12px 12px 0;
  padding: 14px 18px; margin: 12px 0;
}
.user-bubble {
  background: #f4faf1;
  border-left: 3px solid #16a34a;
  border-radius: 0 12px 12px 0;
  padding: 14px 18px; margin: 8px 0;
}
.bubble-label {
  font-size: 11px; color: #94a3b8; margin-bottom: 6px;
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}
.bubble-text {
  font-size: 14px; color: #1a1f2b; line-height: 1.65;
}
</style>
"""


def inject_theme():
    import streamlit as st
    st.markdown(THEME_CSS + SHARED_CARD_CSS, unsafe_allow_html=True)
