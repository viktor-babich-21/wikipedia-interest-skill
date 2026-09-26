"""Wikipedia article attention tools for an Agent Skill.

``resolve`` looks up Wikipedia articles through MediaWiki. ``report`` fetches
daily pageviews into ``pageviews.json``. Metrics, charts, and PDFs come later.
"""

__version__ = "0.1.0"


class ContractError(ValueError):
    """Raised when request or result JSON does not match the contract."""
