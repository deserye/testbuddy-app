# CarePath: A CareShield Life and ElderShield Information Navigator

CarePath is a friendly Streamlit prototype that combines two guided long-term-care information journeys with a minimum-scope document-based RAG workflow.

The full project title is **CarePath: A CareShield Life and ElderShield Information Navigator**. It is an educational prototype and is not an official CPF Board, MOH, or AIC service.

## Minimum-scope features

| Requirement | Implementation |
|---|---|
| Web-based GenAI app | Streamlit application launched from `app.py` |
| Basic roles | Guest, User, and Admin roles; passwords can be configured through Streamlit secrets |
| Document management | Admin uploads PDF, Markdown, or text documents and can load the sample set |
| RAG-based query | Text extraction, overlapping chunks, metadata, FAISS-compatible retrieval, and source excerpts |
| Optional generation | If `OPENAI_API_KEY` is configured, the retrieved excerpts are synthesised by the configured chat model |
| Optional export | Users can download a Markdown answer containing the question, answer, and retrieved citations |
| Required documentation | About Us and Methodology pages, including separate guided-use-case flowcharts and the RAG flow |
| Deployment | Compatible with Streamlit Community Cloud |

## Local setup on Windows Command Prompt

Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/). During installation, enable **Add Python to PATH**.

Open Command Prompt in this project folder and run:

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL displayed in the terminal, normally `http://localhost:8501`.

## Roles and demo access

The default role selector starts in Guest mode. Guest users can access the guided journeys and documentation. A User can access the document query page after signing in. An Admin can upload documents, load the sample set, and rebuild the index.

For a local demonstration without secrets, the prototype accepts the fallback demo passwords `user` and `admin`. For any shared or deployed environment, configure real passwords through Streamlit secrets and do not use the fallback passwords.

## Local secrets

Create `.streamlit\secrets.toml`:

```toml
OPENAI_API_KEY = "your-secret-key"
CARE_LLM_MODEL = "gpt-4o-mini"
USER_PASSWORD = "replace-with-a-user-password"
ADMIN_PASSWORD = "replace-with-an-admin-password"
APP_PASSWORD = ""
```

The API key is optional for retrieval-only operation. Without it, the application still indexes documents, retrieves excerpts, displays citations, and supports Markdown export. The key enables optional answer synthesis.

Never commit `.streamlit\secrets.toml` to GitHub. The project includes only a `.streamlit/secrets.toml.example` template.

## Document workflow

1. Select **Admin** in the sidebar and sign in.
2. Open **Admin documents**.
3. Upload approved `.pdf`, `.md`, or `.txt` documents, or load the sample CarePath set.
4. Click **Save uploaded documents** or **Load sample CarePath documents**.
5. The app extracts text, creates overlapping chunks, records document and page metadata, and rebuilds the FAISS-compatible index.
6. Open **Document RAG** and ask a question.
7. Review the answer, retrieved excerpts, document names, section labels, page information, and scores.
8. Download the result as Markdown if required.

Only upload approved public or project documents. Do not upload medical records, NRIC information, account data, credentials, or other sensitive information.

## Vector-store design

The prototype uses `faiss-cpu` when available and stores vectors in an in-memory FAISS inner-product index. It uses deterministic local hashed embeddings so the minimum RAG flow can run without a separate embeddings API. A NumPy similarity fallback is included for local testing if FAISS is unavailable.

This is intentionally simple for a capstone prototype. A production implementation would normally use persistent storage, stronger embedding models, access-controlled document storage, source freshness monitoring, audit logging, and a more robust retrieval evaluation set.

## Project files

| File or folder | Purpose |
|---|---|
| `app.py` | Main Streamlit interface, roles, guided journeys, chatbot, RAG query page, Admin page, About Us, and Methodology |
| `rag_engine.py` | Document extraction, chunking, metadata, vector index, retrieval, and export serialization |
| `sample_documents/` | Small sample document set for demonstration |
| `documents/` | Local Admin-uploaded document directory; do not upload sensitive files |
| `assets/` | CarePath logo and supporting illustrations |
| `requirements.txt` | Streamlit, FAISS, PDF extraction, data, and model dependencies |
| `test_app.py` | Original CarePath guided-flow and safety smoke tests |
| `test_rag.py` | Sample-document indexing and retrieval smoke test |
| `research_notes.md` | Official source and scope notes |
| `validation_notes.md` | Validation record |

## Streamlit Community Cloud deployment

Push the project to a GitHub repository without `.streamlit/secrets.toml` or private documents. In Streamlit Community Cloud, create an app using `app.py` as the Main file path. Under **App settings → Secrets**, add:

```toml
OPENAI_API_KEY = "your-secret-key"
CARE_LLM_MODEL = "gpt-4o-mini"
USER_PASSWORD = "replace-with-a-user-password"
ADMIN_PASSWORD = "replace-with-an-admin-password"
APP_PASSWORD = ""
```

For a public deployment, remember that the local `documents/` directory is not a durable document-management database. Uploaded files are suitable for prototype demonstrations only. Use an approved persistent storage design for production.

## Validation

Run both test files after installation:

```cmd
python test_app.py
python test_rag.py
```

The application remains subject to the prototype disclaimer. Users must verify current and personal information with CPF Board, MOH, AIC, or another qualified official or professional source.
