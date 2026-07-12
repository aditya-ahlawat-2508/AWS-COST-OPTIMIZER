def format_cost(amount: float, currency: str = "USD") -> str:
    if amount >= 1000:
        return f"${amount:,.2f} {currency}"
    elif amount >= 1:
        return f"${amount:.2f} {currency}"
    else:
        return f"${amount:.4f} {currency}"
def cost_delta_color(delta_pct: float) -> str:
    if delta_pct > 10:
        return "red"
    elif delta_pct > 0:
        return "orange"
    elif delta_pct < 0:
        return "green"
    return "gray"
def state_badge(state: str) -> str:
    state_map = {
        "running": "🟢 running",
        "stopped": "🔴 stopped",
        "stopping": "🟡 stopping",
        "starting": "🟡 starting",
        "pending": "🟡 pending",
        "terminated": "⚫ terminated",
        "available": "🟢 available",
        "active": "🟢 active",
        "deleting": "🔴 deleting",
        "creating": "🟡 creating",
        "modifying": "🟡 modifying",
    }
    return state_map.get(state.lower(), f"⚪ {state}")
def bytes_to_human(num_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} PB"
def get_top_cost_services(by_service: list, top_n: int = 5) -> list:
    sorted_services = sorted(by_service, key=lambda x: x["cost"], reverse=True)
    return sorted_services[:top_n]
def compute_savings_potential(by_service: list) -> dict:
    total = sum(s["cost"] for s in by_service)
    estimated_savings = round(total * 0.30, 2)
    return {
        "estimated_savings": estimated_savings,
        "savings_percentage": 30,
        "total_spend": total,
    }