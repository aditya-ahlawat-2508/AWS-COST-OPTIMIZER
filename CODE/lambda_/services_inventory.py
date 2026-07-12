import boto3
import datetime
def get_ec2_instances(region: str = "us-east-1") -> list:
    ec2 = boto3.client("ec2", region_name=region)
    instances = []
    pricing = {"t2.micro": 8.5, "t3.micro": 7.6, "t3.small": 15.2, "t3.medium": 30.4, "m5.large": 70.0}
    for reservation in ec2.describe_instances().get("Reservations", []):
        for inst in reservation.get("Instances", []):
            name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])
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
def get_rds_instances(region: str = "us-east-1") -> list:
    rds = boto3.client("rds", region_name=region)
    return [{
        "id": db["DBInstanceIdentifier"], "name": db["DBInstanceIdentifier"],
        "type": db["DBInstanceClass"], "state": db["DBInstanceStatus"],
        "engine": f"{db['Engine']} {db.get('EngineVersion', '')}",
        "multi_az": db.get("MultiAZ", False), "storage_gb": db.get("AllocatedStorage", 0),
        "service": "RDS",
    } for db in rds.describe_db_instances().get("DBInstances", [])]
def get_s3_buckets() -> list:
    s3 = boto3.client("s3")
    buckets = []
    for b in s3.list_buckets().get("Buckets", []):
        name = b["Name"]
        try:
            loc = s3.get_bucket_location(Bucket=name).get("LocationConstraint")
            region = loc if loc else "us-east-1"
        except:
            region = "us-east-1"
        try:
            cw = boto3.client("cloudwatch", region_name=region)
            now = datetime.datetime.utcnow()
            start = now - datetime.timedelta(days=2)
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
def get_all_services(region: str = "us-east-1") -> dict:
    results = {"EC2": [], "RDS": [], "S3": [], "Lambda": [], "errors": {}}
    fetchers = {
        "EC2": lambda: get_ec2_instances(region),
        "RDS": lambda: get_rds_instances(region),
        "S3": get_s3_buckets,
        "Lambda": lambda: get_lambda_functions(region),
        "ECS": lambda: get_ecs_clusters(region),
        "ElastiCache": lambda: get_elasticache_clusters(region),
        "NAT Gateway": lambda: get_nat_gateways(region),
    }
    for svc, fn in fetchers.items():
        try:
            results[svc] = fn()
        except Exception as e:
            results["errors"][svc] = str(e)
    return results