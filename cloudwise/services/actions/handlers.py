"""One handler per action_type in infra/onboarding/actions-role.yaml — the
same four, no more: stop_ec2, modify_volume_gp3, release_eip, stop_rds.
None of these delete anything, so there's no snapshot-before-delete case
here (the blueprint's rule still applies; it just doesn't come up for this
action set — a future 'delete unattached EBS' action would need one).

Every handler re-checks the resource's actual current state before acting
and raises PreCheckFailed if it's drifted from what the finding assumed —
this is the "re-check the resource still matches the finding right before
executing" rule from the blueprint, and it's the safety net every one of
these four actions gets, dry-run or not.
"""
from botocore.exceptions import ClientError


class PreCheckFailed(Exception):
    """The resource's live state no longer matches what the finding assumed
    (someone already fixed it, it terminated on its own, etc). The caller
    must not proceed with the action.
    """


def stop_ec2(ec2_client, instance_id: str) -> dict:
    described = ec2_client.describe_instances(InstanceIds=[instance_id])
    state = described["Reservations"][0]["Instances"][0]["State"]["Name"]
    if state != "running":
        raise PreCheckFailed(f"Expected instance {instance_id} to be running, found '{state}'")

    # EC2's StopInstances supports a real server-side DryRun — the one
    # action in this set where that's true, so it's the one place we use it
    # in addition to the pre-check above.
    try:
        ec2_client.stop_instances(InstanceIds=[instance_id], DryRun=True)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "DryRunOperation":
            raise PreCheckFailed(f"Dry-run rejected for {instance_id}: {exc}")

    response = ec2_client.stop_instances(InstanceIds=[instance_id])
    new_state = response["StoppingInstances"][0]["CurrentState"]["Name"]
    return {"pre_check_state": state, "new_state": new_state}


def modify_volume_gp3(ec2_client, volume_id: str) -> dict:
    described = ec2_client.describe_volumes(VolumeIds=[volume_id])
    volume_type = described["Volumes"][0]["VolumeType"]
    if volume_type != "gp2":
        raise PreCheckFailed(f"Expected volume {volume_id} to be gp2, found '{volume_type}'")

    response = ec2_client.modify_volume(VolumeId=volume_id, VolumeType="gp3")
    modification_state = response["VolumeModification"]["ModificationState"]
    return {"pre_check_state": volume_type, "modification_state": modification_state}


def release_eip(ec2_client, allocation_id: str) -> dict:
    described = ec2_client.describe_addresses(AllocationIds=[allocation_id])
    address = described["Addresses"][0]
    if address.get("AssociationId"):
        raise PreCheckFailed(
            f"Elastic IP {allocation_id} is now associated ({address['AssociationId']}); refusing to release"
        )

    ec2_client.release_address(AllocationId=allocation_id)
    return {"pre_check_state": "unassociated", "released": True}


def stop_rds(rds_client, db_instance_id: str) -> dict:
    described = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
    db_status = described["DBInstances"][0]["DBInstanceStatus"]
    if db_status != "available":
        raise PreCheckFailed(f"Expected RDS instance {db_instance_id} to be available, found '{db_status}'")

    rds_client.stop_db_instance(DBInstanceIdentifier=db_instance_id)
    return {"pre_check_state": db_status, "action": "stopping"}
