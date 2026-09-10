from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass
class TestStep:
    step: int
    action: str
    expected_result: str


@dataclass
class GeneratedTestCase:
    test_case_id: str
    requirement_id: str
    title: str
    objective: str
    test_type: str
    priority: str
    preconditions: list[str]
    test_data: list[str]
    steps: list[TestStep]
    expected_result: str
    source_document: str
    source_section: str
    source_excerpt: str
    assumptions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TEST_CASE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "test_case_id": {"type": "string"},
            "requirement_id": {"type": "string"},
            "title": {"type": "string"},
            "objective": {"type": "string"},
            "test_type": {"type": "string"},
            "priority": {"type": "string"},
            "preconditions": {"type": "array", "items": {"type": "string"}},
            "test_data": {"type": "array", "items": {"type": "string"}},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step": {"type": "integer"},
                        "action": {"type": "string"},
                        "expected_result": {"type": "string"},
                    },
                    "required": ["step", "action", "expected_result"],
                    "additionalProperties": False,
                },
            },
            "expected_result": {"type": "string"},
            "source_document": {"type": "string"},
            "source_section": {"type": "string"},
            "source_excerpt": {"type": "string"},
            "assumptions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "test_case_id", "requirement_id", "title", "objective", "test_type",
            "priority", "preconditions", "test_data", "steps", "expected_result",
            "source_document", "source_section", "source_excerpt", "assumptions",
        ],
        "additionalProperties": False,
    },
}


def _normalise_requirement_id(text: str, index: int) -> str:
    match = re.search(r"\b(?:REQ|FR|NFR|URS)[-_ ]?\d+(?:[-.]\d+)*\b", text, re.I)
    return match.group(0).upper().replace(" ", "-") if match else f"REQ-{index:03d}"


def extract_requirement_candidates(results: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        text = re.sub(r"\s+", " ", str(result.get("text", "")).strip())
        if not text:
            continue
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        for sentence in sentences:
            sentence = sentence.strip(" -•")
            if len(sentence) < 25:
                continue
            if not re.search(r"\b(shall|must|required to|should|system will|the system)", sentence, re.I):
                continue
            rid = _normalise_requirement_id(sentence, len(candidates) + 1)
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "requirement_id": rid,
                "requirement_text": sentence,
                "source_document": result.get("document_name", "Unknown document"),
                "source_section": result.get("section", "Unknown section"),
                "source_excerpt": result.get("source_excerpt", sentence),
            })
            if len(candidates) >= limit:
                return candidates
    if not candidates and results:
        for index, result in enumerate(results[:limit], start=1):
            text = re.sub(r"\s+", " ", str(result.get("text", "")).strip())
            if text:
                candidates.append({
                    "requirement_id": f"REQ-{index:03d}",
                    "requirement_text": text[:500],
                    "source_document": result.get("document_name", "Unknown document"),
                    "source_section": result.get("section", "Unknown section"),
                    "source_excerpt": result.get("source_excerpt", text[:320]),
                })
    return candidates


def _fallback_case(candidate: dict[str, Any], case_number: int, negative: bool = False) -> GeneratedTestCase:
    rid = candidate["requirement_id"]
    req = candidate["requirement_text"]
    if negative:
        title = f"Reject invalid or incomplete input for {rid}"
        objective = f"Verify that the system handles an invalid, missing, or boundary input related to: {req}"
        test_type = "Negative / validation"
        priority = "High"
        data = ["Missing required field, invalid format, or value outside the stated rule"]
        steps = [
            TestStep(1, "Prepare the feature with an invalid or incomplete input relevant to the requirement.", "The invalid condition is ready for submission."),
            TestStep(2, "Submit or trigger the relevant system action.", "The system prevents the invalid transaction and provides a clear validation message."),
            TestStep(3, "Correct the input and retry the action.", "The system accepts the corrected input when all stated conditions are satisfied."),
        ]
        expected = "The system rejects the invalid condition without saving an incorrect result and provides actionable feedback."
    else:
        title = f"Verify expected behaviour for {rid}"
        objective = f"Verify that the system satisfies the stated requirement: {req}"
        test_type = "Functional / positive"
        priority = "High"
        data = ["Valid input that satisfies every condition stated in the requirement"]
        steps = [
            TestStep(1, "Arrange the preconditions and prepare valid test data.", "The test environment is ready and the data satisfies the requirement."),
            TestStep(2, "Perform the user or system action described by the requirement.", "The system processes the action without unexpected errors."),
            TestStep(3, "Verify the resulting state, response, or output.", "The observed result matches the stated requirement."),
        ]
        expected = "The system produces the outcome described by the requirement and preserves the expected data and audit state."
    return GeneratedTestCase(
        test_case_id=f"TC-{case_number:03d}",
        requirement_id=rid,
        title=title,
        objective=objective,
        test_type=test_type,
        priority=priority,
        preconditions=["Relevant application feature is available.", "Tester has the required role and permissions."],
        test_data=data,
        steps=steps,
        expected_result=expected,
        source_document=candidate["source_document"],
        source_section=candidate["source_section"],
        source_excerpt=candidate["source_excerpt"],
        assumptions=["Detailed interface labels and field names are to be confirmed against the final design.", "No behaviour beyond the supplied requirement is assumed."],
    )


def direct_input_candidates(text: str, input_type: str = "Business requirement", scenario: str = "General") -> list[dict[str, Any]]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    parts = [part.strip() for part in re.split(r"\n{2,}|(?<=\.)\s+(?=(?:The system|The solution|As a |When |Given |It shall |It must ))", text.strip()) if part.strip()]
    if not parts:
        parts = [cleaned]
    candidates = []
    for index, part in enumerate(parts[:12], start=1):
        candidates.append({
            "requirement_id": _normalise_requirement_id(part, index),
            "requirement_text": re.sub(r"\s+", " ", part).strip(),
            "source_document": f"Direct {input_type} input",
            "source_section": scenario or "Direct input",
            "source_excerpt": re.sub(r"\s+", " ", part).strip()[:500],
        })
    return candidates


def reconciliation_scenarios() -> list[str]:
    return [
        "Matched transactions",
        "Unmatched source record",
        "Unmatched target record",
        "Duplicate entry",
        "Mismatched amount",
        "Mismatched transaction date",
        "Missing mandatory identifier",
        "Partial or split settlement",
        "Reversal or cancellation",
        "Late-arriving record",
    ]


def fallback_generate(candidates: list[dict[str, Any]], include_negative: bool = True, max_cases: int = 10) -> list[GeneratedTestCase]:
    cases: list[GeneratedTestCase] = []
    for candidate in candidates:
        cases.append(_fallback_case(candidate, len(cases) + 1, negative=False))
        if include_negative and len(cases) < max_cases:
            cases.append(_fallback_case(candidate, len(cases) + 1, negative=True))
        if len(cases) >= max_cases:
            break
    return cases


def _clean_model_cases(payload: Any, candidates: list[dict[str, Any]]) -> list[GeneratedTestCase]:
    by_req = {item["requirement_id"]: item for item in candidates}
    cleaned: list[GeneratedTestCase] = []
    for index, item in enumerate(payload if isinstance(payload, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        requirement_id = str(item.get("requirement_id") or f"REQ-{index:03d}")
        source = by_req.get(requirement_id, candidates[min(index - 1, len(candidates) - 1)] if candidates else {})
        steps = []
        for step_index, step in enumerate(item.get("steps", []), start=1):
            if isinstance(step, dict):
                steps.append(TestStep(int(step.get("step") or step_index), str(step.get("action", "")), str(step.get("expected_result", ""))))
        if not steps:
            steps = _fallback_case(source or {"requirement_id": requirement_id, "requirement_text": "", "source_document": "Unknown", "source_section": "Unknown", "source_excerpt": ""}, index).steps
        cleaned.append(GeneratedTestCase(
            test_case_id=str(item.get("test_case_id") or f"TC-{index:03d}"),
            requirement_id=requirement_id,
            title=str(item.get("title", f"Test {requirement_id}")),
            objective=str(item.get("objective", "")),
            test_type=str(item.get("test_type", "Functional")),
            priority=str(item.get("priority", "Medium")),
            preconditions=[str(x) for x in item.get("preconditions", [])],
            test_data=[str(x) for x in item.get("test_data", [])],
            steps=steps,
            expected_result=str(item.get("expected_result", "")),
            source_document=str(item.get("source_document") or source.get("source_document", "Unknown document")),
            source_section=str(item.get("source_section") or source.get("source_section", "Unknown section")),
            source_excerpt=str(item.get("source_excerpt") or source.get("source_excerpt", "")),
            assumptions=[str(x) for x in item.get("assumptions", [])],
        ))
    return cleaned


def llm_generate(client: Any, model: str, candidates: list[dict[str, Any]], include_negative: bool, max_cases: int) -> list[GeneratedTestCase]:
    if not candidates:
        return []
    prompt = {
        "requirements": candidates,
        "instructions": {
            "max_cases": max_cases,
            "include_negative_cases": include_negative,
            "rules": [
                "Generate test cases only from the supplied requirement candidates.",
                "Do not invent business rules, field values, roles, integrations, or acceptance criteria.",
                "Create positive and negative/boundary coverage when the requirement supports it.",
                "Preserve source_document, source_section, and source_excerpt for every case.",
                "Use concise, executable steps with an expected result per step.",
                "If a detail is missing, record it under assumptions instead of guessing.",
            ],
        },
    }
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a senior QA analyst. Generate precise, source-grounded software test cases from URS requirements. Output only the requested JSON array."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        response_format={"type": "json_schema", "json_schema": {"name": "test_cases", "strict": True, "schema": TEST_CASE_SCHEMA}},
        max_tokens=5000,
    )
    content = response.choices[0].message.content if response.choices else "[]"
    return _clean_model_cases(json.loads(content or "[]"), candidates)


def generate_test_cases(candidates: list[dict[str, Any]], client: Any | None = None, model: str = "gpt-4o-mini", include_negative: bool = True, max_cases: int = 10) -> tuple[list[GeneratedTestCase], str]:
    if client is not None:
        try:
            cases = llm_generate(client, model, candidates, include_negative, max_cases)
            if cases:
                return cases[:max_cases], "LLM-generated from retrieved URS evidence"
        except Exception:
            pass
    return fallback_generate(candidates, include_negative=include_negative, max_cases=max_cases), "Deterministic retrieval-grounded fallback"


def cases_to_markdown(cases: list[GeneratedTestCase], title: str = "Generated Test Cases") -> str:
    lines = [f"# {title}", "", f"Generated test cases: {len(cases)}", ""]
    for case in cases:
        lines.extend([f"## {case.test_case_id} — {case.title}", "", f"- **Requirement:** {case.requirement_id}", f"- **Type:** {case.test_type}", f"- **Priority:** {case.priority}", f"- **Objective:** {case.objective}", "", "### Preconditions"])
        lines.extend([f"- {item}" for item in case.preconditions] or ["- None specified"])
        lines.append("\n### Test data")
        lines.extend([f"- {item}" for item in case.test_data] or ["- None specified"])
        lines.append("\n### Steps")
        lines.append("| Step | Action | Expected result |")
        lines.append("|---:|---|---|")
        lines.extend([f"| {step.step} | {step.action} | {step.expected_result} |" for step in case.steps])
        lines.extend(["", f"**Overall expected result:** {case.expected_result}", "", f"**Source:** `{case.source_document}` · {case.source_section}", f"> {case.source_excerpt}", "", "### Assumptions"])
        lines.extend([f"- {item}" for item in case.assumptions] or ["- None specified"])
        lines.append("")
    return "\n".join(lines)


def cases_to_rows(cases: list[GeneratedTestCase]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        row = case.to_dict()
        row["preconditions"] = "\n".join(case.preconditions)
        row["test_data"] = "\n".join(case.test_data)
        row["steps"] = "\n".join(f"{step.step}. {step.action} → {step.expected_result}" for step in case.steps)
        row["assumptions"] = "\n".join(case.assumptions)
        del row["source_excerpt"]
        rows.append(row)
    return rows


def cases_to_json(cases: list[GeneratedTestCase]) -> str:
    return json.dumps([case.to_dict() for case in cases], ensure_ascii=False, indent=2)
