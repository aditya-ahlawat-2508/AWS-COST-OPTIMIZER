# boto 3 required to talk to aws client and get cost and usage data
import boto3
from datetime import datetime, timedelta # to get the current date and time and timedelta is for the retrie suppose i am making an api req  and if my api request fails i want to retry it after 1 second/ 5 seconds/ 10 seconds that we can do using time delta 
##overview of the code:
#1 first one is the cost breakdown function which is used to get the cost breakdown ->cost breakdown is giving you the cost breakdown of the services and the total cost and what is the daily trend of the cost
#2 second one is the monthly forecast function which is used to get the monthly forecast -> how much you will be spending on the aws services in this month (same as forcasted cost present in the aws console)
# these two functionlities are alos provided by aws as well so we can use them to get the cost breakdown and the monthly forecast



# cost breakdown asks for the number of days and returns the cost breakdown for the last 30 days
#we are building cost explorer functionly present in aws console, showing graphs and all the functionalities that are present in the aws console
def get_cost_breakdown(days: int = 30) -> dict:
    ce = boto3.client("ce", region_name="us-east-1")
    # end date is you today date and time delta is the time for which you want to find the cost breakdown for so the start date is the end date - the number of days you want to find the cost breakdown for by default time delta is 30 days if today is 25th july so it will show data for the last 30 days
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    # here we are fetching the cost of each service for a given time period this is the main api call to get the cost breakdown per service
    service_resp = ce.get_cost_and_usage(
        # start date and end date are the time period for which you want to get the cost breakdown  
        # Granularity is the time period for which you want to get the cost breakdown this is monthly because we are getting the cost breakdown per service and we want to get the cost breakdown per service for the last 30 days so we are using monthly granularity
        TimePeriod={"Start": str(start_date), "End": str(end_date)},
        Granularity="MONTHLY",
        # actual cost before the discounts are applied
        Metrics=["UnblendedCost"],
        # groupoing by service is the main thing here we are grouping by service because we want to get the cost breakdown per service
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

# in servuce resp we are talking to our boto client and boto client will give a respoonse which will be stores inn service_resp/ as the data will be uncleaned so we are standardiseing the output 
#
# service_resp = {
#     "ResultsByTime": [                    # ← OUTER list (time periods)
#         {
#             "TimePeriod": {...},
#             "Groups": [                    # ← INNER list (services)
#                 {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "12.34", "Unit": "USD"}}},
#                 {"Keys": ["Amazon S3"],  "Metrics": {"UnblendedCost": {"Amount": "0.00",  "Unit": "USD"}}},
#                 {"Keys": ["Amazon RDS"], "Metrics": {"UnblendedCost": {"Amount": "5.50",  "Unit": "USD"}}},
#             ]
#         }
#     ]
# }
#


    # by_service is a list of dictionaries containing the service name and the cost of the service, empty lust declared 
    by_service = []
    # total_cost is the total cost of the services for the given time period
    total_cost = 0.0
    currency = "USD"
    # service_resp.get("ResultsByTime", []) grabs that outer list of time periods. The , [] is a safety fallback: if the key is missing, use an empty list so the loop just does nothing instead of crashing. Each pass, result becomes one time period. With MONTHLY granularity there's usually only one, so this outer loop typically runs once — but it's written to handle many.
    for result in service_resp.get("ResultsByTime", []):

        for group in result.get("Groups", []):
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            currency = group["Metrics"]["UnblendedCost"]["Unit"]
            # if amount > 0: — only keep going if this service actually cost money. Everything indented below only runs for services with a real cost. This is what silently drops all the $0.00 services (like the S3 entry in my example) so they never clutter your results.
            if amount > 0:
                # only those services will get stored in by_service till 4 decimal places 
                by_service.append({"service": group["Keys"][0], "cost": round(amount, 4)})
                total_cost += amount
    by_service.sort(key=lambda x: x["cost"], reverse=True)

    daily_resp = ce.get_cost_and_usage(
        TimePeriod={"Start": str(start_date), "End": str(end_date)},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
    )
   # What the comprehension is doing, written as a normal loop:
daily_trend = []                                    # start with an empty list
for r in daily_resp.get("ResultsByTime", []):       # walk through each day
    daily_trend.append({                            # build one entry and add it
        "date": r["TimePeriod"]["Start"],
        "cost": round(float(r["Total"]["UnblendedCost"]["Amount"]), 4)
    })
#     # daily_trend = [
#     {"date": "2025-06-25", "cost": 1.2},
#     {"date": "2025-06-26", "cost": 0.95},
#     {"date": "2025-06-27", "cost": 2.1},
#     # ...
# ]
    return {
        "total_cost": round(total_cost, 2),
        "currency": currency,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "by_service": by_service,
        "daily_trend": daily_trend,
    }

    # there is a prolem in monthly forcast ->we are doing future prediction and the problem is due to feburary 

    # suppose today is march 25 
    # This is a separate function with a different goal. The previous one reported what you've already spent; this one asks AWS to predict what you'll spend for the rest of the current month — the same "Forecasted" number you see in the AWS console.

def get_monthly_forecast() -> dict:
    try:
        ce = boto3.client("ce", region_name="us-east-1")
        today = datetime.utcnow().date()
        end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if today >= end_of_month:
            return {"forecast": None, "message": "Month already ended"}
        resp = ce.get_cost_forecast(
            # making an api call from today till the end of the month 

            TimePeriod={"Start": str(today), "End": str(end_of_month)},
            Metric="UNBLENDED_COST",
            Granularity="MONTHLY",
        )
        total = resp["Total"]
        return {"forecast": round(float(total["Amount"]), 2), "currency": total["Unit"]}
    except Exception as e:
        return {"forecast": None, "message": str(e)}

#         '''
#         except Exception as e: — the catch-all safety net. If anything in the try block failed, Python lands here. Exception catches essentially any error, and as e captures the actual error object so you can read what went wrong. It then returns {"forecast": None, "message": str(e)} — None for the forecast (since there isn't one) and str(e) converts the error into a readable text message.
# Why this try/except matters and the earlier function didn't have one: forecasting is genuinely fragile. AWS often can't forecast if your account is new or has too little spending history — it will actively throw an error rather than guess. Without the try/except, that error would crash your entire dashboard. With it, the function fails gracefully: it hands back {"forecast": None, "message": "..."}, and your UI can simply show "Forecast unavailable" instead of the whole page dying. This "return None + an explanation" pattern is a clean way to handle expected failures.
# Tying all three together
# Your get_cost_breakdown function ends by building the daily trend list and returning one big dictionary with the total, currency, dates, per-service breakdown, and daily trend — the full picture of past spending. Then get_monthly_forecast is a smaller, independent function that predicts future spending for the rest of the month, wrapped in try/except because forecasting can legitimately fail. Together they recreate the two headline numbers you see in the AWS Cost Explorer console: "here's what you've spent" and "here's what you're projected to spend."
#         '''

# this is the one of the lambda function which later on i will be setting using terraform 