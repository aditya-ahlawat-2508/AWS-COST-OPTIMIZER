import json
import os
import logging
import cost_explorer, services_inventory, service_actions
logger = logging.getLogger()
logger.setLevel(logging.INFO)
DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    action = event.get("action")
    region = event.get("region", DEFAULT_REGION)
    params = event.get("params", {})
    try:
        body = json.loads(event.get("body", "{}"))
        if not body and "action" in event:
            body = event
        action = body.get("action")
        region = body.get("region", DEFAULT_REGION)
        logger.info(f"Parsed action: {action}, region: {region}")
        if action == "ping":
            import boto3
            sts = boto3.client("sts")
            identity = sts.get_caller_identity()
            result = {
                "account_id": identity.get("Account"),
                "arn": identity.get("Arn")
            }
        elif action == "get_cost_summary":
            days = body.get("days", 30)
            result = cost_explorer.get_cost_breakdown(days=days)
        elif action == "get_cost_forecast":
            days_ahead = body.get("days_ahead", 30)
            result = cost_explorer.get_monthly_forecast()
        elif action == "get_all_services":
            result = services_inventory.get_all_services(region=region)
        elif action == "list_ec2":
            result = {"instances": services_inventory.get_ec2_instances(region=region)}
        elif action == "list_rds":
            result = {"instances": services_inventory.get_rds_instances(region=region)}
        elif action == "list_s3":
            result = {"buckets": services_inventory.get_s3_buckets()}
        elif action == "list_lambda":
            result = {"functions": services_inventory.get_lambda_functions(region=region)}
        elif action == "list_ecs":
            result = {"clusters": []}
            if hasattr(services_inventory, 'get_ecs_clusters'):
                result["clusters"] = services_inventory.get_ecs_clusters(region=region)
        elif action == "list_elasticache":
            result = {"clusters": []}
            if hasattr(services_inventory, 'get_elasticache_clusters'):
                result["clusters"] = services_inventory.get_elasticache_clusters(region=region)
        elif action == "list_nat_gateways":
            result = {"nat_gateways": []}
            if hasattr(services_inventory, 'get_nat_gateways'):
                result["nat_gateways"] = services_inventory.get_nat_gateways(region=region)
        elif action == "stop_ec2":
            instance_ids = body.get("instance_ids", [])
            results = []
            for iid in instance_ids:
                results.append(service_actions.stop_ec2(iid, region=region))
            result = {"results": results}
        elif action == "start_ec2":
            instance_ids = body.get("instance_ids", [])
            results = []
            for iid in instance_ids:
                results.append(service_actions.start_ec2(iid, region=region))
            result = {"results": results}
        elif action == "terminate_ec2":
            instance_ids = body.get("instance_ids", [])
            results = []
            for iid in instance_ids:
                results.append(service_actions.terminate_ec2(iid, region=region))
            result = {"results": results}
        elif action == "stop_rds":
            db_ids = body.get("db_identifiers", [])
            results = []
            for did in db_ids:
                results.append(service_actions.stop_rds(did, region=region))
            result = {"results": results}
        elif action == "start_rds":
            db_ids = body.get("db_identifiers", [])
            results = []
            for did in db_ids:
                results.append(service_actions.start_rds(did, region=region))
            result = {"results": results}
        elif action == "delete_s3":
            bucket = body.get("bucket_name")
            if hasattr(service_actions, 'empty_and_delete_s3_bucket'):
                result = service_actions.empty_and_delete_s3_bucket(bucket)
            else:
                result = {"error": "Not implemented in backend"}
        elif action == "delete_lambda":
            fn_names = body.get("function_names", [])
            results = []
            for fn in fn_names:
                results.append(service_actions.delete_lambda(fn, region=region))
            result = {"results": results}
        elif action == "delete_elasticache":
            cluster_ids = body.get("cluster_ids", [])
            results = []
            for cid in cluster_ids:
                if hasattr(service_actions, 'delete_elasticache'):
                    results.append(service_actions.delete_elasticache(cid, region=region))
                else:
                    results.append({"error": "Not implemented in backend"})
            result = {"results": results}
        elif action == "delete_nat_gateway":
            nat_ids = body.get("nat_gateway_ids", [])
            results = []
            for nid in nat_ids:
                if hasattr(service_actions, 'delete_nat_gateway'):
                    results.append(service_actions.delete_nat_gateway(nid, region=region))
                else:
                    results.append({"error": "Not implemented in backend"})
            result = {"results": results}
        else:
            return _response(400, {"error": f"Unknown action: '{action}'"})
        return _response(200, result)
    except Exception as e:
        logger.error(f"Error handling action: {e}", exc_info=True)
        return _response(500, {"error": str(e)})
def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }