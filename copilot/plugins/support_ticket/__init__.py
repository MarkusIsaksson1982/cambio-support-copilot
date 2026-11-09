from copilot.core.plugin import register, registered
from copilot.plugins.support_ticket.plugin import SupportTicketPlugin

if "support_ticket" not in registered():
    register(SupportTicketPlugin())
