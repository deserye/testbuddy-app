from __future__ import annotations

import os
import base64
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from rag_engine import LocalVectorStore, build_chunks, ensure_sample_documents, save_uploaded_file, serialize_results

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]

PROJECT_DIR = Path(__file__).resolve().parent
ASSET_DIR = PROJECT_DIR / "assets"
LOGO_PATH = ASSET_DIR / "carepath_logo_mark.png"
HERO_IMAGE_PATH = ASSET_DIR / "carepath_hero_family.jpg"
SCHEME_IMAGE_PATH = ASSET_DIR / "carepath_scheme_illustration.jpg"
CONVERSATION_IMAGE_PATH = ASSET_DIR / "carepath_conversation_illustration.jpg"
DOCUMENT_DIR = PROJECT_DIR / "documents"
SAMPLE_DOCUMENT_DIR = PROJECT_DIR / "sample_documents"

st.set_page_config(
    page_title="CarePath: A CareShield Life and ElderShield Information Navigator",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Official sources and safety language
# -----------------------------------------------------------------------------
CARESHIELD_URL = "https://www.cpf.gov.sg/member/healthcare-financing/careshield-life"
ELDERSHIELD_URL = "https://www.cpf.gov.sg/member/healthcare-financing/eldershield"
MOH_SUPPLEMENTS_URL = "https://www.moh.gov.sg/managing-expenses/schemes-and-subsidies/careshield-life/careshield-life-and-eldershield-supplements/"
AIC_CARESHIELD_URL = "https://www.aic.sg/Financial-Assistance/CareShield-Life"
CPF_MEMBER_URL = "https://www.cpf.gov.sg/member"
MOH_CARESHIELD_URL = "https://www.moh.gov.sg/managing-expenses/schemes-and-subsidies/careshield-life/careshield-life/"

DISCLAIMER = (
    "IMPORTANT NOTICE: This web application is a prototype developed for educational "
    "purposes only. The information provided here is NOT intended for real-world usage "
    "and should not be relied upon for making any decisions, especially those related "
    "to financial, legal, or healthcare matters.\n\n"
    "Furthermore, please be aware that the LLM may generate inaccurate or incorrect "
    "information. You assume full responsibility for how you use any generated output.\n\n"
    "Always consult with qualified professionals for accurate and personalised advice."
)

SOURCE_CONTEXT = f"""
You are an educational explainer about Singapore long-term-care protection. Use only the following official-source context for factual claims, and do not invent current rules, amounts, dates, or eligibility outcomes.

CPF Board — CareShield Life: {CARESHIELD_URL}
CPF Board describes CareShield Life as a long-term-care insurance scheme that provides financial support and monthly cash payouts if an insured person develops severe disability. Its public page discusses joining context by birth year, lifelong coverage, subsidies and premium support, MediSave payment, claims, the six activities of daily living, and official premium-check and application services. CPF Board states that all Singapore Citizens and Permanent Residents are eligible to join, but timing depends on birth year; it describes automatic coverage at age 30 for those born in 1980 or after, and optional participation for those born in 1979 or earlier, subject to the detailed rules on its page.

CPF Board — ElderShield: {ELDERSHIELD_URL}
CPF Board describes ElderShield as a closed long-term-care insurance scheme targeted at severe disability. It explains that plan benefits depend on the historical scheme joined and provides a secure route to check coverage through CPF member services. It also explains claims in relation to inability to perform three of six activities of daily living.

AIC — CareShield Life: {AIC_CARESHIELD_URL}
AIC provides public guidance on how to qualify, how the scheme works, how to apply, documents needed, eFASS, MOH-accredited severe-disability assessors, and applying on behalf of someone who lacks mental capacity.

MOH — CareShield Life and ElderShield Supplements: {MOH_SUPPLEMENTS_URL}
MOH explains that supplements add coverage on top of basic CareShield Life or ElderShield plans and publishes comparison materials. Supplement plans differ, so users should contact an insurer for product-specific information rather than rely on a generic assistant.
"""

CARE_COMPARISON = pd.DataFrame(
    [
        ["CareShield Life", "Current long-term-care scheme", "Monthly cash payouts for life if claim criteria are met", "Check the current joining and claim rules on CPF Board"],
        ["ElderShield", "Closed historical scheme", "Plan-dependent historical payouts and duration", "Check actual coverage through CPF member services"],
        ["Supplements", "Additional private coverage", "Benefits differ by plan", "Read MOH comparison materials and contact the insurer"],
    ],
    columns=["Topic", "High-level description", "What the app can explain", "Official next step"],
)

ADL_TABLE = pd.DataFrame(
    [
        ["Washing", "Washing in a bath or shower, including getting in and out, or washing by other means."],
        ["Dressing", "Putting on, taking off, securing, and unfastening garments and relevant appliances."],
        ["Feeding", "Feeding oneself after food has been prepared and made available."],
        ["Toileting", "Using the toilet or managing bowel and bladder function with appropriate aids."],
        ["Walking or moving around", "Moving indoors from room to room on level surfaces."],
        ["Transferring", "Moving from a bed to an upright chair or wheelchair, and vice versa."],
    ],
    columns=["Activity of daily living", "Plain-language description"],
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root { --app-bg: var(--background-color, #fffdf9); --surface: var(--secondary-background-color, #ffffff); --ink: var(--text-color, #203246); --muted: #64758a; --navy: #27506a; --teal: #158477; --mint: #e5f6f0; --coral: #e98268; --cream: #fffdf9; --line: var(--border-color, #e3ebe8); --sidebar-bg: var(--secondary-background-color, #eff8f5); --sidebar-ink: var(--text-color, #29475d); --notice-bg: #fff6e8; --notice-ink: #674a16; --source-bg: #edf8f6; --source-ink: #245b59; }
        body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) { --app-bg: #0e1117; --surface: #171b24; --ink: #f1f5f9; --muted: #b6c1cf; --navy: #b9d9e9; --line: #323a48; --sidebar-bg: #151b25; --sidebar-ink: #e4edf5; --notice-bg: #3b2f1d; --notice-ink: #f8d995; --source-bg: #163434; --source-ink: #b9eee4; }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; color: var(--ink); letter-spacing: -0.025em; }
        h1 { font-size: clamp(2.2rem, 4vw, 4.15rem) !important; line-height: 0.98 !important; }
        h2 { font-size: 2rem !important; }
        .stApp { background: var(--app-bg); color: var(--ink); }
        [data-testid="stSidebar"] { background: var(--sidebar-bg); border-right: 1px solid var(--line); }
        [data-testid="stSidebar"] * { color: var(--sidebar-ink) !important; }
        [data-testid="stSidebar"] hr { border-color: var(--line); }
        [data-testid="stSidebar"] .stRadio label, [data-testid="stSidebar"] [role="radiogroup"] label { width: 100%; min-height: 46px; display: flex; align-items: center; gap: .55rem; padding: .72rem .78rem; margin: .18rem 0; border-radius: 12px; cursor: pointer; box-sizing: border-box; } [data-testid="stSidebar"] .stRadio label:hover, [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #dff1ec; } body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) [data-testid="stSidebar"] .stRadio label:hover, body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #223a3b; } [data-testid="stSidebar"] input[type="radio"] { accent-color: var(--teal); transform: scale(1.12); }
        .hero { background: linear-gradient(135deg, #dff6ee 0%, #e6f1fb 54%, #fff0e7 100%); color: var(--ink); padding: 3.35rem 3.7rem; border-radius: 26px; position: relative; overflow: hidden; margin-bottom: 1.25rem; border: 1px solid var(--line); }
        body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) .hero { background: linear-gradient(135deg, #173833 0%, #1b3040 54%, #3a2b2c 100%); }
        .hero:after { content: ''; position: absolute; right: -95px; top: -125px; width: 370px; height: 370px; border-radius: 50%; border: 1px solid rgba(21,132,119,.18); box-shadow: 0 0 0 34px rgba(21,132,119,.07), 0 0 0 68px rgba(233,130,104,.06); }
        .brand-bar { display: flex; align-items: center; gap: .8rem; background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: .6rem .85rem; margin: -.35rem 0 1.15rem; box-shadow: 0 5px 16px rgba(16,42,67,.05); }
        .brand-bar img { width: 44px; height: 44px; object-fit: contain; border-radius: 12px; }
        .brand-name { font-family: 'Space Grotesk', sans-serif; font-size: 1.06rem; font-weight: 700; color: var(--ink); line-height: 1.1; }
        .brand-subtitle { color: var(--muted); font-size: .74rem; margin-top: .22rem; line-height: 1.25; }
        .hero h1, .hero p { color: var(--ink) !important; max-width: 730px; position: relative; z-index: 1; }
        .hero .eyebrow { color: var(--teal); position: relative; z-index: 1; }
        .hero p { color: var(--muted) !important; font-size: 1.1rem; line-height: 1.6; }
        .eyebrow { text-transform: uppercase; letter-spacing: .14em; color: var(--teal); font-size: .72rem; font-weight: 700; }
        .card { background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1.25rem 1.35rem; height: 100%; box-shadow: 0 6px 20px rgba(16,42,67,.04); }
        [data-testid="stImage"] img { border-radius: 20px; border: 1px solid #dbece8; box-shadow: 0 8px 24px rgba(16,42,67,.06); }
        .card h3 { margin-top: .2rem; font-size: 1.22rem; }
        .card p { color: var(--muted); line-height: 1.55; }
        .accent-card { border-top: 4px solid var(--coral); }
        .teal-card { border-top: 4px solid var(--teal); }
        .notice { background: var(--notice-bg); border: 1px solid #f3d49b; color: var(--notice-ink); border-radius: 14px; padding: 1rem 1.1rem; line-height: 1.55; }
        .source-strip { background: var(--source-bg); border-left: 4px solid var(--teal); border-radius: 8px; padding: .75rem 1rem; color: var(--source-ink); font-size: .9rem; }
        .metric-label { text-transform: uppercase; letter-spacing: .12em; font-size: .68rem; font-weight: 700; color: var(--muted); }
        .metric-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.55rem; font-weight: 700; color: var(--navy); }
        .step { border-left: 3px solid #b8ddd7; padding: .15rem 0 .9rem 1rem; margin-left: .4rem; }
        .step strong { color: var(--navy); }
        div[data-testid="stForm"] { background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1rem; }
        .stButton > button, .stDownloadButton > button { border-radius: 999px; border: 1px solid var(--line); color: var(--ink); font-weight: 600; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button { background: var(--teal); color: white; border: none; }
        a { color: var(--teal); font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_secret(name: str) -> str:
    value = os.getenv(name, "") or ""
    value = str(value).strip()
    if value:
        return value
    try:
        secret_value = st.secrets.get(name, "")
        return str(secret_value or "").strip()
    except Exception:
        return ""


def gate_if_configured() -> None:
    password = get_secret("APP_PASSWORD")
    if not password:
        return
    if st.session_state.get("authenticated"):
        return
    st.markdown('<div class="hero"><div class="eyebrow">Private educational prototype</div><h1>CarePath</h1><p>Enter the access password configured by the project owner to continue.</p></div>', unsafe_allow_html=True)
    entered = st.text_input("Access password", type="password")
    if st.button("Continue", type="primary"):
        if entered == password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


def disclaimer() -> None:
    with st.expander("Important prototype notice", expanded=True):
        st.warning(DISCLAIMER)


def page_header(eyebrow: str, title: str, intro: str) -> None:
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(intro)


def source_strip(text: str, url: str, label: str = "Read the official source") -> None:
    st.markdown(f'<div class="source-strip">{text} <a href="{url}" target="_blank">{label} ↗</a></div>', unsafe_allow_html=True)


def navigate_to(page: str) -> None:
    st.session_state["page"] = page
    st.session_state["page_selector"] = page


def sync_page_from_selector() -> None:
    st.session_state["page"] = st.session_state["page_selector"]


def render_brand_bar() -> None:
    if not LOGO_PATH.exists():
        return
    logo_uri = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    st.markdown(
        f'<div class="brand-bar"><img src="{logo_uri}" alt="CarePath logo mark"><div><div class="brand-name">CarePath</div><div class="brand-subtitle">CareShield Life and ElderShield information navigator</div></div></div>',
        unsafe_allow_html=True,
    )


def current_role() -> str:
    return st.session_state.get("role", "Guest")


def refresh_rag_store() -> LocalVectorStore:
    chunks = build_chunks(DOCUMENT_DIR)
    store = LocalVectorStore(chunks)
    st.session_state["rag_store"] = store
    st.session_state["rag_chunk_count"] = len(chunks)
    return store


def get_rag_store() -> LocalVectorStore:
    if "rag_store" not in st.session_state:
        return refresh_rag_store()
    return st.session_state["rag_store"]


def render_role_controls() -> None:
    with st.sidebar:
        st.markdown("### Access")
        role_choice = st.selectbox("Role", ["Guest", "User", "Admin"], key="role_choice")
        if role_choice == "Guest":
            st.session_state["role"] = "Guest"
            st.caption("Guest mode: guided pages only.")
            return
        password = st.text_input("Role password", type="password", key="role_password")
        if st.button("Sign in", key="role_sign_in", use_container_width=True):
            expected_name = "ADMIN_PASSWORD" if role_choice == "Admin" else "USER_PASSWORD"
            expected = get_secret(expected_name)
            accepted_demo_passwords = {"admin", "adminaibootcamp"} if role_choice == "Admin" else {"user", "useraibootcamp"}
            if (expected and password == expected) or (not expected and password in accepted_demo_passwords):
                st.session_state["role"] = role_choice
                st.success(f"Signed in as {role_choice}.")
                st.rerun()
            else:
                st.error("The role password did not match.")
        if current_role() != role_choice:
            st.caption("Sign in to activate this role.")
        else:
            st.caption(f"Active role: {current_role()}")


def rag_answer(query: str, results: list[dict[str, Any]]) -> str:
    context = "\n\n".join(
        f"[{item['document_name']} · {item.get('section', 'Source')} · page {item.get('page') or 'n/a'}]\n{item['text']}"
        for item in results
    )
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return "The local retrieval results are shown below. Add OPENAI_API_KEY to enable an optional generated synthesis.\n\n" + context
    model = get_secret("CARE_LLM_MODEL") or "gpt-4o-mini"
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    base_url = get_secret("OPENAI_API_BASE")
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are CarePath's source-grounded document assistant. Answer only from the supplied excerpts. Do not make medical, eligibility, claim, payout, or insurance decisions. Cite each material claim with the document name and section. State when the excerpts are insufficient."},
            {"role": "user", "content": f"Question: {query}\n\nRetrieved excerpts:\n{context}"},
        ],
        max_tokens=650,
    )
    choices = getattr(response, "choices", None) or []
    if not choices:
        return "No generated synthesis was returned. Review the retrieved excerpts below.\n\n" + context
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None) if message is not None else None
    return content or ("No generated synthesis was returned. Review the retrieved excerpts below.\n\n" + context)


def render_rag_query() -> None:
    page_header("04 · Document RAG", "Ask the CarePath document set", "Search the approved sample or admin-uploaded documents and inspect the retrieved excerpts behind the answer.")
    st.markdown('<div class="notice"><strong>Prototype boundary.</strong> This page demonstrates document retrieval. It is not a coverage checker, medical assessor, claims decision-maker, or official CPF Board service.</div>', unsafe_allow_html=True)
    if current_role() not in {"User", "Admin"}:
        st.warning("Sign in as User or Admin in the sidebar to query the indexed document set.")
        return
    store = get_rag_store()
    st.caption(f"Indexed chunks: {len(store.chunks)} · Active role: {current_role()}")
    if not store.chunks:
        st.info("No documents are indexed yet. An Admin can upload documents or load the sample set.")
        return
    with st.form("rag_query_form"):
        query = st.text_input("Ask a question about the indexed documents", placeholder="What is ElderShield and where should I verify personal coverage?")
        top_k = st.slider("Retrieved excerpts", 1, 8, 4)
        submitted = st.form_submit_button("Search documents", type="primary", use_container_width=True)
    if submitted and query.strip():
        results = store.search(query.strip(), top_k=top_k)
        st.session_state["rag_results"] = results
        st.session_state["rag_query"] = query.strip()
        with st.spinner("Retrieving relevant excerpts…"):
            try:
                st.session_state["rag_answer"] = rag_answer(query.strip(), results)
            except Exception as exc:
                st.session_state["rag_answer"] = "Retrieval succeeded, but the optional generated synthesis could not connect. Review the excerpts below. Technical detail: " + str(exc)[:180]
    if "rag_results" in st.session_state:
        st.markdown("### Grounded response")
        st.markdown(st.session_state.get("rag_answer", ""))
        st.markdown("### Retrieved source excerpts")
        for index, item in enumerate(st.session_state["rag_results"], start=1):
            page_label = f"Page {item['page']}" if item.get("page") else "Page not available"
            with st.expander(f"{index}. {item['document_name']} · {item['section']} · {page_label} · score {item['score']}"):
                st.write(item["text"])
                st.caption(f"Source excerpt: {item['source_excerpt']}")
        export_text = "# CarePath document query\n\nQuestion: " + st.session_state.get("rag_query", "") + "\n\nAnswer:\n" + st.session_state.get("rag_answer", "") + "\n\nRetrieved results:\n" + serialize_results(st.session_state["rag_results"])
        st.download_button("Download answer and citations", export_text, file_name="carepath_rag_result.md", mime="text/markdown", use_container_width=True)


def render_admin_documents() -> None:
    page_header("05 · Admin workspace", "Manage the CarePath document set", "Upload approved PDF, Markdown, or text documents, load the sample set, and rebuild the lightweight vector index.")
    if current_role() != "Admin":
        st.warning("Admin access is required for document management. Select Admin in the sidebar and sign in.")
        return
    st.markdown('<div class="notice"><strong>Admin boundary.</strong> Upload only approved public or project documents. Do not upload medical records, NRIC data, account information, confidential credentials, or other sensitive personal information.</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload documents", type=["pdf", "md", "txt"], accept_multiple_files=True)
    if st.button("Save uploaded documents", type="primary", disabled=not uploaded):
        for item in uploaded or []:
            save_uploaded_file(item, DOCUMENT_DIR)
        refresh_rag_store()
        st.success(f"Saved {len(uploaded or [])} document(s) and rebuilt the index.")
    if st.button("Load sample CarePath documents"):
        copied = ensure_sample_documents(DOCUMENT_DIR, SAMPLE_DOCUMENT_DIR)
        refresh_rag_store()
        st.success(f"Loaded {copied} sample document(s) and rebuilt the index.")
    st.markdown("### Current document set")
    files = sorted([path for path in DOCUMENT_DIR.iterdir() if path.is_file()]) if DOCUMENT_DIR.exists() else []
    if files:
        st.dataframe(pd.DataFrame([[path.name, path.suffix.lower(), path.stat().st_size] for path in files], columns=["Document", "Type", "Bytes"]), use_container_width=True, hide_index=True)
    else:
        st.info("No documents uploaded yet.")
    st.caption(f"Current indexed chunks: {st.session_state.get('rag_chunk_count', len(get_rag_store().chunks))}")


def render_home() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">Long-term-care learning companion · educational prototype</div><h1>Understand protection before you need it.</h1><p>CarePath brings CareShield Life, ElderShield, and caregiving support information into two practical, source-linked journeys.</p></div>', unsafe_allow_html=True)
    if HERO_IMAGE_PATH.exists():
        st.image(str(HERO_IMAGE_PATH), use_container_width=True, output_format="JPEG")
        st.caption("A calmer way to learn, prepare, and find the right official next step.")
    disclaimer()
    st.write("")
    st.markdown('<div class="eyebrow">Start with a scenario</div>', unsafe_allow_html=True)
    st.subheader("A clearer next step, without collecting sensitive data")
    st.markdown("Choose a learning pathway. Your broad answers stay in this session and are used only to organise public information and questions for further reading.")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="card teal-card"><div class="eyebrow">01 · Coverage</div><h3>Understand my scheme</h3><p>Learn the difference between CareShield Life, ElderShield, and supplements, then find the official route to check your own coverage.</p></div>', unsafe_allow_html=True)
        if st.button("Explore scheme coverage", use_container_width=True, key="home_coverage"):
            navigate_to("Understand my scheme")
            st.rerun()
    with right:
        st.markdown('<div class="card accent-card"><div class="eyebrow">02 · Caregiving</div><h3>Prepare for a care conversation</h3><p>Build a general checklist for speaking with AIC, CPF Board, MOH, a healthcare provider, or an accredited assessor.</p></div>', unsafe_allow_html=True)
        if st.button("Prepare a care conversation", use_container_width=True, key="home_care"):
            navigate_to("Care conversation")
            st.rerun()
    st.write("")
    st.markdown('<div class="eyebrow">What is inside</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        st.markdown('<div class="card"><div class="metric-label">01</div><div class="metric-value">Explain</div><p>Compare schemes and explain the six activities of daily living in plain language.</p></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card"><div class="metric-label">02</div><div class="metric-value">Prepare</div><p>Turn a broad situation into questions, documents to confirm, and official next steps.</p></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="card"><div class="metric-label">03</div><div class="metric-value">Ask</div><p>Use the optional chatbot for source-grounded concept questions, with verification reminders.</p></div>', unsafe_allow_html=True)
    st.write("")
    source_strip("Core content is based on public CPF Board, MOH, and AIC guidance.", CARESHIELD_URL)


def coverage_output(birth_band: str, focus: str, role: str) -> dict[str, Any]:
    prompts = []
    if birth_band == "Born in 1980 or after":
        prompts.append("CPF Board describes automatic CareShield Life coverage at age 30 for those born in 1980 or after, subject to the detailed official rules. Use the CPF Board page to verify the current position for a real person.")
    elif birth_band == "Born in 1979 or earlier":
        prompts.append("CPF Board describes ElderShield as a closed scheme and CareShield Life participation as optional for many people born in 1979 or earlier, with detailed exceptions. Check the official pages rather than assuming coverage.")
    else:
        prompts.append("Birth year is relevant to the CareShield Life and ElderShield context, but this prototype cannot determine which scheme covers a particular person.")
    if focus == "Claims and severe disability":
        prompts.append("Read the official explanation of the six activities of daily living and the role of an MOH-accredited assessor. The app cannot assess disability or predict claim approval.")
    elif focus == "Premiums and support":
        prompts.append("Explore official information on MediSave payment, subsidies, premium support, and the premium-check service. Do not enter an exact premium or account balance here.")
    elif focus == "Supplements":
        prompts.append("MOH explains that supplements provide additional coverage, but benefits differ. Use official comparison materials and contact an insurer for product-specific questions.")
    else:
        prompts.append("Start with the high-level scheme comparison, then use CPF Board’s secure member service to check actual coverage.")
    if role == "Family member or caregiver":
        prompts.append("AIC provides public guidance for applying on behalf of someone who lacks mental capacity, including additional documents and support routes.")
    else:
        prompts.append("For a personal coverage result, use CPF Board’s secure member services rather than entering personal details into this prototype.")
    return {"prompts": prompts}


def render_coverage() -> None:
    intro_col, visual_col = st.columns([1.18, 0.82], gap="large")
    with intro_col:
        page_header("01 · Coverage explorer", "Understand my long-term-care scheme", "Use broad context to learn what to read next. This is an educational explainer, not a coverage or eligibility checker.")
    with visual_col:
        if SCHEME_IMAGE_PATH.exists():
            st.image(str(SCHEME_IMAGE_PATH), use_container_width=True, output_format="JPEG")
            st.caption("A high-level map of protection concepts—not a personal coverage result.")
    source_strip("CPF Board provides the source-of-truth pages for CareShield Life and ElderShield coverage, benefits, premiums, and claims.", CARESHIELD_URL)
    st.write("")
    with st.form("coverage_form"):
        st.markdown("#### Choose the learning context")
        col1, col2 = st.columns(2)
        with col1:
            birth_band = st.selectbox("Broad birth-year context", ["Prefer not to say", "Born in 1980 or after", "Born in 1979 or earlier"], key="coverage_birth")
            role = st.selectbox("Who is this learning pathway for?", ["Myself", "Family member or caregiver", "General learning"], key="coverage_role")
        with col2:
            focus = st.selectbox("What do you want to understand?", ["General comparison", "Claims and severe disability", "Premiums and support", "Supplements"], key="coverage_focus")
            st.caption("Do not enter your name, exact age, NRIC number, health information, account details, or exact financial amounts.")
        submitted = st.form_submit_button("Build my learning pathway", type="primary", use_container_width=True)
    if submitted:
        st.session_state["coverage_result"] = coverage_output(birth_band, focus, role)
    if "coverage_result" in st.session_state:
        result = st.session_state["coverage_result"]
        st.write("")
        st.markdown('<div class="eyebrow">Your pathway</div>', unsafe_allow_html=True)
        st.subheader("Learn first, then verify through official services")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown('<div class="card"><div class="metric-label">Core topic</div><div class="metric-value">' + focus + '</div><p>A learning lens, not a personalised result.</p></div>', unsafe_allow_html=True)
        with m2:
            st.markdown('<div class="card"><div class="metric-label">Scheme context</div><div class="metric-value">Compare</div><p>CareShield Life and ElderShield have different joining and coverage histories.</p></div>', unsafe_allow_html=True)
        with m3:
            st.markdown('<div class="card"><div class="metric-label">Next step</div><div class="metric-value">Check</div><p>Use CPF Board’s secure member services for actual coverage.</p></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("#### Your learning prompts")
        for index, item in enumerate(result["prompts"], start=1):
            st.markdown(f'<div class="step"><strong>Prompt {index:02d}</strong><br>{item}</div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("#### High-level comparison")
        st.dataframe(CARE_COMPARISON, use_container_width=True, hide_index=True)
        st.markdown("#### Six activities of daily living")
        with st.expander("Open the plain-language explainer"):
            st.dataframe(ADL_TABLE, use_container_width=True, hide_index=True)
        chart = pd.DataFrame({"Scheme or topic": ["CareShield Life", "ElderShield", "Supplements"], "Public explanation scope": [5, 4, 3]}).set_index("Scheme or topic")
        st.bar_chart(chart, color="#087f70", height=220)
        st.caption("Relative breadth of the public explanation in this prototype; this is not a measure of coverage or value.")
        st.markdown(f"Continue with [CPF Board CareShield Life]({CARESHIELD_URL}), [CPF Board ElderShield]({ELDERSHIELD_URL}), or [CPF secure member services]({CPF_MEMBER_URL}).")
    st.info("This page does not determine coverage, interpret medical information, or predict a claim.")


def care_output(audience: str, task: str, destination: str) -> dict[str, Any]:
    checklist = []
    if task == "Understand a possible claim":
        checklist.extend(["Read the official claim criteria and the six activities of daily living.", "Ask which MOH-accredited assessor and application route applies.", "Confirm which documents AIC or the relevant agency requires."])
    elif task == "Apply or find application support":
        checklist.extend(["Open AIC’s CareShield Life application guidance and eFASS information.", "Prepare only the documents requested by the official service.", "If applying for someone who lacks mental capacity, check the additional-document guidance before starting."])
    elif task == "Support an older family member":
        checklist.extend(["Clarify whether the question concerns CareShield Life, ElderShield, or another support scheme.", "Write down questions for CPF Board, AIC, MOH, or the healthcare provider.", "Use official secure services for any coverage or account check."])
    else:
        checklist.extend(["Start with the official overview page for the selected destination.", "Separate general questions from personal account or health information.", "Keep a note of the official contact or e-service to use next."])
    checklist.append(f"Your intended destination is {destination}; verify the correct route on the official website before sharing any information.")
    if audience == "Caregiver or family member":
        checklist.append("Ask about consent, authority, and additional documents before acting on behalf of another person.")
    else:
        checklist.append("Do not share medical records, NRIC details, account numbers, or exact financial details with this prototype.")
    return {"checklist": checklist}


def render_care() -> None:
    intro_col, visual_col = st.columns([1.18, 0.82], gap="large")
    with intro_col:
        page_header("02 · Care conversation", "Prepare for a care or claim conversation", "Create a general checklist for the right public-service destination. The application cannot assess disability, interpret a medical report, or predict claim approval.")
    with visual_col:
        if CONVERSATION_IMAGE_PATH.exists():
            st.image(str(CONVERSATION_IMAGE_PATH), use_container_width=True, output_format="JPEG")
            st.caption("Use this journey to prepare questions—not to interpret a medical assessment.")
    source_strip("AIC provides practical guidance on applications, documents, assessors, eFASS, and support for caregivers.", AIC_CARESHIELD_URL)
    st.write("")
    with st.form("care_form"):
        st.markdown("#### Set the conversation context")
        col1, col2 = st.columns(2)
        with col1:
            audience = st.selectbox("Who are you preparing for?", ["Myself", "Caregiver or family member", "General learning"], key="care_audience")
            task = st.selectbox("What are you trying to do?", ["Understand a possible claim", "Apply or find application support", "Support an older family member", "Learn the general process"], key="care_task")
        with col2:
            destination = st.selectbox("Which destination are you preparing to contact?", ["CPF Board", "AIC", "MOH or healthcare provider", "Not sure yet"], key="care_destination")
            st.caption("Do not enter diagnoses, medical records, NRIC details, account numbers, addresses, or exact financial amounts.")
        submitted = st.form_submit_button("Build my conversation checklist", type="primary", use_container_width=True)
    if submitted:
        st.session_state["care_result"] = care_output(audience, task, destination)
    if "care_result" in st.session_state:
        result = st.session_state["care_result"]
        st.write("")
        st.markdown('<div class="eyebrow">Your checklist</div>', unsafe_allow_html=True)
        st.subheader("Questions and preparation prompts")
        left, right = st.columns([1.15, .85], gap="large")
        with left:
            for index, item in enumerate(result["checklist"], start=1):
                st.markdown(f'<div class="step"><strong>Step {index:02d}</strong><br>{item}</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card"><div class="metric-label">Care pathway principle</div><div class="metric-value">Ask, verify, prepare</div><p>Use this checklist to organise a conversation. Only the relevant official agency, assessor, or professional can advise on a real situation.</p></div>', unsafe_allow_html=True)
            st.write("")
            chart = pd.DataFrame({"Preparation area": ["Official route", "Documents", "Assessor or provider", "Authority / consent", "Verification"], "Checklist emphasis": [5, 5, 4, 4, 5]}).set_index("Preparation area")
            st.bar_chart(chart, color="#ed765e", height=240)
            st.caption("Relative emphasis in this generic checklist, not a score of the person or claim.")
        st.write("")
        st.markdown(f"Useful official destinations include [AIC CareShield Life guidance]({AIC_CARESHIELD_URL}), [CPF Board CareShield Life]({CARESHIELD_URL}), and [MOH CareShield Life information]({MOH_CARESHIELD_URL}).")
    st.info("This page is a preparation guide only. It does not provide medical, legal, insurance, or financial advice.")


def assistant_reply(messages: list[dict[str, str]]) -> str:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return "The optional chatbot is not connected yet. The guided tools remain available. Add OPENAI_API_KEY as a server-side environment variable or Streamlit secret to enable concept questions."
    base_url = get_secret("OPENAI_API_BASE") or None
    model = get_secret("CARE_LLM_MODEL") or get_secret("CPF_LLM_MODEL") or "gpt-4o-mini"
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    system = {
        "role": "system",
        "content": (
            "You are CarePath, a concise educational explainer for Singapore long-term-care protection. "
            "Use only the official source context below. Do not request or process medical records, diagnoses, NRIC numbers, account numbers, exact balances, addresses, or other personal data. "
            "Do not diagnose disability, interpret a medical assessment, decide coverage or eligibility, predict claim approval, calculate a personal payout, recommend a supplement, or rank private insurers. "
            "For personal or current questions, direct the user to CPF Board, MOH, or AIC official services. Include a short 'Verify with CPF Board, MOH, or AIC' reminder in every answer.\n\n" + SOURCE_CONTEXT
        ),
    }
    request_kwargs: dict[str, Any] = {"model": model, "messages": [system] + messages[-8:], "max_tokens": 700}
    response = client.chat.completions.create(**request_kwargs)
    return response.choices[0].message.content or "I could not produce an answer. Please verify the information with CPF Board, MOH, or AIC."


def render_chatbot() -> None:
    page_header("03 · Optional chatbot", "Ask CarePath", "Ask about concepts, public processes, and where to read next. The chatbot is source-grounded but can still be wrong, so verify every answer with the official agency.")
    st.markdown('<div class="notice"><strong>Privacy boundary.</strong> Ask general questions only. Do not enter a diagnosis, medical record, NRIC number, account number, exact balance, address, or other identifying information.</div>', unsafe_allow_html=True)
    st.write("")
    if not get_secret("OPENAI_API_KEY"):
        st.info("The guided tools work without a key. Add OPENAI_API_KEY to server-side secrets to enable the optional chatbot.")
    prompts = [
        "What is the high-level difference between CareShield Life and ElderShield?",
        "What are the six activities of daily living?",
        "Where can a caregiver learn about applying for CareShield Life?",
    ]
    st.markdown("**Try a safe starter question**")
    cols = st.columns(3)
    for col, prompt in zip(cols, prompts):
        with col:
            if st.button(prompt, key=f"chat_prompt_{prompt}", use_container_width=True):
                st.session_state["pending_chat_prompt"] = prompt
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    typed = st.chat_input("Ask a general CareShield Life or ElderShield question…")
    prompt = typed or st.session_state.pop("pending_chat_prompt", None)
    if prompt:
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking the official-source context…"):
                try:
                    answer = assistant_reply(st.session_state["chat_messages"])
                except Exception as exc:
                    answer = "The chatbot could not connect. Please use the guided tools and verify information with CPF Board, MOH, or AIC. Technical detail: " + str(exc)[:180]
            st.markdown(answer)
        st.session_state["chat_messages"].append({"role": "assistant", "content": answer})
    st.write("")
    source_strip("The chatbot is a starting point only. Verify current rules and personal details through official services.", CPF_MEMBER_URL, "Open CPF member services")


def render_about() -> None:
    page_header("Documentation", "About CarePath", "A capstone prototype that makes long-term-care protection information easier to explore without collecting sensitive data.")
    st.markdown("**Full project title:** CarePath: A CareShield Life and ElderShield Information Navigator")
    st.markdown("### Project scope")
    st.write("CarePath consolidates public information about CareShield Life, ElderShield, long-term-care claims, and caregiver support. It is designed for citizens and families who want to understand the topic and prepare questions before using official services.")
    st.markdown("### Objectives")
    objectives = pd.DataFrame(
        [
            ["Consolidate information", "Bring CPF Board, MOH, and AIC guidance into one source-linked experience."],
            ["Personalise safely", "Use broad, non-identifying context to shape a learning pathway or conversation checklist."],
            ["Enhance understanding", "Explain schemes, activities of daily living, claims concepts, and public-service routes in plain language."],
            ["Present information effectively", "Combine forms, tables, charts, flowcharts, links, and a guarded chatbot."],
        ],
        columns=["Objective", "How the prototype addresses it"],
    )
    st.dataframe(objectives, use_container_width=True, hide_index=True)
    st.markdown("### Data sources")
    st.write("The prototype uses public pages from CPF Board for CareShield Life and ElderShield, MOH for supplements and healthcare-financing context, and AIC for claim-support and application guidance. These official sources are the source of truth and should be checked for current information.")
    st.markdown(f"Read [CPF Board CareShield Life]({CARESHIELD_URL}), [CPF Board ElderShield]({ELDERSHIELD_URL}), [MOH supplements]({MOH_SUPPLEMENTS_URL}), and [AIC CareShield Life]({AIC_CARESHIELD_URL}).")
    st.markdown("### Features")
    features = pd.DataFrame(
        [
            ["Understand my scheme", "Broad birth-year and topic context produces source-linked learning prompts and a high-level comparison."],
            ["Care conversation", "Broad audience, task, and destination context produces a non-personalised preparation checklist."],
            ["Optional chatbot", "A source-grounded assistant answers concept questions and refuses unsafe personal-data or decision requests."],
            ["Document RAG", "Users search an indexed document set and inspect document, section, page, score, and source-excerpt metadata."],
            ["Admin workspace", "Admins upload approved PDF, Markdown, or text files, load samples, and rebuild the lightweight FAISS index."],
            ["Result export", "Users can download a Markdown record containing the question, answer, retrieved excerpts, and citations."],
            ["Documentation", "About Us and Methodology pages explain the scope, data flow, limitations, and use-case flowcharts."],
        ],
        columns=["Feature", "Description"],
    )
    st.dataframe(features, use_container_width=True, hide_index=True)
    st.markdown("### Privacy and safety")
    st.write("The guided tools remain available to guests. The prototype also provides basic User and Admin roles, with passwords supplied through server-side secrets. Admins can upload approved PDF, Markdown, or text documents into a local project directory; the RAG engine chunks the content and indexes it with FAISS when available. The chatbot and document query page must not receive medical records, NRIC details, account information, exact balances, or other sensitive data.")
    with st.expander("Required prototype disclaimer"):
        st.warning(DISCLAIMER)


def render_methodology() -> None:
    page_header("Documentation", "Methodology", "The application uses a source-first flow: understand the context, surface concepts, provide safe preparation prompts, and point back to official services.")
    st.markdown("### Overall data flow")
    st.graphviz_chart(
        """
        digraph G {
          graph [rankdir=LR, bgcolor="transparent", pad=0.2];
          node [shape=box, style="rounded,filled", fontname="Arial", color="#087f70", fillcolor="#edf8f6", fontcolor="#102a43"];
          a [label="Guest / User / Admin"] -> b [label="Guided journey or document query"];
          b -> c [label="Broad inputs or question"] -> d [label="Deterministic rules / RAG retrieval"];
          d -> e [label="Prompt, answer, citations, or export"];
          f [label="Admin uploads approved PDF / MD / TXT"] -> g [label="Chunk + metadata"] -> h [label="FAISS-compatible vector index"] -> d;
          e -> i [label="Verify with official source"];
        }
        """,
        use_container_width=True,
    )
    st.markdown("### Minimum-scope RAG flow")
    st.write("An Admin uploads approved documents or loads the sample set. The engine extracts text, creates overlapping chunks, enriches each chunk with document and page metadata, and builds a lightweight vector index. A User submits a question, reviews the generated or retrieval-only answer, inspects the source excerpts, and can download the result as Markdown.")
    st.markdown("### Use case 1 — Understand my long-term-care scheme")
    st.graphviz_chart(
        """
        digraph C {
          graph [rankdir=LR, bgcolor="transparent", pad=0.2];
          node [shape=box, style="rounded,filled", fontname="Arial", color="#1b4965", fillcolor="#e7f1f5", fontcolor="#102a43"];
          a [label="Birth-year band + role"] -> b [label="Question focus"] -> c [label="Scheme comparison"] -> d [label="Learning prompts"] -> e [label="Secure coverage-check link"];
        }
        """,
        use_container_width=True,
    )
    st.write("This flow explains the public distinction between CareShield Life, ElderShield, and supplements. It does not determine actual coverage, eligibility, claim status, or payout.")
    st.markdown("### Use case 2 — Prepare for a care or claim conversation")
    st.graphviz_chart(
        """
        digraph H {
          graph [rankdir=LR, bgcolor="transparent", pad=0.2];
          node [shape=box, style="rounded,filled", fontname="Arial", color="#ed765e", fillcolor="#fff0eb", fontcolor="#102a43"];
          a [label="Audience + task"] -> b [label="Intended destination"] -> c [label="Questions and documents"] -> d [label="Care conversation checklist"] -> e [label="CPF Board / AIC / MOH"];
        }
        """,
        use_container_width=True,
    )
    st.write("This flow helps users prepare for an official conversation. It does not diagnose disability, interpret medical assessments, or predict claim approval.")
    st.markdown("### Document-RAG implementation")
    st.write("The Admin workspace accepts PDF, Markdown, and text files. The processing engine extracts text, creates overlapping word-based chunks, and records document name, section, page, and source-excerpt metadata. A deterministic local embedding is used so the prototype can retrieve content without requiring a second embedding API; FAISS performs inner-product search when installed, with a NumPy fallback for local testing. The Document RAG page displays retrieved excerpts and supports Markdown export. If OPENAI_API_KEY is configured, an optional gpt-4o-mini synthesis is generated from those excerpts; otherwise the retrieved context is shown directly.")
    st.markdown("### Chatbot implementation")
    st.write("The optional chatbot receives a fixed official-source context and the most recent conversation turns. It uses a server-side OPENAI_API_KEY and a configurable CARE_LLM_MODEL, defaulting to gpt-4o-mini for broad OpenAI-compatible support. It is disabled gracefully when no key is configured.")
    st.markdown("### Prototype deliverables")
    deliverables = pd.DataFrame(
        [
            ["Role support", "Guest, User, and Admin paths; passwords are configured through secrets for demonstration."],
            ["Document management", "Admin upload for PDF, Markdown, and text files plus a sample CarePath document set."],
            ["RAG query", "Chunking, metadata enrichment, FAISS-compatible retrieval, source excerpts, and answer generation."],
            ["Optional output", "Markdown download containing the response and retrieval evidence."],
            ["Deployment", "Streamlit Community Cloud-compatible requirements and secrets template."],
        ],
        columns=["Minimum scope item", "CarePath implementation"],
    )
    st.dataframe(deliverables, use_container_width=True, hide_index=True)
    st.markdown("### Limitations")
    limitations = pd.DataFrame(
        [
            ["Freshness", "The prototype is not a live mirror of CPF Board, MOH, or AIC. Verify current rules at the official source."],
            ["Medical and financial sensitivity", "No diagnosis, medical interpretation, personal claim decision, payout estimate, or insurance recommendation."],
            ["Personalisation", "Inputs are broad by design and produce educational prompts, not an eligibility assessment."],
            ["Language model", "Generated answers can be inaccurate. Users must verify with CPF Board, MOH, or AIC."],
            ["Privacy", "Do not submit medical records, NRIC details, account information, exact balances, or other identifiers."],
        ],
        columns=["Area", "Boundary"],
    )
    st.dataframe(limitations, use_container_width=True, hide_index=True)


def render_footer() -> None:
    st.divider()
    st.caption("CarePath · Educational prototype · Verify current and personal information with CPF Board, MOH, or AIC.")


def main() -> None:
    inject_css()
    render_brand_bar()
    gate_if_configured()
    pages = ["Home", "Understand my scheme", "Care conversation", "Ask CarePath", "Document RAG", "Admin documents", "About Us", "Methodology"]
    if "page" not in st.session_state or st.session_state["page"] not in pages:
        st.session_state["page"] = "Home"
    if st.session_state.get("page_selector") not in pages:
        st.session_state["page_selector"] = st.session_state["page"]
    render_role_controls()
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=64)
        st.markdown("## CarePath")
        st.caption("Understand care protection. Verify always.")
        selection = st.radio("Navigate", pages, key="page_selector", on_change=sync_page_from_selector, label_visibility="collapsed")
        st.session_state["page"] = selection
        st.divider()
        st.markdown("### Two journeys")
        st.markdown("**Scheme coverage**  \nCareShield Life, ElderShield, and supplements")
        st.markdown("**Care conversation**  \nQuestions, documents, and official next steps")
        st.divider()
        st.caption("No sensitive data needed. Do not enter health or account details.")
    page = st.session_state["page"]
    if page == "Home":
        render_home()
    elif page == "Understand my scheme":
        render_coverage()
    elif page == "Care conversation":
        render_care()
    elif page == "Ask CarePath":
        render_chatbot()
    elif page == "Document RAG":
        render_rag_query()
    elif page == "Admin documents":
        render_admin_documents()
    elif page == "About Us":
        render_about()
    else:
        render_methodology()
    render_footer()


if __name__ == "__main__":
    main()
