import app
from test_case_generator import direct_input_candidates, generate_test_cases, reconciliation_scenarios

assert "IMPORTANT NOTICE" in app.DISCLAIMER
assert "test cases" in app.DISCLAIMER.lower()
assert app.current_role() == "Guest"
assert ".pdf" in __import__("rag_engine").SUPPORTED_EXTENSIONS
assert ".md" in __import__("rag_engine").SUPPORTED_EXTENSIONS
assert ".txt" in __import__("rag_engine").SUPPORTED_EXTENSIONS
assert app.LocalVectorStore([]).search("test") == []

candidates = direct_input_candidates(
    "The reconciliation service shall match source and target records using the agreed identifier and must flag duplicate entries.",
    input_type="Business requirement",
    scenario="Duplicate entry",
)
assert candidates
assert candidates[0]["source_section"] == "Duplicate entry"
cases, mode = generate_test_cases(candidates, client=None, include_negative=True, max_cases=4)
assert cases
assert len(cases) <= 4
assert all(case.source_excerpt for case in cases)
assert all(case.steps for case in cases)
assert "Mismatched amount" in reconciliation_scenarios()
print("TestBuddy smoke tests passed.")
