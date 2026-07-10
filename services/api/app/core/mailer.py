"""Verification-email delivery.

There is no SMTP transport in this project, so the default mailer is a **dev
mailer**: it writes the verification link to ``<DATA_DIR>/outbox/`` and logs it.
Swap in a real transport (SES/SendGrid/SMTP) for production.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DevMailer:
    """Writes verification links to an on-disk outbox and the log."""

    def __init__(self, outbox_dir: Path) -> None:
        self._outbox = outbox_dir

    def send_verification(self, email: str, token: str) -> None:
        """'Send' a verification link for ``email`` carrying ``token``."""
        self._outbox.mkdir(parents=True, exist_ok=True)
        safe = email.replace("@", "_at_").replace("/", "_")
        (self._outbox / f"{safe}.txt").write_text(
            f"Verify {email} with token:\n{token}\n", encoding="utf-8"
        )
        logger.info("DEV MAILER: verification token for %s -> %s", email, token)
