import boto3
# Because these are write operations, there's a mindset shift worth naming before we start: reading is safe and repeatable; these actions have real consequences. terminate_ec2 destroys a server permanently. empty_and_delete_s3_bucket erases files forever. The functions themselves don't ask "are you sure?" — that safety gating is the app's job (buttons, confirmations). These are just the raw levers.
def stop_ec2(instance_id: str, region: str = "us-east-1") -> dict:
    ec2 = boto3.client("ec2", region_name=region)
    resp = ec2.stop_instances(InstanceIds=[instance_id])
#     # resp = {
#     "StoppingInstances": [
#         {
#             "InstanceId": "i-0abc123",
#             "CurrentState": {"Code": 64, "Name": "stopping"},
#             "PreviousState": {"Code": 16, "Name": "running"}
#         }
#     ]
# }
    return {"success": True, "instance_id": instance_id,
            "new_state": resp["StoppingInstances"][0]["CurrentState"]["Name"]}
            # Stopping an EC2 instance turns off the virtual machine. Compute charges pause, but EBS storage costs remain. Starting it resumes operation on potentially new hardware. Terminating permanently deletes the instance and its root volume; you cannot restart it.
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
    # This is the most interesting function in the file — it introduces two new concepts at once: the boto3.resource interface, and S3's multi-step deletion rule. It's also the only function with a try/except, and there's a good reason for all three.
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    try:
        bucket.objects.all().delete()
        bucket.object_versions.all().delete()
        bucket.delete()
        return {"success": True, "bucket": bucket_name, "action": "deleted"}
    except Exception as e:
        return {"success": False, "bucket": bucket_name, "error": str(e)}

        # New concept 1 — boto3.resource instead of boto3.client. Every other function in all three files used boto3.client(...). This one uses boto3.resource(...). Both talk to AWS, but they're two different styles:

# boto3.client("s3") is the low-level interface — you call methods and get back raw dictionaries (JSON-like), exactly what you've seen everywhere else.
# boto3.resource("s3") is the high-level, object-oriented interface — it gives you objects you can navigate with dots. Instead of raw dicts, you get a Bucket object that has an .objects collection, an .object_versions collection, and a .delete() method.

# Line 2, bucket = s3.Bucket(bucket_name), creates a Python object representing your bucket — think of it as a handle you can now command directly. This resource style makes bulk operations like "delete everything in here" much cleaner than the client style would. That convenience is exactly why this one function breaks the pattern and uses resource.
# New concept 2 — why deletion takes three steps. AWS has a strict rule: you cannot delete a bucket that still contains anything. The bucket must be completely empty first. And "empty" is trickier than it sounds when versioning is involved. So the three lines, in order:

# bucket.objects.all().delete() — delete all the current files in the bucket. .objects.all() grabs every object, .delete() removes them in bulk.
# bucket.object_versions.all().delete() — delete all old versions of files. If the bucket had versioning enabled (remember that S3 versioning topic?), deleting the current files isn't enough — every historical version is still stored and still counts as content. This line clears those out too. Skip this on a versioned bucket and step 3 would fail because the bucket isn't truly empty.
# bucket.delete() — now that the bucket is genuinely empty (no current files, no old versions), AWS finally allows the bucket itself to be deleted.

# The order is mandatory: contents first, then the container. You can't remove the box while things are still in it.
# New concept 3 — why the try/except here specifically. This is the only function wrapped in a safety net, and it's the one that most needs it. It's multi-step, so it can fail partway through — maybe the objects delete fine but you lack permission to delete versions, or the bucket is huge and something times out mid-operation. The other functions are single atomic calls (one action, succeeds or raises immediately). This one has three sequential actions where step 2 could break after step 1 succeeded. The try/except catches any such failure and returns a clean {"success": False, ..., "error": "..."} instead of crashing the whole dashboard — and crucially, the str(e) tells you which step failed so you can debug.
# Tracing both paths:

# Success: empty_and_delete_s3_bucket("old-logs-bucket") → {"success": True, "bucket": "old-logs-bucket", "action": "deleted"}
# Failure (say permission denied on versions): → {"success": False, "bucket": "old-logs-bucket", "error": "AccessDenied: ..."}

# Notice the return dictionaries have different shapes depending on outcome — success has an "action" key, failure has an "error" key. The app checks success to decide which to read. This is a clean way to report "it worked" vs "here's what went wrong."

def delete_elasticache(cluster_id: str, region: str = "us-east-1") -> dict:
    ec = boto3.client("elasticache", region_name=region)
    ec.delete_cache_cluster(CacheClusterId=cluster_id)
    return {"success": True, "cluster_id": cluster_id, "action": "deleting"}

def delete_nat_gateway(nat_id: str, region: str = "us-east-1") -> dict:
    ec2 = boto3.client("ec2", region_name=region)
    ec2.delete_nat_gateway(NatGatewayId=nat_id)
    return {"success": True, "nat_gateway_id": nat_id, "action": "deleting"}

    