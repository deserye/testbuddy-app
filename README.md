# TestBuddy: Source-Grounded URS Test-Case Generator

TestBuddy is a Streamlit prototype that helps QA analysts turn approved requirements into reviewable software test cases. It accepts indexed User Requirement Specification documents as well as direct business requirements, user stories, system descriptions, business rules, and reconciliation scenarios.

The application retrieves requirement evidence, generates structured positive, negative, edge, and boundary test cases, preserves source traceability, records assumptions, and exports results as Markdown, CSV, JSON, or Excel workbooks. It is a QA-assistance prototype, not a replacement for formal requirements approval, test planning, or human sign-off.

## Core workflow

1. An Admin uploads an approved PDF, Markdown, or text requirement document, or loads the sample URS.
2. The processing engine extracts text, creates overlapping chunks, enriches metadata, and builds a lightweight FAISS-compatible vector index.
3. A User or Admin opens **Test Case Generator**.
4. The user either searches the indexed requirement set or pastes a direct requirement, user story, system description, or reconciliation rule.
5. TestBuddy retrieves or structures requirement evidence and generates test cases.
6. Each case contains a test ID, requirement ID, objective, test type, priority, preconditions, test data, ordered steps, expected results, source evidence, and assumptions.
7. The user reviews the output and downloads Markdown, CSV, JSON, or an Excel workbook for further QA work. The workbook contains a `Test Cases` sheet and a separate `Steps` sheet, with a `Review Status` column initialized to `Pending review`.

## Supported scenario coverage

For each retrieved requirement, TestBuddy can generate selected coverage dimensions: **happy path**, **negative and validation**, **boundary and limits**, **security and privacy**, **accessibility and usability**, and **performance and reliability**. The coverage selector is explicit so the generated output can show which dimensions were requested. TestBuddy does not claim exhaustive coverage; QA analysts must review the requirement and add domain-specific scenarios.

The optional reconciliation lens covers matched transactions, unmatched source or target records, duplicate entries, mismatched amounts, mismatched transaction dates, missing mandatory identifiers, partial or split settlement, reversals or cancellations, and late-arriving records. These are coverage prompts only. The supplied requirement must define the actual business rules.

## Upload-to-Excel demonstration

1. Open TestBuddy and select either **User** or **Admin** on the initial page. The selected role is shown clearly after sign-in; there is no Guest role.
2. Use the **Test Case Generator** menu. The page is enabled for both User and Admin, while Admin-only pages are greyed out for User.
3. Upload an approved `.docx`, `.pdf`, `.md`, or `.txt` URS directly on the generator page and click **Upload and index URS**. Alternatively, use the Admin workspace to load the sample URS.
4. Confirm that the indexed chunk count is populated.
5. Select **Indexed URS document**, enter a requirement topic or identifier, and select the coverage dimensions to generate. For broad initial coverage, keep all six dimensions selected.
6. Click **Generate comprehensive test coverage**. Review the requirement candidates, source excerpts, assumptions, and generated cases.
7. Click **Download Excel**. The workbook contains a `Test Cases` summary sheet and a `Steps` detail sheet. Each case starts with `Pending review` and must be reviewed before execution.

## Features

| Feature | Description |
|---|---|
| Role support | User and Admin roles with prominent first-page sign-in and password configuration through Streamlit Secrets. |
| Document management | User/Admin upload for Word, PDF, Markdown, and text specifications, sample URS loading, and index rebuilding. |
| RAG retrieval | Local deterministic hashed embeddings with FAISS inner-product retrieval when available and NumPy fallback for testing. |
| Direct input | Paste business requirements, user stories, system descriptions, business rules, or reconciliation logic. |
| Test-case generation | Optional OpenAI-compatible structured JSON generation with deterministic retrieval-grounded fallback. |
| Traceability | Requirement ID, document name, section or chunk, page where available, and source excerpt. |
| Export | Markdown, CSV, JSON, and Excel workbook downloads. |
| Documentation | About Us and Methodology pages explain the data flow, schema, limitations, and review gates. |

## Local setup on Windows Command Prompt

Install Python 3.11 or newer and Git for Windows. Open Command Prompt in this project folder:

```cmd
cd /d C:\path\to\cpf_guide_app
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL shown by Streamlit, normally `http://localhost:8501`.

## Roles and secrets

The application uses a Home-page sign-in panel. It does not use a separate whole-application password gate. The local demonstration accepts fallback role passwords when no role secrets are configured:

| Role | Username | Demonstration password |
|---|---|---|
| User | `user` | `user` or `useraibootcamp` |
| Admin | `admin` | `admin` or `adminaibootcamp` |

For any shared or deployed environment, replace these with strong values in `.streamlit/secrets.toml` locally or Streamlit Community Cloud Secrets:

```toml
OPENAI_API_KEY = "your-new-api-key"
CARE_LLM_MODEL = "gpt-4o-mini"
USER_PASSWORD = "replace-with-a-strong-user-password"
ADMIN_PASSWORD = "replace-with-a-strong-admin-password"
```

`OPENAI_API_KEY` is optional. Without it, the application still supports retrieval, deterministic fallback test-case generation, source evidence, and export. With it, the application attempts structured JSON-schema generation from the supplied evidence.

Never commit `.streamlit/secrets.toml`. The real API key must never appear in source code, GitHub, screenshots, or chat messages. Use anonymised or synthetic data only; do not upload credentials, API keys, confidential source code, production transaction data, customer identifiers, or personal information.

## Model configuration

The default model is `gpt-4o-mini`, configurable with `CARE_LLM_MODEL`. TestBuddy uses two roles: User and Admin. The first page requires the user to select and sign in as one of these roles; inaccessible menu items are disabled until the selected role has permission. The generator sends a structured JSON schema so that each generated case has predictable fields. Model output is accepted only as a draft and must be reviewed by a QA analyst. If the API call fails, the application falls back to deterministic source-grounded cases rather than presenting an ungrounded answer.

## Project files

| File or folder | Purpose |
|---|---|
| `app.py` | Streamlit UI, role controls, document management, evidence search, test-case generator, exports, About Us, and Methodology. |
| `rag_engine.py` | Word/PDF/Markdown/text extraction, chunking, metadata, vector retrieval, and upload helpers. |
| `test_case_generator.py` | Candidate extraction, coverage dimensions, reconciliation lenses, structured generation, deterministic fallback, and Markdown/CSV/JSON/Excel serializers. |
| `sample_documents/` | `sample_urs_customer_portal.md` and `sample_online_application_urs.md` for requirement-generation demonstrations. |
| `documents/` | Local Admin-uploaded documents; non-durable prototype storage. |
| `requirements.txt` | Streamlit, FAISS, Word/PDF extraction, data, model, and Excel workbook dependencies. |
| `test_app.py` | Existing application and safety smoke tests. |
| `test_rag.py` | Sample-document indexing and retrieval smoke test. |
| `test_test_case_generator.py` | Direct-input, reconciliation, fallback, traceability, and export smoke test. |
| `.streamlit/secrets.toml.example` | Secrets template. It contains no real credential. |

## Validation

Run:

```cmd
python -m py_compile app.py rag_engine.py test_case_generator.py
python test_app.py
python test_rag.py
python test_test_case_generator.py
```

## Streamlit Community Cloud deployment

Push the repository to GitHub without `.streamlit/secrets.toml`, private documents, or API keys. Create a Streamlit Community Cloud app using:

```text
Repository: your-account/your-repository
Branch: main
Main file path: app.py
Python version: 3.12
```

Paste the contents of your secrets configuration into Streamlit Community Cloud's **Advanced settings → Secrets** field. Do not commit the secrets file to GitHub.

The local document directory and in-memory vector index are suitable for a prototype demonstration only. A production implementation should use persistent access-controlled storage, a persistent vector database, audit logging, retrieval evaluation, and formal test-case approval workflow.

## Documentation pages

The app includes:

- **About Us**, which explains the project scope, supported inputs, features, privacy boundaries, and human-review expectations.
- **Methodology**, which explains document ingestion, retrieval, structured generation, reconciliation coverage, source traceability, human-review gates, and limitations.
