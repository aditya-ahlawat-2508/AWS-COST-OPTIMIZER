import boto3
import pytest
from moto import mock_aws

from services.actions.handlers import PreCheckFailed, modify_volume_gp3, release_eip, stop_ec2, stop_rds


@mock_aws
def test_stop_ec2_succeeds_for_running_instance():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]

    result = stop_ec2(ec2, instance_id)

    assert result["pre_check_state"] == "running"
    assert result["new_state"] in ("stopping", "stopped")
    described = ec2.describe_instances(InstanceIds=[instance_id])
    assert described["Reservations"][0]["Instances"][0]["State"]["Name"] in ("stopping", "stopped")


@mock_aws
def test_stop_ec2_refuses_already_stopped_instance():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    ec2.stop_instances(InstanceIds=[instance_id])

    with pytest.raises(PreCheckFailed):
        stop_ec2(ec2, instance_id)


@mock_aws
def test_modify_volume_gp3_succeeds_for_gp2_volume():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume_id = ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp2")["VolumeId"]

    result = modify_volume_gp3(ec2, volume_id)

    assert result["pre_check_state"] == "gp2"
    described = ec2.describe_volumes(VolumeIds=[volume_id])
    assert described["Volumes"][0]["VolumeType"] == "gp3"


@mock_aws
def test_modify_volume_gp3_refuses_non_gp2_volume():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume_id = ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3")["VolumeId"]

    with pytest.raises(PreCheckFailed):
        modify_volume_gp3(ec2, volume_id)


@mock_aws
def test_release_eip_succeeds_for_unassociated_address():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    allocation_id = ec2.allocate_address(Domain="vpc")["AllocationId"]

    result = release_eip(ec2, allocation_id)

    assert result["released"] is True
    described = ec2.describe_addresses()
    assert allocation_id not in [a["AllocationId"] for a in described["Addresses"]]


@mock_aws
def test_release_eip_refuses_associated_address():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    allocation = ec2.allocate_address(Domain="vpc")
    ec2.associate_address(InstanceId=instance_id, AllocationId=allocation["AllocationId"])

    with pytest.raises(PreCheckFailed):
        release_eip(ec2, allocation["AllocationId"])


@mock_aws
def test_stop_rds_succeeds_for_available_instance():
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=20,
    )

    result = stop_rds(rds, "test-db")

    assert result["pre_check_state"] == "available"


@mock_aws
def test_stop_rds_refuses_already_stopped_instance():
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_instance(
        DBInstanceIdentifier="test-db-2",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=20,
    )
    rds.stop_db_instance(DBInstanceIdentifier="test-db-2")

    with pytest.raises(PreCheckFailed):
        stop_rds(rds, "test-db-2")
