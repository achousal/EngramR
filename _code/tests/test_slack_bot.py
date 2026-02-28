"""Tests for the two-way vault-aware Slack bot."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engram_r.slack_bot import (
    SlackBot,
    SlackBotConfig,
    VaultContext,
    _merge_consecutive_roles,
    _split_message,
    load_vault_context,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Create a minimal vault structure for testing."""
    (tmp_path / "self").mkdir()
    (tmp_path / "ops").mkdir()
    (tmp_path / "notes").mkdir()
    (tmp_path / "_research" / "hypotheses").mkdir(parents=True)

    (tmp_path / "self" / "identity.md").write_text("# Identity\nI am the agent.")
    (tmp_path / "self" / "methodology.md").write_text("# Methodology\nIterative.")
    (tmp_path / "self" / "goals.md").write_text("# Goals\n## AD biomarkers\nActive.")
    (tmp_path / "ops" / "reminders.md").write_text("- [ ] Submit LONI request")

    # Create some notes and hypotheses
    for i in range(5):
        (tmp_path / "notes" / f"note-{i}.md").write_text(f"Note {i}")
    for i in range(3):
        (tmp_path / "_research" / "hypotheses" / f"H-{i}.md").write_text(f"H {i}")

    return tmp_path


@pytest.fixture()
def config(vault: Path) -> SlackBotConfig:
    """Create a test config."""
    return SlackBotConfig(
        vault_path=vault,
        slack_bot_token="xoxb-test-token",
        slack_app_token="xapp-test-token",
        anthropic_api_key="sk-ant-test-key",
        bot_channel="C_BOT_CHAN",
        model="claude-sonnet-4-20250514",
        max_context_messages=10,
        max_response_tokens=1024,
        vault_refresh_interval_s=0,  # Disable timer in tests
    )


def _mock_anthropic_response(text: str = "Hello from Claude") -> MagicMock:
    """Create a mock Anthropic API response."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


@pytest.fixture()
def mock_app() -> MagicMock:
    """Create a mock slack_bolt App."""
    app = MagicMock()
    # event() should return a decorator that accepts a handler
    app.event = MagicMock(side_effect=lambda event_name: lambda fn: fn)
    app.client.auth_test.return_value = {"user_id": "U_BOT"}
    return app


@pytest.fixture()
def mock_anthropic() -> MagicMock:
    """Create a mock Anthropic client."""
    client = MagicMock()
    client.messages.create.return_value = _mock_anthropic_response()
    return client


@pytest.fixture()
def bot(
    config: SlackBotConfig, mock_app: MagicMock, mock_anthropic: MagicMock
) -> SlackBot:
    """Create a SlackBot with mocked dependencies."""
    b = SlackBot(config=config, app=mock_app, anthropic_client=mock_anthropic)
    b._bot_user_id = "U_BOT"
    return b


# ---------------------------------------------------------------------------
# Config factory tests
# ---------------------------------------------------------------------------


class TestSlackBotConfig:
    def test_from_env_success(self, vault: Path) -> None:
        env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "SLACK_BOT_CHANNEL": "C_CHAN",
        }
        with patch.dict("os.environ", env, clear=False):
            cfg = SlackBotConfig.from_env(vault)
        assert cfg.slack_bot_token == "xoxb-test"
        assert cfg.slack_app_token == "xapp-test"
        assert cfg.anthropic_api_key == "sk-ant-test"
        assert cfg.bot_channel == "C_CHAN"

    def test_from_env_missing_vars_raises(self, vault: Path) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="SLACK_BOT_TOKEN"),
        ):
            SlackBotConfig.from_env(vault)

    def test_from_env_reads_daemon_config(self, vault: Path) -> None:
        # Write a daemon-config with bot section
        config_yaml = (
            "bot:\n" "  model: claude-opus-4-20250514\n" "  max_context_messages: 50\n"
        )
        (vault / "ops" / "daemon-config.yaml").write_text(config_yaml)

        env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
            "ANTHROPIC_API_KEY": "sk-ant-test",
        }
        with patch.dict("os.environ", env, clear=False):
            cfg = SlackBotConfig.from_env(vault)
        assert cfg.model == "claude-opus-4-20250514"
        assert cfg.max_context_messages == 50

    def test_from_env_env_channel_overrides_config(self, vault: Path) -> None:
        config_yaml = "bot:\n  channel: C_FROM_YAML\n"
        (vault / "ops" / "daemon-config.yaml").write_text(config_yaml)

        env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "SLACK_BOT_CHANNEL": "C_FROM_ENV",
        }
        with patch.dict("os.environ", env, clear=False):
            cfg = SlackBotConfig.from_env(vault)
        assert cfg.bot_channel == "C_FROM_ENV"

    def test_from_env_missing_one_var(self, vault: Path) -> None:
        env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            # Missing SLACK_APP_TOKEN and ANTHROPIC_API_KEY
        }
        with (
            patch.dict("os.environ", env, clear=True),
            pytest.raises(ValueError, match="SLACK_APP_TOKEN"),
        ):
            SlackBotConfig.from_env(vault)


# ---------------------------------------------------------------------------
# _should_respond tests
# ---------------------------------------------------------------------------


class TestShouldRespond:
    def test_dm_returns_true(self, bot: SlackBot) -> None:
        event = {"channel_type": "im", "user": "U_HUMAN", "text": "hello"}
        assert bot._should_respond(event) is True

    def test_mention_returns_true(self, bot: SlackBot) -> None:
        event = {
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "hey <@U_BOT> what's up",
            "channel": "C_OTHER",
        }
        assert bot._should_respond(event) is True

    def test_bot_channel_returns_true(self, bot: SlackBot) -> None:
        event = {
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "random message",
            "channel": "C_BOT_CHAN",
        }
        assert bot._should_respond(event) is True

    def test_own_message_returns_false(self, bot: SlackBot) -> None:
        event = {"user": "U_BOT", "text": "I said this", "channel_type": "im"}
        assert bot._should_respond(event) is False

    def test_bot_id_message_returns_false(self, bot: SlackBot) -> None:
        event = {
            "bot_id": "B_SOME_BOT",
            "user": "U_OTHER",
            "text": "bot message",
            "channel_type": "im",
        }
        assert bot._should_respond(event) is False

    def test_subtype_returns_false(self, bot: SlackBot) -> None:
        event = {
            "user": "U_HUMAN",
            "text": "hello",
            "subtype": "channel_join",
            "channel_type": "im",
        }
        assert bot._should_respond(event) is False

    def test_random_channel_no_mention_returns_false(self, bot: SlackBot) -> None:
        event = {
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "just chatting",
            "channel": "C_RANDOM",
        }
        assert bot._should_respond(event) is False

    def test_no_bot_user_id_still_checks_channel(self, bot: SlackBot) -> None:
        bot._bot_user_id = ""
        event = {
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "test",
            "channel": "C_BOT_CHAN",
        }
        assert bot._should_respond(event) is True

    def test_empty_event(self, bot: SlackBot) -> None:
        assert bot._should_respond({}) is False


# ---------------------------------------------------------------------------
# _build_thread_context tests
# ---------------------------------------------------------------------------


class TestBuildThreadContext:
    def test_maps_roles_correctly(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_HUMAN", "text": "question?"},
                {"user": "U_BOT", "text": "answer."},
                {"user": "U_HUMAN", "text": "follow-up?"},
            ]
        }
        result = bot._build_thread_context(client, "C1", "ts1", "follow-up?")
        assert result == [
            {"role": "user", "content": "question?"},
            {"role": "assistant", "content": "answer."},
            {"role": "user", "content": "follow-up?"},
        ]

    def test_merges_consecutive_user(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_HUMAN", "text": "line 1"},
                {"user": "U_OTHER", "text": "line 2"},
            ]
        }
        result = bot._build_thread_context(client, "C1", "ts1", "line 2")
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "line 1" in result[0]["content"]
        assert "line 2" in result[0]["content"]

    def test_caps_at_max(self, bot: SlackBot) -> None:
        client = MagicMock()
        msgs = [{"user": f"U_{i}", "text": f"msg {i}"} for i in range(20)]
        # Alternate with bot
        for i in range(0, 20, 2):
            msgs[i]["user"] = "U_HUMAN"
        for i in range(1, 20, 2):
            msgs[i]["user"] = "U_BOT"
        client.conversations_replies.return_value = {"messages": msgs}
        bot.config.max_context_messages = 4
        result = bot._build_thread_context(client, "C1", "ts1", "current")
        # After capping to 4, merging, and ensuring start/end user
        assert len(result) <= 5  # Could be fewer after merge

    def test_api_error_fallback(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.side_effect = Exception("API error")
        result = bot._build_thread_context(client, "C1", "ts1", "hello?")
        assert result == [{"role": "user", "content": "hello?"}]

    def test_empty_thread(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {"messages": []}
        result = bot._build_thread_context(client, "C1", "ts1", "hey")
        assert result == [{"role": "user", "content": "hey"}]

    def test_strips_bot_mention(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_HUMAN", "text": "<@U_BOT> what are my goals?"},
            ]
        }
        result = bot._build_thread_context(client, "C1", "ts1", "what are my goals?")
        assert "<@U_BOT>" not in result[0]["content"]

    def test_ensures_starts_with_user(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_BOT", "text": "I started this thread"},
                {"user": "U_HUMAN", "text": "ok"},
            ]
        }
        result = bot._build_thread_context(client, "C1", "ts1", "ok")
        assert result[0]["role"] == "user"

    def test_ensures_ends_with_user(self, bot: SlackBot) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_HUMAN", "text": "question"},
                {"user": "U_BOT", "text": "answer"},
            ]
        }
        result = bot._build_thread_context(client, "C1", "ts1", "")
        assert result[-1]["role"] == "user"


# ---------------------------------------------------------------------------
# _merge_consecutive_roles tests
# ---------------------------------------------------------------------------


class TestMergeConsecutiveRoles:
    def test_empty(self) -> None:
        assert _merge_consecutive_roles([]) == []

    def test_no_merge_needed(self) -> None:
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        assert _merge_consecutive_roles(msgs) == msgs

    def test_merges_consecutive_user(self) -> None:
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "user", "content": "b"},
            {"role": "assistant", "content": "c"},
        ]
        result = _merge_consecutive_roles(msgs)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "a\nb"}
        assert result[1] == {"role": "assistant", "content": "c"}

    def test_merges_consecutive_assistant(self) -> None:
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "assistant", "content": "c"},
        ]
        result = _merge_consecutive_roles(msgs)
        assert len(result) == 2
        assert result[1] == {"role": "assistant", "content": "b\nc"}

    def test_single_message(self) -> None:
        msgs = [{"role": "user", "content": "alone"}]
        assert _merge_consecutive_roles(msgs) == msgs

    def test_does_not_mutate_input(self) -> None:
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "user", "content": "b"},
        ]
        original = [m.copy() for m in msgs]
        _merge_consecutive_roles(msgs)
        assert msgs == original


# ---------------------------------------------------------------------------
# build_system_prompt tests
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_includes_identity(self, bot: SlackBot) -> None:
        prompt = bot.build_system_prompt()
        assert "I am the agent" in prompt

    def test_includes_goals(self, bot: SlackBot) -> None:
        prompt = bot.build_system_prompt()
        assert "AD biomarkers" in prompt

    def test_includes_reminders(self, bot: SlackBot) -> None:
        prompt = bot.build_system_prompt()
        assert "LONI" in prompt

    def test_includes_stats(self, bot: SlackBot) -> None:
        prompt = bot.build_system_prompt()
        assert "5 notes" in prompt
        assert "3 hypotheses" in prompt

    def test_includes_intro(self, bot: SlackBot) -> None:
        prompt = bot.build_system_prompt()
        assert "research assistant" in prompt

    def test_omits_empty_sections(self, bot: SlackBot) -> None:
        bot._vault_context = VaultContext()
        prompt = bot.build_system_prompt()
        assert "## Identity" not in prompt
        assert "## Current Research Goals" not in prompt
        assert "research assistant" in prompt  # Intro always present


# ---------------------------------------------------------------------------
# load_vault_context tests
# ---------------------------------------------------------------------------


class TestLoadVaultContext:
    def test_reads_files(self, vault: Path) -> None:
        ctx = load_vault_context(vault)
        assert "I am the agent" in ctx.identity
        assert "Iterative" in ctx.methodology
        assert "AD biomarkers" in ctx.goals
        assert "LONI" in ctx.reminders
        assert "5 notes" in ctx.stats
        assert "3 hypotheses" in ctx.stats

    def test_handles_missing_files(self, tmp_path: Path) -> None:
        ctx = load_vault_context(tmp_path)
        assert ctx.identity == ""
        assert ctx.goals == ""
        assert "0 notes" in ctx.stats

    def test_truncates_long_files(self, vault: Path) -> None:
        long_content = "\n".join(f"Line {i}" for i in range(300))
        (vault / "self" / "identity.md").write_text(long_content)
        ctx = load_vault_context(vault)
        lines = ctx.identity.splitlines()
        assert len(lines) == 200


# ---------------------------------------------------------------------------
# refresh_vault_context tests
# ---------------------------------------------------------------------------


class TestRefreshVaultContext:
    def test_updates_context(self, bot: SlackBot, vault: Path) -> None:
        # Modify a vault file
        (vault / "self" / "goals.md").write_text("# Goals\n## New Goal\nUpdated.")
        bot.refresh_vault_context()
        assert "New Goal" in bot._vault_context.goals

    def test_handles_error(self, bot: SlackBot) -> None:
        bot.config = SlackBotConfig(
            vault_path=Path("/nonexistent/vault"),
            slack_bot_token="t",
            slack_app_token="t",
            anthropic_api_key="t",
        )
        # Should not raise
        bot.refresh_vault_context()


# ---------------------------------------------------------------------------
# _call_claude tests
# ---------------------------------------------------------------------------


class TestCallClaude:
    def test_success(self, bot: SlackBot, mock_anthropic: MagicMock) -> None:
        result = bot._call_claude([{"role": "user", "content": "hi"}], "system prompt")
        assert result == "Hello from Claude"
        mock_anthropic.messages.create.assert_called_once()

    def test_passes_config(self, bot: SlackBot, mock_anthropic: MagicMock) -> None:
        bot._call_claude([{"role": "user", "content": "hi"}], "sys")
        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["system"] == "sys"

    def test_api_error_returns_message(
        self, bot: SlackBot, mock_anthropic: MagicMock
    ) -> None:
        mock_anthropic.messages.create.side_effect = RuntimeError("rate limit")
        result = bot._call_claude([{"role": "user", "content": "hi"}], "system")
        assert "could not generate" in result.lower()

    def test_empty_response(self, bot: SlackBot, mock_anthropic: MagicMock) -> None:
        resp = MagicMock()
        resp.content = []
        mock_anthropic.messages.create.return_value = resp
        result = bot._call_claude([{"role": "user", "content": "hi"}], "system")
        assert result == "(empty response)"

    def test_multi_block_response(
        self, bot: SlackBot, mock_anthropic: MagicMock
    ) -> None:
        block1 = MagicMock()
        block1.text = "Part 1"
        block2 = MagicMock()
        block2.text = "Part 2"
        resp = MagicMock()
        resp.content = [block1, block2]
        mock_anthropic.messages.create.return_value = resp
        result = bot._call_claude([{"role": "user", "content": "hi"}], "system")
        assert result == "Part 1\nPart 2"


# ---------------------------------------------------------------------------
# _split_message tests
# ---------------------------------------------------------------------------


class TestSplitMessage:
    def test_short_message(self) -> None:
        assert _split_message("hello", max_len=100) == ["hello"]

    def test_splits_at_newline(self) -> None:
        text = "a" * 50 + "\n" + "b" * 50
        chunks = _split_message(text, max_len=60)
        assert len(chunks) == 2
        assert chunks[0] == "a" * 50
        assert chunks[1] == "b" * 50

    def test_splits_at_space(self) -> None:
        text = "word " * 20  # 100 chars
        chunks = _split_message(text, max_len=50)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_hard_split(self) -> None:
        text = "x" * 200
        chunks = _split_message(text, max_len=50)
        assert len(chunks) == 4
        assert "".join(chunks) == text

    def test_empty_message(self) -> None:
        assert _split_message("") == [""]


# ---------------------------------------------------------------------------
# Event handler integration tests
# ---------------------------------------------------------------------------


class TestHandleMessageIntegration:
    def test_full_flow_mention(
        self, bot: SlackBot, mock_anthropic: MagicMock
    ) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_HUMAN", "text": "<@U_BOT> what are my goals?"},
            ]
        }
        say = MagicMock()

        event = {
            "channel": "C_BOT_CHAN",
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "<@U_BOT> what are my goals?",
            "ts": "123.456",
        }

        bot._handle_mention(event=event, say=say, client=client)

        # Claude was called
        mock_anthropic.messages.create.assert_called_once()
        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert call_kwargs["messages"][0]["role"] == "user"
        assert "goals" in call_kwargs["messages"][0]["content"].lower()

        # System prompt has vault context
        assert "AD biomarkers" in call_kwargs["system"]

        # Response was sent
        say.assert_called_once()
        assert say.call_args.kwargs["thread_ts"] == "123.456"

    def test_dm_flow(self, bot: SlackBot, mock_anthropic: MagicMock) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [{"user": "U_HUMAN", "text": "hello"}]
        }
        say = MagicMock()

        event = {
            "channel": "D_DM",
            "channel_type": "im",
            "user": "U_HUMAN",
            "text": "hello",
            "ts": "789.012",
        }

        bot._handle_message(event=event, say=say, client=client)
        say.assert_called_once()

    def test_skips_non_target(self, bot: SlackBot) -> None:
        say = MagicMock()
        client = MagicMock()

        event = {
            "channel": "C_RANDOM",
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "not for bot",
            "ts": "111.222",
        }

        bot._handle_message(event=event, say=say, client=client)
        say.assert_not_called()

    def test_error_sends_apology(
        self, bot: SlackBot, mock_anthropic: MagicMock
    ) -> None:
        client = MagicMock()
        client.conversations_replies.side_effect = Exception("fail")
        mock_anthropic.messages.create.side_effect = Exception("double fail")
        say = MagicMock()

        event = {
            "channel": "C_BOT_CHAN",
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "test",
            "ts": "333.444",
        }

        # Use _process_event directly (bot_channel, no mention)
        bot._process_event(event=event, say=say, client=client)
        # Should still try to say something (apology or error response)
        assert say.call_count >= 1

    def test_thread_reply(self, bot: SlackBot, mock_anthropic: MagicMock) -> None:
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [
                {"user": "U_HUMAN", "text": "first question"},
                {"user": "U_BOT", "text": "first answer"},
                {"user": "U_HUMAN", "text": "<@U_BOT> follow-up"},
            ]
        }
        say = MagicMock()

        event = {
            "channel": "C_BOT_CHAN",
            "channel_type": "channel",
            "user": "U_HUMAN",
            "text": "<@U_BOT> follow-up",
            "ts": "456.789",
            "thread_ts": "123.000",
        }

        bot._handle_mention(event=event, say=say, client=client)

        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        # Should have the full thread context
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Reply should be in the thread
        assert say.call_args.kwargs["thread_ts"] == "123.000"
