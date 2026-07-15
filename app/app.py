"""
app.py
Chat-style interface for "AI SQL Assistant" — an AI agent that turns natural
language questions into SQL, runs them safely, and explains the results.

Run with:
    streamlit run app/app.py
"""

import streamlit as st
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sql_agent import generate_sql, validate_sql, run_sql, explain_result, UnsafeQueryError

st.set_page_config(
    page_title="✨ AI SQL Assistant",
    page_icon="✨",
    layout="centered"
)

# ---------------------------------------------------------------------------
# STYLING
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* Override Streamlit's own theme variables at the root — this is what
   actually removes the white bars, since built-in components (like the
   fixed chat input bar) read these vars rather than hardcoded colors. */
:root, .stApp {
    --background-color: #0D0D14 !important;
    --secondary-background-color: #16161F !important;
    --text-color: #ECEBF5 !important;

    --bg: #0D0D14;
    --surface: #16161F;
    --surface-2: #1E1E2A;
    --card-glass: rgba(255, 255, 255, 0.03);
    --border: #2B2B3A;
    --violet: #8C7AE6;
    --violet-glow: rgba(140, 122, 230, 0.15);
    --amber: #F0A85E;
    --amber-glow: rgba(240, 168, 94, 0.15);
    --text: #ECEBF5;
    --text-muted: #8A8AA3;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stBottom"],
[data-testid="stBottomBlockContainer"], [data-testid="stHeader"] {
    background-color: var(--bg) !important;
}
#MainMenu, footer, header {visibility: hidden;}
.block-container { padding-top: 2.2rem !important; max-width: 760px; }

/* ---------- Fade-in for new content ---------- */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
.msg-row, .feature-card, .stat-card { animation: fadeInUp 0.35s ease both; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] [data-testid] { background: transparent !important; }

.brand-row { display:flex; align-items:center; gap:10px; margin-bottom: 1rem; }
.brand-mark {
    width: 30px; height: 30px; border-radius: 8px;
    background: var(--violet-glow); border: 1px solid var(--violet);
    color: var(--violet); display:flex; align-items:center; justify-content:center;
    font-family: 'Space Grotesk', sans-serif; font-weight:700; font-size:1rem;
}
.brand-word { font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:1.05rem; color: var(--text) !important; }

.sidebar-eyebrow {
    font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.12em;
    color: var(--violet) !important; text-transform: uppercase;
    display: flex; align-items: center; gap: 6px; margin-bottom: 1rem;
}
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--violet); box-shadow: 0 0 6px var(--violet); animation: pulse 2s infinite ease-in-out; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }

.sidebar-section-label {
    font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.1em;
    color: var(--text-muted) !important; text-transform: uppercase; margin: 1.3rem 0 0.6rem 0;
}
.stat-pill {
    font-family: 'JetBrains Mono', monospace; font-size: 0.73rem; color: var(--text-muted) !important;
    background: var(--surface-2); border: 1px solid var(--border); border-radius: 6px;
    padding: 5px 10px; display: inline-block; margin: 2px 3px 2px 0;
}
.stat-pill b { color: var(--violet) !important; font-weight: 500; }
.arch-note { font-family: 'Inter', sans-serif; font-size: 0.81rem; color: var(--text-muted) !important; line-height: 1.6; }

.sidebar-footer {
    margin-top: 2rem; padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-family: 'Inter', sans-serif; font-size: 0.82rem; line-height: 1.7;
}
.sidebar-footer .role { color: var(--violet) !important; font-size: 0.78rem; }
.sidebar-footer .stack { color: var(--text-muted) !important; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; }

/* ---------- Main header ---------- */
.main-headline {
    font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 3rem;
    line-height: 1.1; color: var(--text) !important; margin-bottom: 24px;
    background: linear-gradient(135deg, #ECEBF5 40%, var(--violet) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.main-subtitle {
    font-family: 'Inter', sans-serif; font-size: 18px; color: var(--text-muted) !important;
    margin-bottom: 20px;
}

/* ---------- Recruiter stat cards ---------- */
.stat-card-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 32px; }
.stat-card {
    flex: 1; min-width: 130px;
    background: var(--card-glass); backdrop-filter: blur(8px);
    border: 1px solid var(--border); border-radius: 12px;
    padding: 14px 16px; text-align: center;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.stat-card:hover { transform: translateY(-3px); border-color: var(--violet); }
.stat-card .value { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.15rem; color: var(--violet); }
.stat-card .label { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }

/* ---------- Feature glass cards ---------- */
.feature-grid { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 32px; }
.feature-card {
    background: var(--card-glass); backdrop-filter: blur(8px);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 10px 14px; display: flex; align-items: center; gap: 8px;
    font-family: 'Inter', sans-serif; font-size: 0.82rem; color: var(--text);
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.feature-card:hover { transform: translateY(-3px); border-color: var(--amber); box-shadow: 0 4px 16px rgba(240,168,94,0.12); }
.feature-card .check { color: var(--amber); font-weight: 600; }

/* ---------- Custom chat bubbles ---------- */
.msg-row { display: flex; margin: 14px 0; gap: 10px; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }

.avatar-badge {
    width: 28px; height: 28px; min-width:28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 500;
    margin-top: 2px;
}
.avatar-user { background: var(--amber-glow); border: 1px solid var(--amber); color: var(--amber); }
.avatar-agent { background: var(--violet-glow); border: 1px solid var(--violet); color: var(--violet); }

.bubble {
    max-width: 78%; padding: 12px 16px; border-radius: 14px;
    font-family: 'Inter', sans-serif; font-size: 0.95rem; line-height: 1.55;
    color: var(--text);
}
.bubble-user { background: var(--surface-2); border: 1px solid var(--border); border-top-right-radius: 4px; }
.bubble-agent { background: var(--surface); border: 1px solid var(--border); border-left: 2px solid var(--violet); border-top-left-radius: 4px; }

.msg-label {
    font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 4px; opacity: 0.7;
}

.guardrail-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--amber);
    background: var(--amber-glow); border: 1px solid rgba(240, 168, 94, 0.3);
    border-radius: 6px; padding: 4px 9px; display: inline-block; margin: 8px 0 0 38px;
}

/* ---------- Sidebar example buttons ---------- */
.stButton > button {
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.76rem !important;
    background: var(--surface-2) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important; border-radius: 8px !important;
    text-align: left !important; transition: border-color 0.15s ease, transform 0.15s ease !important;
}
.stButton > button:hover { border-color: var(--violet) !important; color: var(--violet) !important; transform: translateY(-2px); }

/* ---------- Chat input — bigger, rounded, dark, no white leakage ---------- */
[data-testid="stChatInput"] {
    background: var(--bg) !important;
    border-top: 1px solid var(--border) !important;
    padding: 15px !important;
}
[data-testid="stChatInput"] > div {
    background: #171822 !important;
    border: 1px solid #2b2b3a !important;
    border-radius: 16px !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    min-height: 52px !important;
    font-size: 0.95rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-muted) !important; }
[data-testid="stChatInput"] button {
    background: var(--violet) !important; border-radius: 10px !important;
    transition: box-shadow 0.2s ease !important;
}
[data-testid="stChatInput"] button:hover { box-shadow: 0 0 14px var(--violet-glow) !important; }
[data-testid="stChatInput"] svg { color: var(--bg) !important; fill: var(--bg) !important; }

/* ---------- Status widget — wrapped as a proper card ---------- */
[data-testid="stStatusWidget"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 4px 6px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25) !important;
}
[data-testid="stStatusWidget"] p { font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem !important; }

/* ---------- Expander (agent reasoning) ---------- */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important; border-radius: 10px !important;
    margin-left: 38px; background: var(--surface) !important;
    transition: border-color 0.2s ease;
}
[data-testid="stExpander"]:hover { border-color: var(--violet) !important; }
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; color: var(--violet) !important;
}
.stCodeBlock, pre { background: var(--surface-2) !important; border: 1px solid var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand-row">
        <div class="brand-mark">✨</div>
        <div class="brand-word">AI SQL Assistant</div>
    </div>
    <div class="sidebar-eyebrow"><span class="status-dot"></span>AGENT ONLINE</div>
    <div class="arch-note">Turns plain-English questions into SQL, runs them safely,
    and explains the results — with memory across follow-up questions.</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-label">Dataset</div>', unsafe_allow_html=True)
    st.markdown("""
    <span class="stat-pill"><b>9,994</b> orders</span>
    <span class="stat-pill"><b>21</b> columns</span>
    <span class="stat-pill"><b>4</b> regions</span>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-label">How it works</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="arch-note">1&nbsp;&nbsp;Schema + sample rows sent to the LLM<br>'
        '2&nbsp;&nbsp;LLM generates SQL<br>'
        '3&nbsp;&nbsp;Guardrail blocks anything but SELECT<br>'
        '4&nbsp;&nbsp;Query runs on a read-only DB<br>'
        '5&nbsp;&nbsp;LLM explains the result</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="sidebar-section-label">Try asking</div>', unsafe_allow_html=True)
    EXAMPLE_QUESTIONS = [
        "Which category has the worst margin on 40%+ discounts?",
        "Top 5 states by total sales?",
        "Which region has the highest profit?",
        "Average discount in Furniture?",
    ]
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if st.button(q, key=f"ex_{i}", use_container_width=True):
            st.session_state["pending_prompt"] = q

    st.markdown("""
    <div class="sidebar-footer">
        Built by <b style="color:var(--text) !important;">Amrutha K</b><br>
        <span class="role">AI Application Developer</span><br>
        <span class="stack">Python • SQL • Streamlit • Llama 3.3</span>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# MAIN HEADER
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-headline">Ask your data anything</div>
<div class="main-subtitle">Natural language → SQL → Safe execution → Insights</div>
""", unsafe_allow_html=True)

# Recruiter-friendly stat cards
st.markdown("""
<div class="stat-card-row">
    <div class="stat-card"><div class="value">9,994</div><div class="label">Rows</div></div>
    <div class="stat-card"><div class="value">SQL</div><div class="label">Agent</div></div>
    <div class="stat-card"><div class="value">✓</div><div class="label">Memory</div></div>
    <div class="stat-card"><div class="value">✓</div><div class="label">Read Only</div></div>
</div>
""", unsafe_allow_html=True)

# Feature glass cards
st.markdown("""
<div class="feature-grid">
    <div class="feature-card"><span class="check">✔</span> Natural Language</div>
    <div class="feature-card"><span class="check">✔</span> SQL Generation</div>
    <div class="feature-card"><span class="check">✔</span> Read-only Database</div>
    <div class="feature-card"><span class="check">✔</span> Context Memory</div>
    <div class="feature-card"><span class="check">✔</span> Safety Guardrails</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# CHAT STATE + RENDER HELPERS
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sql_history" not in st.session_state:
    st.session_state.sql_history = []


def render_user_bubble(content):
    st.markdown(f"""
    <div class="msg-row user">
        <div class="bubble bubble-user">
            <div class="msg-label" style="color:var(--amber)">You</div>
            {content}
        </div>
        <div class="avatar-badge avatar-user">AM</div>
    </div>
    """, unsafe_allow_html=True)


def render_agent_bubble(content):
    st.markdown(f"""
    <div class="msg-row assistant">
        <div class="avatar-badge avatar-agent">✨</div>
        <div class="bubble bubble-agent">
            <div class="msg-label" style="color:var(--violet)">Agent</div>
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)


for msg in st.session_state.messages:
    if msg["role"] == "user":
        render_user_bubble(msg["content"])
    else:
        render_agent_bubble(msg["content"])
        if "sql" in msg:
            st.markdown('<span class="guardrail-badge">✓ SQL validated · SELECT-only · read-only DB</span>', unsafe_allow_html=True)
            with st.expander("▾ View Generated SQL"):
                st.code(msg["sql"], language="sql")
                st.markdown("**Result**")
                st.dataframe(msg["result"], use_container_width=True)


def process_question(question: str):
    render_user_bubble(question)
    st.session_state.messages.append({"role": "user", "content": question})

    try:
        with st.status("Reading schema...", expanded=True) as status:
            status.write("Loaded table structure and sample rows")
            time.sleep(0.25)

            status.update(label="Generating SQL query...")
            sql = generate_sql(question, history=st.session_state.sql_history)
            preview = sql if len(sql) <= 60 else sql[:60] + "..."
            status.write(f"Generated: `{preview}`")

            status.update(label="Running safety check...")
            validate_sql(sql)
            status.write("Passed — SELECT-only, no forbidden keywords")

            status.update(label="Executing against database...")
            result_df = run_sql(sql)
            status.write(f"Returned {len(result_df)} row(s)")

            status.update(label="Writing plain-English answer...")
            answer = explain_result(question, sql, result_df)

            status.update(label="Done", state="complete", expanded=False)

        render_agent_bubble(answer)
        st.markdown('<span class="guardrail-badge">✓ SQL validated · SELECT-only · read-only DB</span>', unsafe_allow_html=True)

        with st.expander("▾ View Generated SQL"):
            st.code(sql, language="sql")
            st.markdown("**Result**")
            st.dataframe(result_df, use_container_width=True)

        st.session_state.messages.append({"role": "assistant", "content": answer, "sql": sql, "result": result_df})
        st.session_state.sql_history.append({"question": question, "sql": sql})

    except UnsafeQueryError:
        msg = "This question produced a query that was blocked for safety reasons. Try rephrasing it as a simple data lookup."
        render_agent_bubble(msg)
        st.session_state.messages.append({"role": "assistant", "content": msg})

    except Exception as e:
        msg = f"Something went wrong: {e}"
        render_agent_bubble(msg)
        st.session_state.messages.append({"role": "assistant", "content": msg})


if "pending_prompt" in st.session_state:
    q = st.session_state.pop("pending_prompt")
    process_question(q)

user_input = st.chat_input("Ask a question about the data...")
if user_input:
    process_question(user_input)
