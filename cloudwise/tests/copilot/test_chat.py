from types import SimpleNamespace
from unittest.mock import MagicMock

from app.database import org_scoped_session
from app.models import AWSAccount, Finding, Organization
from services.copilot.agent import chat


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name, tool_input, block_id="tool_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def _seed_org_with_finding():
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Acme")
        session.add(org)
        session.flush()
        org_id = org.id

    with org_scoped_session(org_id=str(org_id)) as session:
        account = AWSAccount(
            org_id=org_id,
            aws_account_id="111111111111",
            role_arn="arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            external_id="ext-1",
        )
        session.add(account)
        session.flush()
        finding = Finding(
            org_id=org_id,
            account_id=account.id,
            rule_id="idle_ec2",
            resource_id="i-0123456789abcdef0",
            resource_type="ec2_instance",
            evidence={"fix": "Stop it."},
            monthly_savings=42.0,
            effort="low",
            risk="medium",
        )
        session.add(finding)
        session.flush()

    return org_id


def test_chat_answers_directly_when_no_tool_needed():
    org_id = _seed_org_with_finding()
    fake_client = MagicMock()
    fake_client.messages.create.return_value = SimpleNamespace(
        stop_reason="end_turn",
        content=[_text_block("Hi! Ask me about your AWS spend.")],
    )

    with org_scoped_session(org_id=str(org_id)) as session:
        result = chat(fake_client, session, org_id, org_id, "hello")

    assert result.text == "Hi! Ask me about your AWS spend."
    assert result.tool_calls == []
    assert result.grounding_warnings == []
    assert fake_client.messages.create.call_count == 1


def test_chat_executes_tool_and_grounds_final_answer():
    org_id = _seed_org_with_finding()
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        SimpleNamespace(
            stop_reason="tool_use",
            content=[_tool_use_block("list_findings", {"status": "open"})],
        ),
        SimpleNamespace(
            stop_reason="end_turn",
            content=[_text_block("Stopping i-0123456789abcdef0 saves $42.00/month, low effort.")],
        ),
    ]

    with org_scoped_session(org_id=str(org_id)) as session:
        result = chat(fake_client, session, org_id, org_id, "what should I fix?")

    assert "42.00" in result.text
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "list_findings"
    assert result.grounding_warnings == []


def test_chat_flags_fabricated_numbers_but_still_returns_answer():
    org_id = _seed_org_with_finding()
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        SimpleNamespace(
            stop_reason="tool_use",
            content=[_tool_use_block("list_findings", {})],
        ),
        SimpleNamespace(
            stop_reason="end_turn",
            content=[_text_block("You could save up to $9,999.00/month across your fleet.")],
        ),
    ]

    with org_scoped_session(org_id=str(org_id)) as session:
        result = chat(fake_client, session, org_id, org_id, "how much could I save overall?")

    assert result.grounding_warnings != []
    assert "9,999" in result.grounding_warnings[0]


def test_chat_gives_up_gracefully_after_max_tool_rounds():
    org_id = _seed_org_with_finding()
    fake_client = MagicMock()
    fake_client.messages.create.return_value = SimpleNamespace(
        stop_reason="tool_use",
        content=[_tool_use_block("list_findings", {})],
    )

    with org_scoped_session(org_id=str(org_id)) as session:
        result = chat(fake_client, session, org_id, org_id, "loop forever")

    assert "narrowing" in result.text.lower()


def test_org_id_is_never_taken_from_the_model():
    # propose_change's tool schema has no org_id field at all — this test
    # documents/locks that invariant rather than exercising new behavior.
    from services.copilot.agent import TOOL_DEFINITIONS

    propose_change_tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "propose_change")
    assert "org_id" not in propose_change_tool["input_schema"]["properties"]
