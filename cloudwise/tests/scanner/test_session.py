from unittest.mock import MagicMock

from services.scanner.session import SESSION_DURATION_SECONDS, assume_scan_role


def test_assume_scan_role_uses_external_id_and_short_duration():
    fake_sts = MagicMock()
    fake_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIAFAKE",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }
    }

    session = assume_scan_role(
        role_arn="arn:aws:iam::111111111111:role/CloudWiseReadOnly",
        external_id="tenant-abc-123",
        region="us-east-1",
        sts_client=fake_sts,
    )

    fake_sts.assume_role.assert_called_once_with(
        RoleArn="arn:aws:iam::111111111111:role/CloudWiseReadOnly",
        RoleSessionName="cloudwise-scan",
        ExternalId="tenant-abc-123",
        DurationSeconds=SESSION_DURATION_SECONDS,
    )

    creds = session.get_credentials().get_frozen_credentials()
    assert creds.access_key == "AKIAFAKE"
    assert creds.secret_key == "secret"
    assert creds.token == "token"
    assert session.region_name == "us-east-1"
