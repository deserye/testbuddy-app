# CarePath validation notes

**Full project title:** CarePath: A CareShield Life and ElderShield Information Navigator

## Local preview

The Streamlit preview loaded successfully at `http://localhost:8501/` with the title `CarePath | Long-term-care protection`. The sidebar renders Home, Understand my scheme, Care conversation, Ask CarePath, About Us, and Methodology. The home page renders the required disclaimer, two guided-use-case entry points, and an official CPF Board source link.

## Use case 1: Understand my scheme

The scheme-coverage form rendered with broad birth-year context, audience, and topic focus. Submitting the default scenario produced a learning pathway with one “Your learning prompts” heading, a high-level CareShield Life/ElderShield/Supplements comparison table, a six-activities-of-daily-living explainer, a visual chart, and CPF Board links. The page explicitly says it does not determine coverage, interpret medical information, or predict a claim.

## Use case 2: Care conversation

The care-conversation form rendered with audience, task, and destination fields. Submitting the default scenario produced a five-step preparation checklist, an “Ask, verify, prepare” guardrail panel, a visual emphasis chart, and AIC, CPF Board, and MOH links. The page clearly states that it does not provide medical, legal, insurance, or financial advice.

## Optional chatbot

The chatbot page rendered with a clear privacy boundary, three safe starter prompts, an optional-key setup message, and an official CPF member-services link. The implementation uses a server-side key, a fixed official-source context, the configurable `CARE_LLM_MODEL`, standard chat-completion fields, and no provider-specific reasoning parameter. The no-key fallback was verified by automated smoke tests.

## Documentation pages

The About Us page rendered the project scope, objectives, public data sources, feature table, privacy and safety statement, and required prototype disclaimer. The Methodology page rendered the overall data-flow diagram, separate flowcharts for both use cases, chatbot implementation notes, and limitations table.

## Automated checks

`python3 -m py_compile app.py` passed.

`python3 test_app.py` passed, including deterministic outputs for both guided journeys, required source/disclaimer content, and the chatbot no-key fallback.

## Deployment note

The project is prepared for Streamlit Community Cloud. Configure `OPENAI_API_KEY`, `CARE_LLM_MODEL`, and optionally `APP_PASSWORD` in the platform’s Secrets panel. The current local preview is temporary and is not a permanent public deployment.

## Temporary public preview

The updated CarePath home page is reachable at `https://8501-i758fxk77lhu2t69cdbin-de3e45f8.us3.manus.computer`. The public page loaded with the CarePath title, two guided-use-case entry points, sidebar navigation, official-source link, and required disclaimer. This URL is a temporary preview, not a permanent Streamlit Community Cloud deployment.

## Friendly light-theme update

The visual refresh passed `python3 -m py_compile app.py` and `python3 test_app.py`. The local preview now uses a light mint sidebar, soft cream background, pastel teal/blue/peach hero treatment, warmer accent colors, and dark readable text. Navigation, disclaimer, and the two guided journey entry points remain intact.

## CarePath branding update

The public preview now reports the full browser title `CarePath: A CareShield Life and ElderShield Information Navigator`. The visible sidebar and navigation use `CarePath`, while the About Us page contains the full project title. The light theme and all existing functionality remain intact.

## Visual asset integration

The local preview now renders the CarePath logo mark in the sidebar and the hero family illustration on the home page. The scheme journey renders its supporting illustration beside the page header and form, with an explanatory caption. The full browser title and CarePath navigation remain intact.

The care-conversation journey also renders its supporting illustration beside the page header and form, with a safety-focused caption. Both guided pages retain their official-source strips, forms, and boundary notices.

## Dark-mode compatibility update

The custom CSS now detects Streamlit’s selected theme using the checked `stMainMenuItem-theme-Dark` control. In the dark-theme browser check, the page background, sidebar, hero, custom cards, source strip, notice, and text colours rendered consistently with the selected dark theme. Light mode remains the default friendly presentation. Syntax checks and deterministic smoke tests passed.

## Navigation and header usability update

The sidebar navigation labels now have larger 46px minimum-height targets, increased padding and spacing, a full-width clickable area, a visible hover state, and a slightly larger radio indicator. A compact CarePath brand bar now appears below Streamlit’s top toolbar with the logo mark, CarePath name, and supporting project descriptor. The local preview rendered the brand bar and larger navigation controls successfully.

## Navigation state fix

The sidebar radio navigation now uses a dedicated `page_selector` widget key and an `on_change` synchronisation callback. Browser validation confirmed that one click from Home opened “Understand my scheme” immediately, and one subsequent click opened “Care conversation” without reverting to the prior selection.

## Minimum-scope RAG refinement

The refined prototype adds Guest, User, and Admin role controls, Admin document upload for PDF/Markdown/text files, a sample CarePath document set, chunking and metadata enrichment, a FAISS-compatible in-memory vector store with NumPy fallback, a Document RAG query page, retrieved source excerpts, optional model synthesis, and Markdown answer export.

Automated checks passed: `python3 -m py_compile app.py rag_engine.py`, `python3 test_app.py`, and `python3 test_rag.py`.

Browser validation confirmed the new role selector and navigation labels, Admin sign-in with the demo Admin credentials, the Admin documents page with sample documents indexed, the Document RAG form, and a successful ElderShield query returning two cited sample-document excerpts and a download control. Retrieval-only mode remains usable without an API key.
