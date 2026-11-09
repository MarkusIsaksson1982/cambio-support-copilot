"""Rule-first classification of Swedish support tickets (inspired by arende-triage/rules.py).

Weighted phrases per label. A label wins when its score >= MIN_SCORE and beats the
runner-up by MARGIN; otherwise the rules are undecided and the model may propose.
"""
from __future__ import annotations

import re

from copilot.core.plugin import RuleResult

LABELS = ["inloggning", "behorighet", "journalfel", "bugg", "instruktion", "ovrigt"]
DISPLAY = {"inloggning": "Inloggning / SITHS", "behorighet": "Behörighet / åtkomst",
           "journalfel": "Fel i patientjournal", "bugg": "Systemfel / bugg",
           "instruktion": "Hur gör jag?", "ovrigt": "Övrigt"}
ROUTES = {"inloggning": "forsta_linjen", "behorighet": "behorighetsansvarig",
          "journalfel": "patientsakerhet", "bugg": "andra_linjen_teknik",
          "instruktion": "forsta_linjen", "ovrigt": "forsta_linjen"}

PATTERNS: dict[str, list[tuple[str, int]]] = {
    "inloggning": [(r"logga in|inloggning|inloggad", 2), (r"siths|e-tjänstekort|bankid", 3),
                   (r"lösenord|pinkod|pin-kod", 2), (r"utloggad|session", 1)],
    "behorighet": [(r"behörighet", 3), (r"åtkomst|komma åt", 2), (r"saknar (rätt|tillgång)", 2),
                   (r"medarbetaruppdrag|vårdrelation", 3), (r"spärrad journal|sammanhållen", 2)],
    "journalfel": [(r"fel patient|annan patient|fel journal", 4), (r"förväxla\w* (patient|journal)|patientförväxling", 4), (r"journalanteckning.*(försvunnit|fel)", 3),
                   (r"läkemedelslista\w* (är|var|visar) fel|fel ?dos|dubbel ?dos|feldos", 4), (r"\bavvikelse\b", 2), (r"felaktig(t)? journal", 3)],
    "bugg": [(r"krasch|kraschar|hänger sig|fryser", 3), (r"felmeddelande|error|fel ?kod", 2),
             (r"går inte att spara|sparas inte", 2), (r"långsam|laddar", 1)],
    "instruktion": [(r"hur (gör|kan|ska) jag", 3), (r"var hittar jag", 3), (r"instruktion|manual", 2),
                   (r"uttagning|ta fram|statistik per|körning vi kan få|anpassat datauttag", 3)],
}
MIN_SCORE, MARGIN = 3, 2
# Patient-safety phrases always go to a human, whatever the label.
SAFETY = [r"fel patient", r"annan patient", r"förväxla\w* (patient|journal)", r"patientförväxling",
          r"fel ?dos", r"dubbel ?dos", r"vårdskada"]


def classify(masked_text: str) -> RuleResult:
    t = masked_text.lower()
    scores: dict[str, int] = {}
    hits = []
    for label, pats in PATTERNS.items():
        for pat, w in pats:
            m = re.search(pat, t)
            if m:
                scores[label] = scores.get(label, 0) + w
                hits.append({"label": label, "phrase": m.group(0), "weight": w})
    forced = []
    if any(re.search(p, t) for p in SAFETY):
        forced.append("patient_safety")
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    if not ranked:
        return RuleResult(None, 0.0, hits, None, forced)
    top, s1 = ranked[0]
    s2 = ranked[1][1] if len(ranked) > 1 else 0
    if s1 >= MIN_SCORE and s1 - s2 >= MARGIN:
        conf = round(min(0.95, 0.6 + 0.05 * (s1 - s2)), 2)
        return RuleResult(top, conf, hits, ROUTES[top], forced)
    return RuleResult(None, 0.0, hits, None, forced)
