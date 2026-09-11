from __future__ import annotations

import os
import base64
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from rag_engine import LocalVectorStore, build_chunks, ensure_sample_documents, save_uploaded_file, serialize_results
from test_case_generator import COVERAGE_OPTIONS, cases_to_excel, cases_to_json, cases_to_markdown, cases_to_rows, direct_input_candidates, extract_requirement_candidates, generate_test_cases, reconciliation_scenarios

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]

PROJECT_DIR = Path(__file__).resolve().parent
DOCUMENT_DIR = PROJECT_DIR / "documents"
SAMPLE_DOCUMENT_DIR = PROJECT_DIR / "sample_documents"

st.set_page_config(
    page_title="TestBuddy",
    page_icon=":material/bug_report:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Application safety and test-case generation boundaries
# -----------------------------------------------------------------------------
DISCLAIMER = (
    "IMPORTANT NOTICE: TestBuddy is an educational QA-assistance prototype. Generated "
    "test cases are drafts and must not be treated as formal test sign-off, compliance "
    "evidence, or a replacement for approved requirements and human QA review.\n\n"
    "AI-generated output may be incomplete, inaccurate, or based on assumptions. Review "
    "every requirement link, business rule, test datum, expected result, and environment "
    "dependency before execution.\n\n"
    "Use anonymised or synthetic data only. Never upload credentials, API keys, confidential "
    "source code, production transaction data, or personal information."
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
        /* Theme-safe Streamlit controls */
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea { background: var(--surface) !important; color: var(--ink) !important; border-color: var(--line) !important; caret-color: var(--ink) !important; }
        [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder { color: var(--muted) !important; opacity: .9 !important; }
        [data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] > div { background: var(--surface) !important; color: var(--ink) !important; border-color: var(--line) !important; }
        [data-baseweb="select"] [role="option"], [data-baseweb="popover"] * { color: var(--ink) !important; background: var(--surface) !important; }
        [data-testid="stRadio"] label, [data-testid="stCheckbox"] label, [data-testid="stMultiSelect"] label, [data-testid="stSelectbox"] label, [data-testid="stTextInput"] label, [data-testid="stTextArea"] label, [data-testid="stFileUploader"] label { color: var(--ink) !important; }
        [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
        [data-testid="stDataFrame"] iframe { background: var(--surface) !important; }
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { background: var(--surface); color: var(--ink) !important; border-color: var(--line) !important; }
        .stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--teal) !important; color: var(--teal) !important; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button { background: var(--teal) !important; color: #ffffff !important; border-color: var(--teal) !important; }
        .stButton > button:disabled, .stDownloadButton > button:disabled { background: var(--surface) !important; color: var(--muted) !important; border-color: var(--line) !important; opacity: .48 !important; cursor: not-allowed !important; }
        [data-testid="stAlert"] { color: var(--ink) !important; }
        body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) [data-testid="stDataFrame"], body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) [data-testid="stDataFrame"] iframe { background: #171b24 !important; color-scheme: dark; }
        body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) [data-baseweb="popover"], body:has([data-testid="stMainMenuItem-theme-Dark"][aria-checked="true"]) [role="listbox"] { background: #171b24 !important; color: #f1f5f9 !important; }
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
    st.session_state["pending_page_selector"] = page
    st.rerun()


def sync_page_from_selector() -> None:
    st.session_state["page"] = st.session_state["page_selector"]


def render_brand_bar() -> None:
    st.markdown('<div class="brand-bar"><div><div class="brand-name">TestBuddy</div><div class="brand-subtitle">Source-grounded URS test-case generator</div></div></div>', unsafe_allow_html=True)


def current_role() -> str:
    return st.session_state.get("role", "Not signed in")


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


def authenticate_role(role_choice: str, password: str) -> bool:
    expected_name = "ADMIN_PASSWORD" if role_choice == "Admin" else "USER_PASSWORD"
    expected = get_secret(expected_name)
    accepted_demo_passwords = {"admin", "adminaibootcamp"} if role_choice == "Admin" else {"user", "useraibootcamp"}
    return bool((expected and password == expected) or (not expected and password in accepted_demo_passwords))


def page_allowed(page: str) -> bool:
    role = current_role()
    if role not in {"User", "Admin"}:
        return page == "Home"
    if page in {"Home", "About Us", "Methodology"}:
        return True
    if page in {"Test Case Generator", "Document RAG"}:
        return role in {"User", "Admin"}
    if page == "Admin documents":
        return role == "Admin"
    return False


def render_navigation(pages: list[str]) -> None:
    with st.sidebar:
        st.markdown("## TestBuddy")
        st.caption("Source-grounded URS test-case generation")
        role = current_role()
        if role in {"User", "Admin"}:
            st.success(f"Selected role: {role}")
        else:
            st.warning("No role selected. Return to Home to sign in.")
        st.markdown("### Menu")
        for page in pages:
            if st.button(page, key=f"nav_{page}", use_container_width=True, disabled=not page_allowed(page)):
                navigate_to(page)
        st.divider()
        st.markdown("### Workflow")
        st.markdown("**1. Upload**  \\nChoose a URS document")
        st.markdown("**2. Generate**  \\nCreate comprehensive coverage")
        st.markdown("**3. Review**  \\nExport Excel and validate assumptions")
        st.caption("Greyed-out pages require a different role. Do not upload confidential source code, credentials, or personal data.")


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
            {"role": "system", "content": "You are TestBuddy's source-grounded requirement assistant. Answer only from the supplied excerpts. Cite each material claim with the document name and section. State when the excerpts are insufficient."},
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


def get_llm_client() -> Any | None:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    base_url = get_secret("OPENAI_API_BASE")
    if base_url:
        client_kwargs["base_url"] = base_url
    return OpenAI(**client_kwargs)


def render_test_case_generator() -> None:
    page_header("01 · Upload and generate", "Upload a URS and generate test cases", "Choose a Word, PDF, Markdown, or text User Requirement Specification, index it, select coverage dimensions, and export review-ready test cases.")
    st.markdown('<div class="notice"><strong>Source-grounded generation.</strong> Use an indexed URS, paste a business requirement or user story, or describe a system. Missing details are recorded as assumptions rather than silently invented. Use anonymised or synthetic data only. A QA analyst must review every generated case before execution.</div>', unsafe_allow_html=True)
    if current_role() not in {"User", "Admin"}:
        st.warning("Return to Home and sign in as User or Admin to generate test cases.")
        return
    st.markdown("### Step 1 — Upload and index your URS")
    uploaded_urs = st.file_uploader("Choose a URS document", type=["docx", "pdf", "md", "txt"], accept_multiple_files=True, help="Word documents (.docx), PDF, Markdown, and text URS files are supported.")
    if st.button("Upload and index URS", type="primary", disabled=not uploaded_urs, use_container_width=True):
        for item in uploaded_urs or []:
            save_uploaded_file(item, DOCUMENT_DIR)
        refresh_rag_store()
        st.success(f"Indexed {len(uploaded_urs or [])} URS document(s). You can now generate test cases below.")
    store = get_rag_store()
    st.caption(f"Indexed URS/document chunks: {len(store.chunks)} · Active role: {current_role()}")
    input_mode = st.radio("What are you providing?", ["Indexed URS document", "Direct requirement or user story", "System description"], horizontal=True, key="generator_input_mode", help="Selecting a mode immediately changes the input fields below.")
    mode_guidance = {
        "Indexed URS document": "Use this mode after uploading and indexing a URS. Leave the topic blank to generate from the full indexed document, or enter a topic/requirement ID to focus the result.",
        "Direct requirement or user story": "Use this mode when you want to paste one requirement, user story, business rule, or acceptance statement without uploading a document.",
        "System description": "Use this mode when you want to describe a system, workflow, integration, or service and generate an initial test-design draft from that description.",
    }
    st.info(mode_guidance[input_mode])
    with st.form("test_case_generator_form"):
        if input_mode == "Indexed URS document":
            query = st.text_input("Requirement topic or identifier (optional)", placeholder="Leave blank to generate from the uploaded URS; or enter e.g. payment validation, REQ-001, user registration")
            direct_text = ""
            scenario = "General"
        elif input_mode == "Direct requirement or user story":
            query = "Direct input"
            scenario = st.selectbox("Optional scenario lens", ["General"] + reconciliation_scenarios(), help="Use a lens only when it is relevant to the supplied requirement.")
            direct_text = st.text_area("Paste the requirement or user story", height=180, placeholder="Example: The customer shall receive a confirmation email after a successful registration.")
        else:
            query = "Direct input"
            scenario = st.selectbox("Optional scenario lens", ["General"] + reconciliation_scenarios(), help="Use a lens only when it is relevant to the supplied system description.")
            direct_text = st.text_area("Describe the system or workflow", height=180, placeholder="Example: The reconciliation service matches source and target records using an agreed identifier and amount rule, then routes exceptions for manual review.")
        coverage = st.multiselect("Coverage dimensions", COVERAGE_OPTIONS, default=COVERAGE_OPTIONS, help="Choose the scenario dimensions to generate for each requirement. The application will not claim a dimension is covered unless it is selected and generated.")
        top_k = st.slider("Retrieved requirement excerpts", 1, 12, 6, disabled=input_mode != "Indexed URS document")
        include_negative = st.checkbox("Include negative and boundary cases", value=True)
        max_cases = st.slider("Maximum generated cases", 2, 60, 20, help="The maximum applies across all requirements and selected coverage dimensions.")
        submitted = st.form_submit_button("Generate comprehensive test coverage", type="primary", use_container_width=True)
    if submitted and ((input_mode == "Indexed URS document" and store.chunks) or query.strip() or direct_text.strip()):
        with st.spinner("Preparing requirement evidence and generating traceable test cases…"):
            if input_mode == "Indexed URS document":
                if query.strip():
                    results = store.search(query.strip(), top_k=top_k)
                else:
                    results = [{**chunk.__dict__, "score": 1.0} for chunk in store.chunks]
                candidates = extract_requirement_candidates(results, limit=min(60, max(top_k, 12)))
            else:
                results = []
                candidates = direct_input_candidates(direct_text, input_type=input_mode, scenario=scenario)
                if scenario != "General" and candidates:
                    for candidate in candidates:
                        candidate["requirement_text"] += f" Scenario lens: cover {scenario.lower()}."
            client = get_llm_client()
            model = get_secret("CARE_LLM_MODEL") or get_secret("CPF_LLM_MODEL") or "gpt-4o-mini"
            selected_coverage = coverage or (["Happy path", "Negative / validation"] if include_negative else ["Happy path"])
            cases, mode = generate_test_cases(candidates, client=client, model=model, include_negative=include_negative, max_cases=max_cases, coverage=selected_coverage)
            st.session_state["tc_query"] = query.strip() if input_mode == "Indexed URS document" else direct_text.strip()
            st.session_state["tc_results"] = results
            st.session_state["tc_candidates"] = candidates
            st.session_state["tc_cases"] = cases
            st.session_state["tc_mode"] = mode
            st.session_state["tc_coverage"] = selected_coverage
    cases = st.session_state.get("tc_cases", [])
    if not cases:
        return
    st.success(f"Generated {len(cases)} test case(s) · {st.session_state.get('tc_mode', '')}")
    st.info("Coverage requested: " + ", ".join(st.session_state.get("tc_coverage", ["Happy path", "Negative / validation"])))
    st.markdown("### Requirement coverage")
    candidates = st.session_state.get("tc_candidates", [])
    if candidates:
        st.dataframe(pd.DataFrame(candidates)[["requirement_id", "requirement_text", "source_document", "source_section"]], use_container_width=True, hide_index=True)
    st.markdown("### Generated test cases")
    for case in cases:
        with st.expander(f"{case.test_case_id} · {case.requirement_id} · {case.title}", expanded=False):
            st.write(f"**Objective:** {case.objective}")
            st.write(f"**Type:** {case.test_type} · **Priority:** {case.priority}")
            st.markdown("**Preconditions**")
            for item in case.preconditions:
                st.markdown(f"- {item}")
            st.markdown("**Test data**")
            for item in case.test_data:
                st.markdown(f"- {item}")
            st.markdown("**Steps**")
            st.table(pd.DataFrame([{"Step": step.step, "Action": step.action, "Expected result": step.expected_result} for step in case.steps]))
            st.write(f"**Overall expected result:** {case.expected_result}")
            st.markdown(f"**Source:** `{case.source_document}` · {case.source_section}")
            st.caption(case.source_excerpt)
            st.markdown("**Assumptions to review**")
            for item in case.assumptions:
                st.markdown(f"- {item}")
    export_base = cases_to_markdown(cases, title="TestBuddy — Generated URS Test Cases")
    export_json = cases_to_json(cases)
    export_csv = pd.DataFrame(cases_to_rows(cases)).to_csv(index=False)
    export_excel = cases_to_excel(cases)
    st.markdown("### Export")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button("Download Markdown", export_base, file_name="generated_test_cases.md", mime="text/markdown", use_container_width=True)
    with c2:
        st.download_button("Download JSON", export_json, file_name="generated_test_cases.json", mime="application/json", use_container_width=True)
    with c3:
        st.download_button("Download CSV", export_csv, file_name="generated_test_cases.csv", mime="text/csv", use_container_width=True)
    with c4:
        st.download_button("Download Excel", export_excel, file_name="generated_test_cases.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def render_rag_query() -> None:
    page_header("02 · Evidence search", "Search the indexed requirement set", "Retrieve source excerpts from approved URS and specification documents before generating or reviewing test cases.")
    st.markdown('<div class="notice"><strong>Prototype boundary.</strong> This page demonstrates requirement evidence retrieval. It is not a test sign-off or substitute for formal QA review.</div>', unsafe_allow_html=True)
    if current_role() not in {"User", "Admin"}:
        st.warning("Return to Home and sign in as User or Admin to query the indexed document set.")
        return
    store = get_rag_store()
    st.caption(f"Indexed chunks: {len(store.chunks)} · Active role: {current_role()}")
    if not store.chunks:
        st.info("No documents are indexed yet. Upload a URS from the combined Test Case Generator workflow or use the Admin document workspace to load the sample set.")
        return
    with st.form("rag_query_form"):
        query = st.text_input("Ask a question about the indexed documents", placeholder="Which validation rule applies to this requirement?")
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
        export_text = "# TestBuddy evidence query\n\nQuestion: " + st.session_state.get("rag_query", "") + "\n\nAnswer:\n" + st.session_state.get("rag_answer", "") + "\n\nRetrieved results:\n" + serialize_results(st.session_state["rag_results"])
        st.download_button("Download answer and citations", export_text, file_name="ai_test_generator_evidence.md", mime="text/markdown", use_container_width=True)


def render_admin_documents() -> None:
    page_header("03 · Admin workspace", "Manage the requirement set", "Upload approved Word, PDF, Markdown, or text requirement specifications, load the sample set, and rebuild the lightweight vector index.")
    if current_role() != "Admin":
        st.warning("Return to Home and sign in as Admin to manage documents.")
        return
    st.markdown('<div class="notice"><strong>Admin boundary.</strong> Upload only approved requirement specifications. Do not upload API keys, credentials, confidential source code, production records, customer identifiers, or other sensitive personal information.</div>', unsafe_allow_html=True)
    st.markdown("**Workflow:** 1. Upload a URS file. 2. Click **Save uploaded documents**. 3. Confirm the indexed chunk count. 4. Open **Test Case Generator**. 5. Select coverage dimensions and generate cases. 6. Download the Excel workbook for QA review.")
    uploaded = st.file_uploader("Upload a URS or requirements document", type=["docx", "pdf", "md", "txt"], accept_multiple_files=True, help="Use an approved Word, PDF, Markdown, or text URS. For best extraction, keep requirement IDs and requirement statements in the document.")
    if st.button("Save uploaded documents", type="primary", disabled=not uploaded):
        for item in uploaded or []:
            save_uploaded_file(item, DOCUMENT_DIR)
        refresh_rag_store()
        st.success(f"Saved {len(uploaded or [])} document(s) and rebuilt the index.")
    if st.button("Load sample URS documents"):
        copied = ensure_sample_documents(DOCUMENT_DIR, SAMPLE_DOCUMENT_DIR)
        refresh_rag_store()
        st.success(f"Loaded {copied} sample URS document(s) and rebuilt the index.")
    st.markdown("### Current document set")
    files = sorted([path for path in DOCUMENT_DIR.iterdir() if path.is_file()]) if DOCUMENT_DIR.exists() else []
    if files:
        st.dataframe(pd.DataFrame([[path.name, path.suffix.lower(), path.stat().st_size] for path in files], columns=["Document", "Type", "Bytes"]), use_container_width=True, hide_index=True)
        st.markdown("### Remove uploaded URS documents")
        st.caption("Deleting a document removes it from the local document folder and rebuilds the search index. It does not delete the original file on your computer.")
        selected_document = st.selectbox("Document to remove", [path.name for path in files], key="document_to_remove")
        remove_col, clear_col = st.columns(2)
        with remove_col:
            if st.button("Remove selected document", use_container_width=True):
                target = DOCUMENT_DIR / selected_document
                if target.exists() and target.is_file():
                    target.unlink()
                refresh_rag_store()
                st.session_state.pop("tc_cases", None)
                st.session_state.pop("tc_candidates", None)
                st.session_state.pop("rag_results", None)
                st.success(f"Removed {selected_document} and rebuilt the index.")
                st.rerun()
        with clear_col:
            if st.button("Clear all uploaded documents", use_container_width=True):
                for path in files:
                    if path.is_file():
                        path.unlink()
                refresh_rag_store()
                st.session_state.pop("tc_cases", None)
                st.session_state.pop("tc_candidates", None)
                st.session_state.pop("rag_results", None)
                st.success("Removed all uploaded documents and rebuilt the index.")
                st.rerun()
    else:
        st.info("No documents uploaded yet.")
    chunk_count = st.session_state.get('rag_chunk_count', len(get_rag_store().chunks))
    st.caption(f"Current indexed chunks: {chunk_count}")
    if files and chunk_count:
        if st.button("Open Test Case Generator", type="primary", use_container_width=True):
            navigate_to("Test Case Generator")


def render_login_page() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">Secure role access · TestBuddy</div><h1>Sign in to begin</h1><p>Select the role that matches your task. User generates test cases from URS documents. Admin manages approved requirement documents and the indexed requirement set.</p></div>', unsafe_allow_html=True)
    st.markdown("### Choose your role")
    st.info("There is no Guest role. You must sign in as User or Admin to access the application workflow. Pages that are not available before sign-in are greyed out in the sidebar.")
    with st.form("dedicated_role_login"):
        selected_role = st.selectbox("Role", ["User", "Admin"], key="login_role")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Enter the password provided by the project owner")
        submitted = st.form_submit_button("Sign in to TestBuddy", type="primary", use_container_width=True)
    if submitted:
        if authenticate_role(selected_role, password):
            st.session_state["role"] = selected_role
            st.session_state["page"] = "Home"
            st.rerun()
        st.error("The role password did not match. Check the deployment instructions or ask the project owner for the configured password.")
    st.markdown("### Role permissions")
    st.dataframe(pd.DataFrame([
        ["User", "Upload a URS directly in Test Case Generator, generate comprehensive test coverage, search evidence, and download Excel/CSV results."],
        ["Admin", "All User capabilities plus approved-document management, sample URS loading, and index rebuilding."],
    ], columns=["Role", "Access" ]), use_container_width=True, hide_index=True)


def render_home() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">Source-grounded QA productivity · prototype</div><h1>Turn requirements into reviewable test cases.</h1><p>TestBuddy helps QA analysts retrieve requirements from a User Requirement Specification and generate traceable functional, negative, and boundary test cases with source evidence.</p></div>', unsafe_allow_html=True)
    disclaimer()
    st.write("")
    st.markdown('<div class="eyebrow">Start with a workflow</div>', unsafe_allow_html=True)
    st.subheader("A faster first draft, with evidence attached")
    st.markdown("Upload an approved URS document, retrieve the relevant requirement text, generate candidate test cases, and review every assumption before execution.")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="card teal-card"><div class="eyebrow">01 · Generate</div><h3>Generate URS test cases</h3><p>Retrieve requirement evidence and create positive, negative, and boundary cases with steps, expected results, assumptions, and source traceability.</p></div>', unsafe_allow_html=True)
        if st.button("Open test-case generator", use_container_width=True, key="home_generator"):
            navigate_to("Test Case Generator")
            st.rerun()
    with right:
        st.markdown('<div class="card accent-card"><div class="eyebrow">02 · Manage</div><h3>Manage the requirement set</h3><p>Admins can upload approved PDF, Markdown, or text specifications, load the sample URS, and rebuild the lightweight vector index.</p></div>', unsafe_allow_html=True)
        if st.button("Open document management", use_container_width=True, key="home_admin"):
            navigate_to("Admin documents")
            st.rerun()
    st.write("")
    st.markdown('<div class="eyebrow">What is inside</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        st.markdown('<div class="card"><div class="metric-label">01</div><div class="metric-value">Retrieve</div><p>Find relevant requirement excerpts from indexed URS documents and preserve document-level traceability.</p></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card"><div class="metric-label">02</div><div class="metric-value">Generate</div><p>Create structured test cases with preconditions, data, steps, expected results, priorities, and assumptions.</p></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="card"><div class="metric-label">03</div><div class="metric-value">Review</div><p>Inspect the evidence behind each generated case and export Markdown, CSV, JSON, or Excel for QA review.</p></div>', unsafe_allow_html=True)
    st.write("")
    st.markdown('<div class="source-strip">Use approved URS documents only. Generated test cases are drafts for QA review and are not a substitute for formal test design or requirements sign-off.</div>', unsafe_allow_html=True)


def render_about() -> None:
    page_header("Documentation", "About TestBuddy", "A source-grounded QA productivity prototype that turns requirements into reviewable test cases without hiding the evidence behind the output.")
    st.markdown("**Full project title:** TestBuddy: Source-Grounded User Requirement Specification Test-Case Generator")
    st.markdown("### Project scope")
    st.write("TestBuddy accepts an indexed User Requirement Specification or direct input such as a business requirement, user story, system description, business rule, or reconciliation scenario. It retrieves relevant requirement evidence and generates structured positive, negative, edge, and boundary test cases for human QA review.")
    st.markdown("### Objectives")
    objectives = pd.DataFrame(
        [
            ["Accelerate test design", "Produce a useful first draft of test cases from requirements while keeping the source evidence visible."],
            ["Improve coverage", "Prompt for happy paths, negative conditions, boundary values, duplicates, mismatches, missing data, and exception handling."],
            ["Preserve traceability", "Carry requirement identifiers, document names, sections, page metadata where available, and source excerpts into each case."],
            ["Support QA judgement", "Record assumptions and limitations so a tester can review, refine, approve, or reject every generated case."],
        ],
        columns=["Objective", "How the prototype addresses it"],
    )
    st.dataframe(objectives, use_container_width=True, hide_index=True)
    st.markdown("### Supported inputs")
    st.dataframe(pd.DataFrame([
        ["URS document", "PDF, Markdown, or text requirement specification uploaded by an Admin."],
        ["Business requirement", "A pasted statement of desired behaviour, rules, inputs, or outputs."],
        ["User story", "A user-centred description such as role, goal, and acceptance expectation."],
        ["System description", "A functional or integration description supplied directly by a User or Admin."],
        ["Reconciliation scenario", "Matched, unmatched, duplicate, amount mismatch, date mismatch, missing identifier, reversal, or late-arriving records."],
    ], columns=["Input type", "Description"]), use_container_width=True, hide_index=True)
    st.markdown("### Features")
    features = pd.DataFrame(
        [
            ["Document management", "Admins upload approved Word, PDF, Markdown, or text specifications, load the sample URS, and rebuild the lightweight vector index."],
            ["Requirement retrieval", "Users search the indexed source set and inspect the evidence selected for generation."],
            ["Test-case generation", "The application creates structured cases with ID, requirement, objective, type, priority, preconditions, test data, steps, expected results, sources, and assumptions."],
            ["Scenario coverage", "The workflow supports happy paths, negative and boundary cases, and reconciliation-specific scenario lenses."],
            ["Export", "Cases can be downloaded as Markdown, CSV, JSON, or Excel for QA review and onward processing."],
            ["Roles", "User and Admin roles protect generation and document management with server-side secrets. The initial page clearly identifies the selected role, and inaccessible navigation items are disabled."],
        ],
        columns=["Feature", "Description"],
    )
    st.dataframe(features, use_container_width=True, hide_index=True)
    st.markdown("### Privacy and human review")
    st.write("Do not submit credentials, secrets, confidential source code, production transaction data, customer identifiers, or personal information. Use anonymised or synthetic examples. Generated cases are drafts; they may miss domain-specific nuances, so a qualified QA analyst must review the requirement coverage, test data, expected results, assumptions, and environment dependencies before execution.")
    with st.expander("Prototype disclaimer"):
        st.warning("TestBuddy is an educational QA-assistance prototype. Generated output is not a test sign-off, compliance decision, or replacement for approved requirements, detailed design, formal test planning, or human review.")


def render_methodology() -> None:
    page_header("Documentation", "Methodology", "The prototype follows a source-first requirement-to-test-case flow: ingest, retrieve, generate, trace, review, and export.")
    st.markdown("### End-to-end data flow")
    st.graphviz_chart(
        """
        digraph G {
          graph [rankdir=LR, bgcolor="transparent", pad=0.2];
          node [shape=box, style="rounded,filled", fontname="Arial", color="#087f70", fillcolor="#edf8f6", fontcolor="#102a43"];
          a [label="Admin uploads URS or User enters requirement"] -> b [label="Extract text + metadata"] -> c [label="Chunk requirement evidence"] -> d [label="FAISS-compatible retrieval"];
          d -> e [label="Candidate requirements"] -> f [label="Structured test-case generation"] -> g [label="Source + assumptions"] -> h [label="Human review + export"];
        }
        """,
        use_container_width=True,
    )
    st.markdown("### Requirement processing")
    st.write("PDF, Markdown, and text files are extracted into text, divided into overlapping chunks, and enriched with document name, section or chunk label, page where available, and source excerpts. A deterministic local hashed embedding is used for the prototype, with FAISS inner-product retrieval when available and a NumPy fallback for local testing.")
    st.markdown("### Test-case generation")
    st.write("The generator first creates candidate requirement records. If an OpenAI-compatible API key is configured, a structured JSON-schema request asks the model to generate cases only from those candidates. If no key is available or generation fails, a deterministic fallback creates positive and negative cases from the same evidence. This keeps the workflow demonstrable without making the API a hard dependency.")
    st.markdown("### Structured output schema")
    st.dataframe(pd.DataFrame([
        ["Identity", "Test-case ID and linked requirement ID."],
        ["Intent", "Title, objective, test type, and priority."],
        ["Execution", "Preconditions, test data, ordered steps, and expected results."],
        ["Traceability", "Source document, source section, page metadata where available, and excerpt."],
        ["Review", "Assumptions that require confirmation before execution."],
    ], columns=["Field group", "Purpose"]), use_container_width=True, hide_index=True)
    st.markdown("### Reconciliation coverage lens")
    st.write("The optional reconciliation lens helps users ask for matched transactions, unmatched source or target records, duplicate entries, mismatched amounts, date mismatches, missing identifiers, partial settlement, reversals, cancellations, and late-arriving records. These are scenario prompts, not invented business rules; the supplied requirement must define the actual matching logic and expected treatment.")
    st.markdown("### Human-review gates")
    st.graphviz_chart(
        """
        digraph H {
          graph [rankdir=LR, bgcolor="transparent", pad=0.2];
          node [shape=box, style="rounded,filled", fontname="Arial", color="#ed765e", fillcolor="#fff0eb", fontcolor="#102a43"];
          a [label="Generated draft"] -> b [label="Check requirement coverage"] -> c [label="Check business rules + test data"] -> d [label="Check expected results"] -> e [label="Approve, revise, or reject"];
        }
        """,
        use_container_width=True,
    )
    st.markdown("### Limitations")
    st.dataframe(pd.DataFrame([
        ["Requirement ambiguity", "The model cannot resolve missing or contradictory rules reliably; it records assumptions for review."],
        ["Source grounding", "The system can only preserve evidence that was supplied or retrieved; it must not be treated as a complete requirements repository."],
        ["Generated quality", "AI output can be incomplete, repetitive, or technically incorrect. Human QA review is mandatory."],
        ["Data privacy", "Use anonymised or synthetic data and do not upload credentials, confidential source code, or production records."],
        ["Persistence", "The prototype uses local document storage and an in-memory index; uploaded content is not durable production storage."],
    ], columns=["Area", "Boundary"]), use_container_width=True, hide_index=True)


def render_footer() -> None:
    st.divider()
    st.caption("TestBuddy · QA prototype · Review generated test cases against approved requirements before execution.")


def main() -> None:
    inject_css()
    render_brand_bar()
    pages = ["Home", "Test Case Generator", "Document RAG", "Admin documents", "About Us", "Methodology"]
    if "page" not in st.session_state or st.session_state["page"] not in pages:
        st.session_state["page"] = "Home"
    render_navigation(pages)
    if current_role() not in {"User", "Admin"}:
        render_login_page()
        render_footer()
        return
    page = st.session_state["page"]
    if page == "Home":
        render_home()
    elif page == "Test Case Generator":
        render_test_case_generator()
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
