import json
import logging
import requests
from typing import Dict, Any, List
from config import settings
logger = logging.getLogger(__name__)
class AWSClient:
    def __init__(self, region: str = None):
        self.region = region or settings.AWS_REGION
        self.api_url = settings.API_GATEWAY_URL
        if not self.api_url:
            logger.warning("API_GATEWAY_URL is not set. API calls will fail.")
    def _call_api(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.api_url:
            return {"error": "API Gateway URL is not configured in .env or settings."}
        payload = {
            "action": action,
            "region": self.region
        }
        if params:
            payload.update(params)
        try:
            logger.info(f"Calling API Gateway: {action}")
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30  
            )
            response.raise_for_status()
            data = response.json()
            if "body" in data:
                try:
                    data = json.loads(data["body"])
                except json.JSONDecodeError:
                    pass
            if "error" in data:
                logger.error(f"API Error ({action}): {data['error']}")
                return {"error": data["error"]}
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Request failed: {str(e)}")
            return {"error": f"Connection failed: {str(e)}"}
        except json.JSONDecodeError:
            logger.error(f"API returned invalid JSON: {response.text}")
            return {"error": "Invalid response format from API"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": str(e)}
    def get_caller_identity(self) -> Dict[str, Any]:
        res = self._call_api("ping")
        if "error" in res:
            return {"connected": False, "status": "error", "error": res["error"]}
        return {
            "connected": True,
            "status": "success", 
            "account_id": res.get("account_id", "Lambda execution role"),
            "arn": res.get("arn", "arn:aws:iam::...")
        }
    def get_cost_breakdown(self, days: int = 30) -> Dict[str, Any]:
        return self._call_api("get_cost_summary", {"days": days})
    def get_monthly_cost_forecast(self, days_ahead: int = 30) -> Dict[str, Any]:
        return self._call_api("get_cost_forecast", {"days_ahead": days_ahead})
    def list_ec2_instances(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_ec2")
        return res.get("instances", []) if "error" not in res else [{"error": res["error"]}]
    def list_rds_instances(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_rds")
        return res.get("instances", []) if "error" not in res else [{"error": res["error"]}]
    def list_s3_buckets(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_s3")
        return res.get("buckets", []) if "error" not in res else [{"error": res["error"]}]
    def list_lambda_functions(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_lambda")
        return res.get("functions", []) if "error" not in res else [{"error": res["error"]}]
    def list_ecs_clusters(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_ecs")
        return res.get("clusters", []) if "error" not in res else [{"error": res["error"]}]
    def list_elasticache_clusters(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_elasticache")
        return res.get("clusters", []) if "error" not in res else [{"error": res["error"]}]
    def list_nat_gateways(self) -> List[Dict[str, Any]]:
        res = self._call_api("list_nat_gateways")
        return res.get("nat_gateways", []) if "error" not in res else [{"error": res["error"]}]
    def get_all_services(self, region: str = None) -> Dict[str, Any]:
        reg = region or self.region
        res = self._call_api("get_all_services", {"region": reg})
        return res if "error" not in res else {"errors": {"API": res["error"]}}
    def stop_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return self._call_api("stop_ec2", {"instance_ids": [instance_id]})
    def start_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return self._call_api("start_ec2", {"instance_ids": [instance_id]})
    def terminate_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return self._call_api("terminate_ec2", {"instance_ids": [instance_id]})
    def stop_rds_instance(self, db_identifier: str) -> Dict[str, Any]:
        return self._call_api("stop_rds", {"db_identifiers": [db_identifier]})
    def start_rds_instance(self, db_identifier: str) -> Dict[str, Any]:
        return self._call_api("start_rds", {"db_identifiers": [db_identifier]})
    def empty_and_delete_s3_bucket(self, bucket_name: str) -> Dict[str, Any]:
        return self._call_api("delete_s3", {"bucket_name": bucket_name})
    def delete_lambda_function(self, function_name: str) -> Dict[str, Any]:
        return self._call_api("delete_lambda", {"function_names": [function_name]})
    def delete_elasticache_cluster(self, cluster_id: str) -> Dict[str, Any]:
        return self._call_api("delete_elasticache", {"cluster_ids": [cluster_id]})
    def delete_nat_gateway(self, nat_gateway_id: str) -> Dict[str, Any]:
        return self._call_api("delete_nat_gateway", {"nat_gateway_ids": [nat_gateway_id]})
def get_aws_client(region: str = None) -> AWSClient:
    return AWSClient(region=region)