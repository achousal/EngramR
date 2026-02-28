"""Two-way vault-aware Slack bot for EngramR.

Listens for DMs, @mentions, and messages in a configured channel via
Socket Mode. Responds using the Anthropic Messages API with full vault
context (goals, identity, reminders, stats).

Runs as a standalone process alongside the daemon -- does not interfere
with the existing notification system (slack_notify.py).

All public methods are wrapped in try/except -- they never raise.
Designed to be launched via ops/scripts/slack-bot.sh in tmux.
"""

from __future__ import annotations

import contextlib
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class SlackBotConfig:
    """Configuration for the Slack bot process."""

    vault_path: Path
    slack_bot_token: str
    slack_app_token: str
    anthropic_api_key: str
    bot_channel: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_context_messages: int = 20
    max_response_tokens: int = 4096
    vault_refresh_interval_s: int = 300

    @classmethod
    def from_env(cls, vault_path: Path) -> SlackBotConfig:
        """Create config from environment variables and daemon-config.yaml.

        Required env vars: SLACK_BOT_TOKEN, SLACK_APP_TOKEN, ANTHROPIC_API_KEY.
        Optional env var: SLACK_BOT_CHANNEL.

        Bot-specific settings (model, max_context_messages, etc.) are read from
        the ``bot:`` section of ops/daemon-config.yaml, with env vars taking
        precedence for channel.

        Raises:
            ValueError: If required environment variables are missing.
        """
        missing = []
        bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        if not bot_token:
            missing.append("SLACK_BOT_TOKEN")
        app_token = os.environ.get("SLACK_APP_TOKEN", "")
        if not app_token:
            missing.append("SLACK_APP_TOKEN")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            missing.append("ANTHROPIC_API_KEY")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # Read daemon-config.yaml bot section for defaults
        bot_cfg = _load_bot_config(vault_path)

        return cls(
            vault_path=vault_path,
            slack_bot_token=bot_token,
            slack_app_token=app_token,
            anthropic_api_key=api_key,
            bot_channel=os.environ.get("SLACK_BOT_CHANNEL", "")
            or bot_cfg.get("channel", ""),
            model=bot_cfg.get("model", "claude-sonnet-4-20250514"),
            max_context_messages=bot_cfg.get("max_context_messages", 20),
            max_response_tokens=bot_cfg.get("max_response_tokens", 4096),
            vault_refresh_interval_s=bot_cfg.get("vault_refresh_interval_s", 300),
        )


def _load_bot_config(vault_path: Path) -> dict[str, Any]:
    """Load the bot section from daemon-config.yaml, returning {} on failure."""
    try:
        import yaml

        config_path = vault_path / "ops" / "daemon-config.yaml"
        if not config_path.exists():
            return {}
        raw = yaml.safe_load(config_path.read_text())
        if isinstance(raw, dict) and isinstance(raw.get("bot"), dict):
            return raw["bot"]
    except Exception:
        logger.debug("Could not read bot config from daemon-config.yaml", exc_info=True)
    return {}


# ---------------------------------------------------------------------------
# Vault context
# ---------------------------------------------------------------------------


@dataclass
class VaultContext:
    """Cached vault state used to build system prompts."""

    identity: str = ""
    methodology: str = ""
    goals: str = ""
    reminders: str = ""
    skills_summary: str = ""
    stats: str = ""


def _read_file_safe(path: Path, max_lines: int = 200) -> str:
    """Read a file, returning empty string on failure. Truncates to max_lines."""
    try:
        if not path.exists():
            return ""
        lines = path.read_text().splitlines()
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""


def load_vault_context(vault_path: Path) -> VaultContext:
    """Load vault context files for the system prompt."""
    self_dir = vault_path / "self"
    ops_dir = vault_path / "ops"

    # Count notes and hypotheses for a quick stats line
    notes_dir = vault_path / "notes"
    hyp_dir = vault_path / "_research" / "hypotheses"
    note_count = len(list(notes_dir.glob("*.md"))) if notes_dir.exists() else 0
    hyp_count = len(list(hyp_dir.glob("*.md"))) if hyp_dir.exists() else 0
    stats = f"Vault: {note_count} notes, {hyp_count} hypotheses"

    return VaultContext(
        identity=_read_file_safe(self_dir / "identity.md"),
        methodology=_read_file_safe(self_dir / "methodology.md", max_lines=80),
        goals=_read_file_safe(self_dir / "goals.md"),
        reminders=_read_file_safe(ops_dir / "reminders.md"),
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


def _merge_consecutive_roles(
    messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Merge consecutive messages with the same role.

    The Anthropic API requires alternating user/assistant roles.
    Consecutive same-role messages are joined with newlines.
    """
    if not messages:
        return []

    merged: list[dict[str, str]] = [messages[0].copy()]
    for msg in messages[1:]:
        if msg["role"] == merged[-1]["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(msg.copy())
    return merged


# ---------------------------------------------------------------------------
# SlackBot
# ---------------------------------------------------------------------------


@dataclass
class SlackBot:
    """Two-way vault-aware Slack assistant.

    Args:
        config: Bot configuration.
        app: Optional pre-built slack_bolt.App (for testing).
        anthropic_client: Optional pre-built anthropic.Anthropic (for testing).
    """

    config: SlackBotConfig
    app: Any = field(default=None, repr=False)
    anthropic_client: Any = field(default=None, repr=False)
    _bot_user_id: str = field(default="", init=False, repr=False)
    _vault_context: VaultContext = field(
        default_factory=VaultContext, init=False, repr=False
    )
    _refresh_timer: threading.Timer | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.app is None:
            from slack_bolt import App

            self.app = App(token=self.config.slack_bot_token)

        if self.anthropic_client is None:
            import anthropic

            self.anthropic_client = anthropic.Anthropic(
                api_key=self.config.anthropic_api_key
            )

        # Register event handlers -- separate handlers to avoid routing conflicts
        self.app.event("app_mention")(self._handle_mention)
        self.app.event("message")(self._handle_message)

        # Log all unhandled events for debugging
        @self.app.middleware
        def _log_all_events(body, next):
            event = body.get("event", {})
            etype = event.get("type", "unknown")
            esubtype = event.get("subtype", "")
            logger.debug(
                "Incoming event: type=%s subtype=%s user=%s channel=%s",
                etype,
                esubtype,
                event.get("user", ""),
                event.get("channel", ""),
            )
            next()

        # Load initial vault context
        self.refresh_vault_context()

    def start(self) -> None:
        """Start the bot (blocking). Connects via Socket Mode."""
        from slack_bolt.adapter.socket_mode import SocketModeHandler

        # Resolve bot identity
        try:
            auth = self.app.client.auth_test()
            self._bot_user_id = auth.get("user_id", "")
            logger.info("Bot identity resolved: %s", self._bot_user_id)
        except Exception:
            logger.warning("Could not resolve bot identity via auth.test")

        # Start periodic vault refresh
        self._schedule_vault_refresh()

        logger.info("Starting Slack bot via Socket Mode...")
        handler = SocketModeHandler(self.app, self.config.slack_app_token)
        handler.start()

    # -- Event handling -----------------------------------------------------

    def _handle_mention(self, event: dict[str, Any], say: Any, client: Any) -> None:
        """Handle app_mention events. Delegates to the shared handler."""
        logger.info("app_mention event received from user=%s", event.get("user", ""))
        self._process_event(event, say, client)

    def _handle_message(self, event: dict[str, Any], say: Any, client: Any) -> None:
        """Handle message events (DMs, bot channel). Skips @mentions (handled above)."""
        # Skip if this is an @mention -- already handled by _handle_mention
        text = event.get("text", "")
        if self._bot_user_id and f"<@{self._bot_user_id}>" in text:
            channel_type = event.get("channel_type", "")
            if channel_type != "im":
                return
        logger.info(
            "message event received: user=%s channel_type=%s",
            event.get("user", ""),
            event.get("channel_type", ""),
        )
        self._process_event(event, say, client)

    def _process_event(self, event: dict[str, Any], say: Any, client: Any) -> None:
        """Shared handler for message and app_mention events."""
        try:
            if not self._should_respond(event):
                return

            channel = event.get("channel", "")
            thread_ts = event.get("thread_ts") or event.get("ts", "")
            user_text = event.get("text", "")

            # Strip bot mention from text
            if self._bot_user_id:
                user_text = user_text.replace(f"<@{self._bot_user_id}>", "").strip()

            # Add thinking reaction
            with contextlib.suppress(Exception):
                client.reactions_add(
                    name="thinking_face",
                    channel=channel,
                    timestamp=event.get("ts", ""),
                )

            # Build thread context
            thread_messages = self._build_thread_context(
                client, channel, thread_ts, user_text
            )

            # Build system prompt
            system = self.build_system_prompt()

            # Call Claude
            response_text = self._call_claude(thread_messages, system)

            # Split long responses (Slack limit ~4000 chars per message)
            chunks = _split_message(response_text, max_len=3900)
            for chunk in chunks:
                say(text=chunk, thread_ts=thread_ts)

            # Remove thinking reaction, add done
            try:
                client.reactions_remove(
                    name="thinking_face",
                    channel=channel,
                    timestamp=event.get("ts", ""),
                )
                client.reactions_add(
                    name="white_check_mark",
                    channel=channel,
                    timestamp=event.get("ts", ""),
                )
            except Exception:
                pass  # Non-critical

        except Exception:
            logger.exception("Error handling message event")
            with contextlib.suppress(Exception):
                say(
                    text="Sorry, I encountered an error processing your message.",
                    thread_ts=event.get("thread_ts") or event.get("ts", ""),
                )

    def _should_respond(self, event: dict[str, Any]) -> bool:
        """Determine whether the bot should respond to this event.

        Responds to:
        - Direct messages (channel_type == 'im')
        - @mentions (text contains bot user ID)
        - Messages in the configured bot_channel

        Skips:
        - Messages from the bot itself
        - Messages with subtypes (joins, leaves, etc.) except bot_message
        """
        # Skip own messages
        user = event.get("user", "")
        if self._bot_user_id and user == self._bot_user_id:
            return False

        # Skip bot_id messages (from other integrations or self)
        if event.get("bot_id"):
            return False

        # Skip message subtypes (join/leave/topic etc.)
        subtype = event.get("subtype", "")
        if subtype:
            return False

        # Direct messages
        channel_type = event.get("channel_type", "")
        if channel_type == "im":
            return True

        # @mention
        text = event.get("text", "")
        if self._bot_user_id and f"<@{self._bot_user_id}>" in text:
            return True

        # Bot channel
        channel = event.get("channel", "")
        return bool(self.config.bot_channel and channel == self.config.bot_channel)

    def _build_thread_context(
        self,
        client: Any,
        channel: str,
        thread_ts: str,
        current_text: str,
    ) -> list[dict[str, str]]:
        """Build conversation context from thread history.

        Fetches thread replies, maps bot messages to assistant role and
        all others to user role, merges consecutive same-role messages,
        and caps at max_context_messages.

        Falls back to just the current message on API errors.
        """
        messages: list[dict[str, str]] = []

        try:
            result = client.conversations_replies(channel=channel, ts=thread_ts)
            thread_msgs = result.get("messages", [])

            for msg in thread_msgs:
                msg_user = msg.get("user", "")
                msg_text = msg.get("text", "")

                # Strip bot mention from text
                if self._bot_user_id:
                    msg_text = msg_text.replace(f"<@{self._bot_user_id}>", "").strip()

                if not msg_text:
                    continue

                if self._bot_user_id and msg_user == self._bot_user_id:
                    role = "assistant"
                else:
                    role = "user"

                messages.append({"role": role, "content": msg_text})

        except Exception:
            logger.debug("Could not fetch thread replies, using current message only")
            if current_text:
                messages = [{"role": "user", "content": current_text}]

        if not messages:
            if current_text:
                messages = [{"role": "user", "content": current_text}]
            else:
                return []

        # Cap at max_context_messages
        messages = messages[-self.config.max_context_messages :]

        # Merge consecutive same-role messages
        messages = _merge_consecutive_roles(messages)

        # Ensure conversation starts with user
        if messages and messages[0]["role"] != "user":
            messages = messages[1:]

        # Ensure conversation ends with user
        if messages and messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": "(waiting for response)"})

        return messages

    def build_system_prompt(self) -> str:
        """Assemble the system prompt from cached vault context."""
        ctx = self._vault_context
        sections = []

        sections.append(
            "You are a research assistant for a bioinformatics knowledge vault "
            "(EngramR). You help the researcher with questions about their "
            "research goals, hypotheses, vault contents, and general science. "
            "Be concise and direct. Use markdown formatting."
        )

        if ctx.identity:
            sections.append(f"## Identity\n{ctx.identity}")

        if ctx.goals:
            sections.append(f"## Current Research Goals\n{ctx.goals}")

        if ctx.reminders:
            sections.append(f"## Active Reminders\n{ctx.reminders}")

        if ctx.stats:
            sections.append(f"## Vault Stats\n{ctx.stats}")

        if ctx.methodology:
            sections.append(f"## Methodology (abbreviated)\n{ctx.methodology}")

        return "\n\n".join(sections)

    def refresh_vault_context(self) -> None:
        """Re-read vault files into the cached context."""
        try:
            self._vault_context = load_vault_context(self.config.vault_path)
            logger.debug("Vault context refreshed")
        except Exception:
            logger.exception("Failed to refresh vault context")

    def _schedule_vault_refresh(self) -> None:
        """Schedule periodic vault context refresh."""
        interval = self.config.vault_refresh_interval_s
        if interval <= 0:
            return

        def _refresh_loop() -> None:
            self.refresh_vault_context()
            self._refresh_timer = threading.Timer(interval, _refresh_loop)
            self._refresh_timer.daemon = True
            self._refresh_timer.start()

        self._refresh_timer = threading.Timer(interval, _refresh_loop)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    # -- Claude API ---------------------------------------------------------

    def _call_claude(
        self,
        messages: list[dict[str, str]],
        system: str,
    ) -> str:
        """Call the Anthropic Messages API. Returns text or error message."""
        try:
            response = self.anthropic_client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_response_tokens,
                system=system,
                messages=messages,
            )
            # Extract text from response content blocks
            parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
            return "\n".join(parts) if parts else "(empty response)"

        except Exception as exc:
            logger.exception("Claude API call failed")
            # Return a user-friendly message; full details are in the logs
            err_type = type(exc).__name__
            return (
                f"Sorry, I could not generate a response ({err_type}). "
                "Check the bot logs for details."
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_message(text: str, max_len: int = 3900) -> list[str]:
    """Split a message into chunks that fit Slack's character limit."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Try to split at a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at <= 0:
            # Fall back to space
            split_at = text.rfind(" ", 0, max_len)
        if split_at <= 0:
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entrypoint for the Slack bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    vault_path = Path(os.environ.get("VAULT_PATH", Path.cwd()))
    config = SlackBotConfig.from_env(vault_path)
    bot = SlackBot(config=config)
    bot.start()


if __name__ == "__main__":
    main()
