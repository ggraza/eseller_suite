__version__ = "0.0.1"

# -----------------------------------------------------------------------------
# WARNING: MONKEY PATCHING ZONE
#
# This section rewires core behaviors at import time.
# If you touch anything here without fully understanding the consequences,
# you might accidentally set your workstation on fire. Or worse, create
# unpredictable permission behavior that will haunt you for weeks.
#
# What this does:
# - Imports core doctypes
# - Overrides their methods with our custom logic
#
# Why this is terrifying:
# - These overrides take effect globally.
# - Any update, patch, migration, or reload will execute this file and apply
#   the overrides silently.
# - A dev who adds imports below this block or rearranges them incorrectly
#   may break permissions, accounting, or ticket visibility.
#
# If you don’t know precisely how Frappe resolves method bindings:
#       Do. Not. Touch. This. Section.
#
# You’ve been warned.
# -----------------------------------------------------------------------------

from erpnext.controllers import queries
from eseller_suite.eseller_suite.queries import custom_item_query

queries.item_query = custom_item_query
