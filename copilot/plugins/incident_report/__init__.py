"""incident_report (avvikelse). See docs/EXTENDING.md path (a).

Path (a): fill in plugin.py and it registers like support_ticket.
Path (b): build a separate project that consumes contracts/handoff_envelope.v1.schema.json
and returns contracts/incident_report.v1.schema.json; see copilot/chain.py.
"""
from copilot.core.plugin import register, registered
from copilot.plugins.incident_report.plugin import IncidentReportPlugin

if "incident_report" not in registered():
    register(IncidentReportPlugin())
