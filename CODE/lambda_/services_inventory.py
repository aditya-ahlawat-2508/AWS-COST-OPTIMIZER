# this is the lambda function made in order to list all the services on the services page and also that the services can talk to aws to retrieve something 
# This file is the inventory engine — where the last one answered "what am I spending this one answers "what do I actually have running It walks through seven AWS services, collects every resource, and hands back clean lists.
import boto3
import datetime
def get_ec2_instances(region: str = "us-east-1") -> list:
    ec2 = boto3.client("ec2", region_name=region)

    instances = []
    # there was a problem of pricing i was not able to get the prices so i hardcoded them as the pricing api is only avaliable to organisations 
    pricing = {"t2.micro": 8.5, "t3.micro": 7.6, "t3.small": 15.2, "t3.medium": 30.4, "m5.large": 70.0}
#     # {
#     "Reservations": [                    # ← OUTER list
#         {
#             "Instances": [               # ← INNER list
#                 {
#                     "InstanceId": "i-0abc123",
#                     "InstanceType": "t3.micro",
#                     "State": {"Name": "running"},
#                     "Placement": {"AvailabilityZone": "us-east-1a"},
#                     "PublicIpAddress": "54.12.33.9",
#                     "LaunchTime": "2025-07-01 10:30:00+00:00",
#                     "Tags": [{"Key": "Name", "Value": "web-server"}, {"Key": "env", "Value": "prod"}]
#                 }
#             ]
#         }
#     ]
# }

    for reservation in ec2.describe_instances().get("Reservations", []):
        for inst in reservation.get("Instances", []):
            name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])
            # "Give me the value of the Name tag; if there's no Name tag, just use the instance ID as the name." For the example above, it finds "web-server". For an untagged instance, it would return "i-0abc123"
            instances.append({
                "id": inst["InstanceId"], "name": name,
                "type": inst["InstanceType"], "state": inst["State"]["Name"],
                "region": region, "az": inst.get("Placement", {}).get("AvailabilityZone", ""),
                "public_ip": inst.get("PublicIpAddress", "—"),
                "launch_time": str(inst.get("LaunchTime", ""))[:19],
                "estimated_monthly_cost": pricing.get(inst["InstanceType"], 20.0) if inst["State"]["Name"] == "running" else 0.0,
                "service": "EC2",
            })
    return instances


def get_rds_instances(region="us-east-1"):
    rds = boto3.client("rds", region_name=region)
    
    result_list = []                                         # ← HERE is where it's stored
    
    response = rds.describe_db_instances()                   # call AWS
    db_list = response.get("DBInstances", [])                # grab the DBInstances list
    
    for db in db_list:                                       # loop each database
        entry = {                                            # build one entry
            "id": db["DBInstanceIdentifier"],
            "name": db["DBInstanceIdentifier"],
            "type": db["DBInstanceClass"],
            "state": db["DBInstanceStatus"],
            "engine": f"{db['Engine']} {db.get('EngineVersion', '')}",
            "multi_az": db.get("MultiAZ", False),
            "storage_gb": db.get("AllocatedStorage", 0),
            "service": "RDS",
        }
        result_list.append(entry)                            # store it in the list
    
    return result_list     #    hand the list back


# # {
#     "DBInstances": [
#         {
#             "DBInstanceIdentifier": "prod-mysql-db",
#             "DBInstanceClass": "db.t3.micro",
#             "DBInstanceStatus": "available",
#             "Engine": "mysql",
#             "EngineVersion": "8.0.35",
#             "MultiAZ": False,
#             "AllocatedStorage": 20
#         },
#         {
#             "DBInstanceIdentifier": "analytics-postgres",
#             "DBInstanceClass": "db.r5.large",
#             "DBInstanceStatus": "available",
#             "Engine": "postgres",
#             "EngineVersion": "15.3",
#             "MultiAZ": True,
#             "AllocatedStorage": 100
#         }
#     ]
# }

def get_s3_buckets() -> list:
    s3 = boto3.client("s3")
    buckets = []
    for b in s3.list_buckets().get("Buckets", []):
        name = b["Name"]
        # Standard setup: list all buckets, loop through each one. s3.list_buckets() returns a flat Buckets list, so one loop.
        try:
            loc = s3.get_bucket_location(Bucket=name).get("LocationConstraint")
            region = loc if loc else "us-east-1"
        except:
            region = "us-east-1"
            # S3 buckets each live in a specific region, but you have to ask for it. get_bucket_location returns a LocationConstraint. There's a historical AWS quirk: buckets in us-east-1 return None for this field instead of the region name. So region = loc if loc else "us-east-1" means "use the location if it's set, otherwise assume us-east-1." And if the whole call fails (permissions, etc.), the except catches it and defaults to us-east-1. This is failing gracefully — a region lookup problem shouldn't kill the whole inventory.
        try:
            cw = boto3.client("cloudwatch", region_name=region)
            now = datetime.datetime.utcnow()
            start = now - datetime.timedelta(days=2)
            #  S3 doesn't tell you a bucket's size on demand. Instead, AWS records daily size measurements into CloudWatch (its monitoring service).
            size_resp = cw.get_metric_statistics(
                Namespace="AWS/S3", MetricName="BucketSizeBytes",
                Dimensions=[{"Name": "BucketName", "Value": name}, {"Name": "StorageType", "Value": "StandardStorage"}],
                StartTime=start, EndTime=now, Period=86400, Statistics=["Average"]
            )
            size_bytes = size_resp["Datapoints"][0]["Average"] if size_resp["Datapoints"] else 0
            size_gb = round(size_bytes / (1024 ** 3), 2)
            obj_resp = cw.get_metric_statistics(
                Namespace="AWS/S3", MetricName="NumberOfObjects",
                Dimensions=[{"Name": "BucketName", "Value": name}, {"Name": "StorageType", "Value": "AllStorageTypes"}],
                StartTime=start, EndTime=now, Period=86400, Statistics=["Average"]
            )
            obj_count = int(obj_resp["Datapoints"][0]["Average"]) if obj_resp["Datapoints"] else 0
        except Exception:
            size_gb = 0.0
            obj_count = 0
        est_cost = round(size_gb * 0.023, 2)
        # est_cost = round(size_gb * 0.023, 2) estimates monthly cost — S3 standard storage is roughly $0.023 per GB per month, so size × rate. Then it builds the entry. [:10] on the creation date slices the first 10 characters to keep just YYYY-MM-DD. Returns the full list.
        buckets.append({
            "id": name, "name": name,
            "region": region,
            "size_gb": size_gb,
            "object_count": obj_count,
            "estimated_monthly_cost": est_cost,
            "creation_date": str(b.get("CreationDate", ""))[:10],
            "service": "S3",
        })
    return buckets


def get_lambda_functions(region: str = "us-east-1") -> list:
    lam = boto3.client("lambda", region_name=region)
    functions = []
    paginator = lam.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page.get("Functions", []):
            functions.append({
                "id": fn["FunctionName"], "name": fn["FunctionName"],
                "type": f"{fn.get('Runtime', 'Custom')} / {fn['MemorySize']} MB",
                "timeout_sec": fn["Timeout"], 
                "code_size_mb": round(fn.get("CodeSize", 0) / (1024 * 1024), 2),
                "last_modified": str(fn.get("LastModified", ""))[:10],
                "service": "Lambda",
            })
    return functions


def get_ecs_clusters(region: str = "us-east-1") -> list:
    ecs = boto3.client("ecs", region_name=region)
    resp = ecs.list_clusters()
    cluster_arns = resp.get("clusterArns", [])
    if not cluster_arns:
        return []
    details = ecs.describe_clusters(clusters=cluster_arns).get("clusters", [])
    return [{
        "id": c["clusterName"], "name": c["clusterName"],
        "status": c.get("status", "UNKNOWN"),
        "running_tasks": c.get("runningTasksCount", 0),
        "pending_tasks": c.get("pendingTasksCount", 0),
        "active_services": c.get("activeServicesCount", 0),
        "service": "ECS", "region": region
    } for c in details]


def get_elasticache_clusters(region: str = "us-east-1") -> list:
    ec = boto3.client("elasticache", region_name=region)
    return [{
        "id": c["CacheClusterId"],
        "name": c["CacheClusterId"],
        "engine": f"{c['Engine']} {c.get('EngineVersion', '')}",
        "node_type": c["CacheNodeType"],
        "status": c["CacheClusterStatus"],
        "num_nodes": c.get("NumCacheNodes", 1),
        "service": "ElastiCache", "region": region
    } for c in ec.describe_cache_clusters().get("CacheClusters", [])]


def get_nat_gateways(region: str = "us-east-1") -> list:
    ec2 = boto3.client("ec2", region_name=region)
    return [{
        "id": n["NatGatewayId"],
        "name": next((t["Value"] for t in n.get("Tags", []) if t["Key"] == "Name"), n["NatGatewayId"]),
        "vpc_id": n["VpcId"],
        "subnet_id": n["SubnetId"],
        "state": n["State"],
        "service": "NAT Gateway", "region": region
    } for n in ec2.describe_nat_gateways().get("NatGateways", [])]

# This is the conductor that runs all seven fetchers and combines their results. It introduces the dictionary-of-functions 
def get_all_services(region: str = "us-east-1") -> dict:
    results = {"EC2": [], "RDS": [], "S3": [], "Lambda": [], "errors": {}}
    # results is prepared with empty lists and a special "errors" sub-dictionary to record any failures.
    fetchers = {
        "EC2": lambda: get_ec2_instances(region),
        "RDS": lambda: get_rds_instances(region),
        "S3": get_s3_buckets,
        "Lambda": lambda: get_lambda_functions(region),
        "ECS": lambda: get_ecs_clusters(region),
        "ElastiCache": lambda: get_elasticache_clusters(region),
        "NAT Gateway": lambda: get_nat_gateways(region),
    }
    # Then fetchers — this is the clever bit. It's a dictionary where each value is a function (not the function's result, the function itself, ready to be called later). This lets the code loop over all seven services uniformly instead of writing seven separate try/except blocks by hand.
# Why lambda: in front of most of them? A lambda here is a tiny anonymous throwaway function. The issue is that most fetchers need the region argument passed in. You can't write "EC2": get_ec2_instances(region) because that would call the function immediately and store its result, not the function. But you want to store the function and call it later, inside the safe try/except loop. lambda: get_ec2_instances(region) wraps the call so it's "frozen" — a little package that says "when someone calls me, then run get_ec2_instances(region)." Notice "S3": get_s3_buckets has no lambda and no parentheses — that's because get_s3_buckets takes no arguments, so you can store the bare function directly. The lambdas exist purely to carry the region argument along until call time.

    for svc, fn in fetchers.items():
        try:
            results[svc] = fn()
        except Exception as e:
            results["errors"][svc] = str(e)
    return results

    # This is the whole point of the design: each service is fetched in isolation. If your ElastiCache permissions are missing and that call fails, the loop catches it, notes the error, and keeps going — EC2, RDS, S3, and the rest still come back fine. The dashboard degrades gracefully, showing whatever succeeded plus a list of what didn't.