import json
from unittest.mock import MagicMock, patch

import handler


def test_null_body_returns_400_instead_of_crashing():
    # Regression test: json.loads(event.get("body", "{}")) raised TypeError
    # when "body" was present but None (e.g. console test invocations).
    event = {"body": None}

    response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 400


@patch("boto3.client")
def test_ping_action_with_valid_body(mock_boto_client):
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test",
    }
    mock_boto_client.return_value = mock_sts

    event = {"body": json.dumps({"action": "ping"})}
    response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["account_id"] == "123456789012"


def test_unknown_action_returns_400():
    event = {"body": json.dumps({"action": "does_not_exist"})}
    response = handler.lambda_handler(event, None)
    assert response["statusCode"] == 400
