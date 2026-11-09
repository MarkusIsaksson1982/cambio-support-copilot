"""Offline eval pack: schema, citations, patient-data handoff, three repeats."""
from copilot.eval.pack import evaluate, render_markdown


def test_eval_pack_gates():
    summary = evaluate(runs=3)
    assert summary["tickets"] == 44
    assert summary["schema_pass"] == 1
    assert summary["audit_match"] == 1
    assert summary["patient_data_cases"] > 0
    assert summary["patient_data_handoff"] == 1
    assert summary["needs_human_cases"] > 0
    assert summary["needs_human_handoff"] == 1
    assert summary["retrieval_hits"] >= summary["citation_eligible"]
    assert summary["citation_cited"] > 0
    assert summary["citation_faithfulness"] == 1
    assert summary["citation_eligible"] > 0
    assert summary["citation_recall"] == 1
    assert summary["incident_chains"] > 0
    assert summary["incident_schema_pass"] == 1
    assert summary["repeat_mismatches"] == []
    report = render_markdown(summary)
    assert "44" in report
    assert "live model is not" in report
