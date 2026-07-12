import boto3
def stop_ec2(instance_id: str, region: str = "us-east-1") -> dict:
    ec2 = boto3.client("ec2", region_name=region)
    resp = ec2.stop_instances(InstanceIds=[instance_id])
    return {"success": True, "instance_id": instance_id,
            "new_state": resp["StoppingInstances"][0]["CurrentState"]["Name"]}
def start_ec2(instance_id: str, region: str = "us-east-1") -> dict:
    ec2 = boto3.client("ec2", region_name=region)
    resp = ec2.start_instances(InstanceIds=[instance_id])
    return {"success": True, "instance_id": instance_id,
            "new_state": resp["StartingInstances"][0]["CurrentState"]["Name"]}
def terminate_ec2(instance_id: str, region: str = "us-east-1") -> dict:
    ec2 = boto3.client("ec2", region_name=region)
    resp = ec2.terminate_instances(InstanceIds=[instance_id])
    return {"success": True, "instance_id": instance_id,
            "new_state": resp["TerminatingInstances"][0]["CurrentState"]["Name"]}
def stop_rds(db_identifier: str, region: str = "us-east-1") -> dict:
    rds = boto3.client("rds", region_name=region)
    rds.stop_db_instance(DBInstanceIdentifier=db_identifier)
    return {"success": True, "db_identifier": db_identifier, "action": "stopping"}
def start_rds(db_identifier: str, region: str = "us-east-1") -> dict:
    rds = boto3.client("rds", region_name=region)
    rds.start_db_instance(DBInstanceIdentifier=db_identifier)
    return {"success": True, "db_identifier": db_identifier, "action": "starting"}
def delete_lambda(function_name: str, region: str = "us-east-1") -> dict:
    lam = boto3.client("lambda", region_name=region)
    lam.delete_function(FunctionName=function_name)
    return {"success": True, "function": function_name, "action": "deleted"}
def empty_and_delete_s3_bucket(bucket_name: str) -> dict:
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    try:
        bucket.objects.all().delete()
        bucket.object_versions.all().delete()
        bucket.delete()
        return {"success": True, "bucket": bucket_name, "action": "deleted"}
    except Exception as e:
        return {"success": False, "bucket": bucket_name, "error": str(e)}
def delete_elasticache(cluster_id: str, region: str = "us-east-1") -> dict:
    ec = boto3.client("elasticache", region_name=region)
    ec.delete_cache_cluster(CacheClusterId=cluster_id)
    return {"success": True, "cluster_id": cluster_id, "action": "deleting"}
def delete_nat_gateway(nat_id: str, region: str = "us-east-1") -> dict:
    ec2 = boto3.client("ec2", region_name=region)
    ec2.delete_nat_gateway(NatGatewayId=nat_id)
    return {"success": True, "nat_gateway_id": nat_id, "action": "deleting"}