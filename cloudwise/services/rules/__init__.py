from typing import Any, Dict, List

from . import gp2_to_gp3, idle_ec2, idle_nat_gateway, non_prod_schedule, stopped_rds, unattached_ebs, unused_eip
from .base import Finding

# Each rule reads one key out of the scan context and returns Findings for it.
# Keys not present in the context are treated as "nothing scanned yet" (empty
# list), so partial scans degrade gracefully instead of raising.
RULES = {
    idle_ec2.RULE_ID: ("ec2_instances", idle_ec2.detect),
    unattached_ebs.RULE_ID: ("ebs_volumes", unattached_ebs.detect),
    gp2_to_gp3.RULE_ID: ("ebs_volumes", gp2_to_gp3.detect),
    unused_eip.RULE_ID: ("elastic_ips", unused_eip.detect),
    idle_nat_gateway.RULE_ID: ("nat_gateways", idle_nat_gateway.detect),
    stopped_rds.RULE_ID: ("rds_instances", stopped_rds.detect),
    non_prod_schedule.RULE_ID: ("ec2_instances", non_prod_schedule.detect),
}


def run_all(context: Dict[str, List[Dict[str, Any]]]) -> List[Finding]:
    """context maps resource-list names (ec2_instances, ebs_volumes,
    elastic_ips, nat_gateways, rds_instances) to lists of plain dicts, as
    produced by services/scanner collectors merged with services/pricing.
    """
    findings: List[Finding] = []
    for _rule_id, (context_key, detect_fn) in RULES.items():
        findings.extend(detect_fn(context.get(context_key, [])))
    return findings
