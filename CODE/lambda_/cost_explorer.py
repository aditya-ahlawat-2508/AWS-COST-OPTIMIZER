import boto3
from datetime import datetime, timedelta
def get_cost_breakdown(days: int = 30) -> dict:
    ce = boto3.client("ce", region_name="us-east-1")
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    service_resp = ce.get_cost_and_usage(
        TimePeriod={"Start": str(start_date), "End": str(end_date)},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )
    by_service = []
    total_cost = 0.0
    currency = "USD"
    for result in service_resp.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            currency = group["Metrics"]["UnblendedCost"]["Unit"]
            if amount > 0:
                by_service.append({"service": group["Keys"][0], "cost": round(amount, 4)})
                total_cost += amount
    by_service.sort(key=lambda x: x["cost"], reverse=True)
    daily_resp = ce.get_cost_and_usage(
        TimePeriod={"Start": str(start_date), "End": str(end_date)},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
    )
    daily_trend = [
        {"date": r["TimePeriod"]["Start"], "cost": round(float(r["Total"]["UnblendedCost"]["Amount"]), 4)}
        for r in daily_resp.get("ResultsByTime", [])
    ]
    return {
        "total_cost": round(total_cost, 2),
        "currency": currency,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "by_service": by_service,
        "daily_trend": daily_trend,
    }
def get_monthly_forecast() -> dict:
    try:
        ce = boto3.client("ce", region_name="us-east-1")
        today = datetime.utcnow().date()
        end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if today >= end_of_month:
            return {"forecast": None, "message": "Month already ended"}
        resp = ce.get_cost_forecast(
            TimePeriod={"Start": str(today), "End": str(end_of_month)},
            Metric="UNBLENDED_COST",
            Granularity="MONTHLY",
        )
        total = resp["Total"]
        return {"forecast": round(float(total["Amount"]), 2), "currency": total["Unit"]}
    except Exception as e:
        return {"forecast": None, "message": str(e)}