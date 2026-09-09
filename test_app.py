import app

coverage = app.coverage_output(
    "Born in 1980 or after",
    "Claims and severe disability",
    "Family member or caregiver",
)
assert len(coverage["prompts"]) == 3
assert any("six activities of daily living" in item for item in coverage["prompts"])
assert any("AIC" in item for item in coverage["prompts"])

care = app.care_output(
    "Caregiver or family member",
    "Apply or find application support",
    "AIC",
)
assert len(care["checklist"]) == 5
assert any("eFASS" in item for item in care["checklist"])
assert any("mental capacity" in item for item in care["checklist"])

assert "IMPORTANT NOTICE" in app.DISCLAIMER
assert "CareShield Life" in app.SOURCE_CONTEXT
assert "ElderShield" in app.SOURCE_CONTEXT
assert "long-term-care" in app.SOURCE_CONTEXT
assert app.current_role() == "Guest"
assert ".pdf" in __import__("rag_engine").SUPPORTED_EXTENSIONS
assert ".md" in __import__("rag_engine").SUPPORTED_EXTENSIONS
assert ".txt" in __import__("rag_engine").SUPPORTED_EXTENSIONS
assert app.LocalVectorStore([]).search("test") == []
original_get_secret = app.get_secret
app.get_secret = lambda name: ""
assert "not connected" in app.assistant_reply([])
app.get_secret = original_get_secret
print("CarePath deterministic smoke tests passed.")
