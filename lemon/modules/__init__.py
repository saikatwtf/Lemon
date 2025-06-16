# Import all modules
from lemon.modules import (
    admin,
    antiflood,
    captcha,
    filters,
    notes,
    start,
    warns,
    approval,
    federation,
    greetings,
    cleaning,
    settings
)

# Collect all handlers
ALL_HANDLERS = [
    admin.HANDLERS,
    antiflood.HANDLERS,
    captcha.HANDLERS,
    filters.HANDLERS,
    notes.HANDLERS,
    start.HANDLERS,
    warns.HANDLERS,
    approval.HANDLERS,
    federation.HANDLERS,
    greetings.HANDLERS,
    cleaning.HANDLERS,
    settings.HANDLERS
]