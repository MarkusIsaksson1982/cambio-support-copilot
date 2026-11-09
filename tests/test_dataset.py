import json
from copilot.core.adapters import NoneAdapter
from copilot.core.pipeline import run


def test_dataset_run_all():
    with open("data/support_tickets.jsonl", encoding="utf-8") as f:
        tickets = [json.loads(line) for line in f if line.strip()]

    passed = 0
    failed = 0
    rules_decided_correct = 0
    rules_decided_total = 0

    for ticket in tickets:
        result = run(ticket, adapter=NoneAdapter())
        status_ok = result["status"] == ticket["expected_status"]
        if status_ok:
            passed += 1
        else:
            failed += 1

        rule = result.get("rule", {})
        label_decided = rule.get("label") is not None
        if label_decided:
            rules_decided_total += 1
            if rule.get("label") == ticket["expected_label"]:
                rules_decided_correct += 1

    accuracy = rules_decided_correct / rules_decided_total if rules_decided_total > 0 else 1.0
    assert passed == len(tickets), f"{failed}/{len(tickets)} tickets failed expected status"
    assert accuracy >= 0.8, f"Label accuracy {accuracy:.2f} < 0.8 for rules-decided tickets"