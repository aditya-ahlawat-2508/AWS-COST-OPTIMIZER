"""Cross-account access, the way the blueprint requires: assume the
customer's CloudWiseReadOnly role (infra/onboarding/readonly-role.yaml) with
its per-tenant ExternalId, hold the resulting credentials only in memory for
a short session, and never store or log them.
"""
import boto3

SESSION_DURATION_SECONDS = 900  # 15 minutes — short-lived by design
SESSION_NAME = "cloudwise-scan"


def assume_scan_role(role_arn: str, external_id: str, region: str, sts_client=None) -> boto3.Session:
    sts = sts_client or boto3.client("sts")
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=SESSION_NAME,
        ExternalId=external_id,
        DurationSeconds=SESSION_DURATION_SECONDS,
    )
    creds = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )
