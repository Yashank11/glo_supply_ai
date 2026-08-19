from database import ShippingRoute, Port

class LogisticsAgent:
    def __init__(self):
        pass

    def evaluate_route_options(self, db, origin_type: str, origin_id: int, dest_type: str, dest_id: int) -> list:
        """
        Queries all available shipping routes between origin and destination,
        and rates them based on cost, transit time, and status.
        """
        routes = db.query(ShippingRoute).filter(
            ShippingRoute.origin_type == origin_type,
            ShippingRoute.origin_id == origin_id,
            ShippingRoute.dest_type == dest_type,
            ShippingRoute.dest_id == dest_id
        ).all()
        
        evaluation = []
        for r in routes:
            score = 100
            # Penalty for slow routes
            score -= r.lead_time_days * 1.5
            # Penalty for expensive routes
            score -= r.cost_per_unit * 10
            # Penalty for congested or blocked status
            status_penalty = {
                "Active": 0,
                "Congested": 30,
                "Blocked": 100
            }.get(r.status, 0)
            score -= status_penalty

            evaluation.append({
                "route_id": r.id,
                "name": r.name,
                "transport_mode": r.transport_mode,
                "lead_time_days": r.lead_time_days,
                "cost_per_unit": r.cost_per_unit,
                "status": r.status,
                "feasibility_score": max(0.0, round(score, 1))
            })
            
        # Sort by feasibility score descending
        return sorted(evaluation, key=lambda x: x["feasibility_score"], reverse=True)

    def calculate_reroute_impact(self, db, primary_route_id: int, alternate_route_id: int) -> dict:
        """
        Calculates differences in cost, time, and mode between two routes.
        Useful when simulating Suez Canal closure or port closures.
        """
        primary = db.query(ShippingRoute).filter(ShippingRoute.id == primary_route_id).first()
        alternate = db.query(ShippingRoute).filter(ShippingRoute.id == alternate_route_id).first()
        
        if not primary or not alternate:
            return {"error": "Primary or Alternate route not found."}
            
        time_diff_days = alternate.lead_time_days - primary.lead_time_days
        cost_diff_pct = ((alternate.cost_per_unit - primary.cost_per_unit) / primary.cost_per_unit) * 100
        
        return {
            "primary_route_name": primary.name,
            "alternate_route_name": alternate.name,
            "primary_lead_time_days": primary.lead_time_days,
            "alternate_lead_time_days": alternate.lead_time_days,
            "delay_added_days": round(time_diff_days, 1),
            "primary_cost_per_unit": primary.cost_per_unit,
            "alternate_cost_per_unit": alternate.cost_per_unit,
            "cost_increase_pct": round(cost_diff_pct, 1),
            "modes": {
                "primary": primary.transport_mode,
                "alternate": alternate.transport_mode
            }
        }
