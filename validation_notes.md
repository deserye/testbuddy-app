# TestBuddy validation notes

## Current scope

TestBuddy is a source-grounded QA prototype for generating software test cases from User Requirement Specification documents, business requirements, user stories, system descriptions, business rules, and reconciliation scenarios.

## Implemented workflow

An Admin can upload PDF, Markdown, or text requirement documents and load the included sample URS. The processing engine extracts text, creates overlapping chunks, enriches source metadata, and builds a FAISS-compatible in-memory index with a NumPy fallback.

A signed-in User or Admin can search indexed requirement evidence or paste a direct requirement. The generator produces structured positive, negative, edge, and boundary cases with test IDs, linked requirement IDs, objectives, priorities, preconditions, test data, ordered steps, expected results, source excerpts, and assumptions.

The optional reconciliation lens covers matched transactions, unmatched records, duplicates, amount mismatches, date mismatches, missing identifiers, partial settlement, reversals, and late-arriving records. These are prompts for coverage and do not invent actual business rules.

## Safety and review boundaries

Generated cases are drafts and require human QA review before execution. The application instructs users to review requirement coverage, business rules, test data, expected results, assumptions, environment dependencies, and security controls. Users must use anonymised or synthetic data and must not upload credentials, API keys, confidential source code, production transaction data, customer identifiers, or personal information.

## Validation checks

The following checks passed after the redesign and rename:

```text
python3 -m py_compile app.py rag_engine.py test_case_generator.py
python3 test_app.py
python3 test_rag.py
python3 test_test_case_generator.py
```

The project includes About Us and Methodology pages, a sample URS document, role-based access, document management, evidence retrieval, optional structured model generation, deterministic fallback generation, and Markdown/CSV/JSON export.

## Deployment note

The project is compatible with Streamlit Community Cloud. Configure the API key, model name, User password, and Admin password in Streamlit Secrets. Do not commit the real secrets file. The local document directory and in-memory index are prototype storage and are not durable production infrastructure.
