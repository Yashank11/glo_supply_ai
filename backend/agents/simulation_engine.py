from database import Port, ShippingRoute, Inventory, Product, Warehouse, Customer
from agents.risk_agent import RiskAgent
from agents.forecast_agent import ForecastAgent
from agents.logistics_agent import LogisticsAgent
from agents.finance_agent import FinanceAgent
from agents.procurement_copilot import ProcurementCopilot
from neo4j_service import Neo4jService
import math

class ScenarioSimulator:
    def __init__(self):
        self.forecast_agent = ForecastAgent()
        self.logistics_agent = LogisticsAgent()
        self.finance_agent = FinanceAgent()
        self.procurement_copilot = ProcurementCopilot()
        
    def simulate_port_closure(self, db, port_name: str, closure_duration_days: int) -> dict:
        """
        Simulates the closure of a major shipping port (e.g., Shanghai Port) for N days.
        """
        # Find port in DB
        port = db.query(Port).filter(Port.name == port_name).first()
        if not port:
            return {"error": f"Port '{port_name}' not found."}

        # 1. Graph Blast Radius (Identify downstream nodes affected)
        graph = Neo4jService()
        try:
            graph.sync_from_relational_db(db)
            blast_radius = graph.get_blast_radius(port.id, "Port")
        except Exception as e:
            print(f"Graph blast radius error: {e}")
            blast_radius = []
        finally:
            graph.close()

        # Extract names and types of affected nodes
        affected_warehouses = [n for n in blast_radius if n["label"] == "Warehouse"]
        affected_customers = [n for n in blast_radius if n["label"] == "Customer"]
        
        # 2. Identify shipping routes impacted
        impacted_routes = db.query(ShippingRoute).filter(
            ((ShippingRoute.origin_type == "Port") & (ShippingRoute.origin_id == port.id)) |
            ((ShippingRoute.dest_type == "Port") & (ShippingRoute.dest_id == port.id))
        ).all()

        products_affected = set()
        total_units_delayed = 0.0
        max_transit_delay = closure_duration_days
        rerouting_additional_cost = 0.0

        # Rerouting option evaluation
        alternative_route_details = None
        for route in impacted_routes:
            if route.alternative_route_id:
                # Calculate rerouting impact using Logistics Agent
                alt_impact = self.logistics_agent.calculate_reroute_impact(db, route.id, route.alternative_route_id)
                if "error" not in alt_impact:
                    alternative_route_details = alt_impact
                    # Shifting to alternate route adds cost but reduces delay
                    max_transit_delay = alt_impact["delay_added_days"]
                    rerouting_additional_cost = alt_impact["alternate_cost_per_unit"] - alt_impact["primary_cost_per_unit"]

        # 3. Simulate inventory depletion at downstream warehouses
        inventory_impacts = []
        revenue_loss_estimate = 0.0
        net_financial_impact = 0.0

        # Look up products at affected warehouses
        for wh in affected_warehouses:
            # Extract numerical id from "warehouse_{id}"
            wh_id = int(wh["id"].split("_")[1])
            inventories = db.query(Inventory).filter(Inventory.warehouse_id == wh_id).all()
            
            for inv in inventories:
                prod = db.query(Product).filter(Product.id == inv.product_id).first()
                products_affected.add(prod.name)
                
                # Demand and forecast
                # If the port is closed, replenishment is cut off for 'closure_duration_days'
                daily_demand = inv.daily_demand
                total_units_delayed += daily_demand * closure_duration_days
                
                # Check depletion
                fc = self.forecast_agent.forecast_inventory(
                    current_stock=inv.current_stock,
                    daily_demand=daily_demand,
                    safety_stock=inv.safety_stock,
                    lead_time_days=int(max_transit_delay),
                    horizon_days=30
                )
                
                # Estimate financial cost of this depletion
                fin_impact = self.finance_agent.calculate_disruption_cost(
                    units_affected=daily_demand * closure_duration_days,
                    unit_cost=prod.base_cost,
                    selling_price=prod.selling_price,
                    delay_days=max_transit_delay,
                    freight_increase_per_unit=rerouting_additional_cost
                )
                
                revenue_loss_estimate += fin_impact["revenue_lost"]
                net_financial_impact += fin_impact["total_financial_loss"]

                inventory_impacts.append({
                    "warehouse_name": wh["name"],
                    "product_name": prod.name,
                    "current_stock": inv.current_stock,
                    "safety_stock": inv.safety_stock,
                    "depletion_days": fc["depletion_days"],
                    "stockout_probability": fc["stockout_probability"],
                    "stockout_risk_level": "High" if fc["depletion_days"] < max_transit_delay and fc["depletion_days"] > 0 else "Low"
                })

        # Recommendations list
        recommendations = [
            f"Activate emergency diversion to alternative port (e.g., Ningbo Port) to reduce lead time delay from {closure_duration_days} days to {max_transit_delay} days.",
            f"Pre-allocate air freight capacity for critical high-value SKUs ({', '.join(list(products_affected)[:2])}) to bypass ocean routes entirely.",
            "Contact backup raw-material and component suppliers to distribute production volumes away from primary affected factory zones."
        ]

        return {
            "scenario": f"Closure of {port_name} for {closure_duration_days} days",
            "products_affected_count": len(products_affected),
            "products_affected": list(products_affected),
            "units_delayed": round(total_units_delayed, 0),
            "revenue_at_risk": round(revenue_loss_estimate * 3, 2), # overall contract at risk
            "expected_revenue_loss": round(revenue_loss_estimate, 2),
            "total_financial_impact": round(net_financial_impact, 2),
            "warehouses_impacted": [w["name"] for w in affected_warehouses],
            "customers_impacted": [c["name"] for c in affected_customers],
            "inventory_status": inventory_impacts,
            "alternative_route": alternative_route_details,
            "recommendations": recommendations
        }

    def simulate_commodity_price_spike(self, db, commodity_name: str, price_increase_pct: float) -> dict:
        """
        Simulates cost increases when raw materials / commodities (e.g. Lithium, Oil, Copper) rise.
        """
        commodity_name_lower = commodity_name.lower().strip()
        
        # 1. Global Logistics / Fuel Impact (Oil)
        if commodity_name_lower == "oil":
            commodity_spend = 45000000.0  # default logistics fuel spend
            logistics_factor = 0.6
            trans_cost_rise = price_increase_pct * logistics_factor
            base_cost_rise = price_increase_pct * 0.05
            
            fin_impact = self.finance_agent.evaluate_commodity_price_impact(
                annual_spend=commodity_spend,
                price_increase_pct=price_increase_pct,
                pass_through_pct=25.0
            )
            
            recommendations = [
                f"Negotiate long-term index-linked pricing hedges for Crude Oil / Fuel to stabilize global logistics cost fluctuations.",
                f"Increase logistics surcharges to customers to pass through at least {round(price_increase_pct * 0.25, 1)}% of transport price spikes.",
                f"Shift shipping routes to modes with higher fuel efficiency (e.g., Rail over Air/Road where feasible)."
            ]
            
            return {
                "scenario": f"Logistics Fuel (Oil) price increase of {price_increase_pct}%",
                "transportation_cost_increase_pct": round(trans_cost_rise, 1),
                "production_cost_increase_pct": round(base_cost_rise, 1),
                "annual_gross_cost_increase": fin_impact["gross_cost_increase"],
                "expected_annual_loss": fin_impact["net_margin_loss"],
                "margin_absorbed_pct": 75.0,
                "recommendations": recommendations
            }

        # 2. Product-specific raw material impact
        products = db.query(Product).all()
        affected_products = []
        
        total_annual_spend = 0.0
        total_gross_cost_increase = 0.0
        total_expected_annual_loss = 0.0
        
        for p in products:
            materials = [m.strip().lower() for m in (p.essential_materials or "").split(",") if m.strip()]
            if commodity_name_lower in materials:
                affected_products.append(p.name)
                # Find demand/volume for this product in warehouses
                inventories = db.query(Inventory).filter(Inventory.product_id == p.id).all()
                annual_demand = sum(inv.daily_demand * 365 for inv in inventories)
                
                # Annual base cost spend for this product
                product_base_spend = annual_demand * p.base_cost
                
                # Assume this specific commodity represents a portion of the product base cost
                # E.g. default to 30% of base cost is this raw material
                commodity_cost_contribution_pct = 30.0
                commodity_annual_spend = product_base_spend * (commodity_cost_contribution_pct / 100.0)
                
                # Calculate cost increase for this product
                product_gross_increase = commodity_annual_spend * (price_increase_pct / 100.0)
                # Assume we absorb 75% and pass through 25% to customers
                product_net_loss = product_gross_increase * 0.75
                
                total_annual_spend += commodity_annual_spend
                total_gross_cost_increase += product_gross_increase
                total_expected_annual_loss += product_net_loss
                
        if not affected_products:
            # Fallback if no products explicitly link, but it was selected
            total_annual_spend = 10000000.0
            total_gross_cost_increase = total_annual_spend * (price_increase_pct / 100.0)
            total_expected_annual_loss = total_gross_cost_increase * 0.75
            
        trans_cost_rise = price_increase_pct * 0.05  # Minimal logistics impact
        prod_cost_factor = 0.3
        base_cost_rise = price_increase_pct * prod_cost_factor
        
        recommendations = [
            f"Negotiate long-term volume commitments with backup suppliers of {commodity_name_lower} to hedge against price volatility.",
            f"Increase customer selling price of affected products ({', '.join(affected_products[:2])}) to pass through raw material cost spikes.",
            f"Redesign products to reduce reliance on {commodity_name_lower} or qualify alternative raw material grades."
        ]
        
        return {
            "scenario": f"{commodity_name.capitalize()} price increase of {price_increase_pct}%",
            "transportation_cost_increase_pct": round(trans_cost_rise, 1),
            "production_cost_increase_pct": round(base_cost_rise, 1),
            "annual_gross_cost_increase": round(total_gross_cost_increase, 2),
            "expected_annual_loss": round(total_expected_annual_loss, 2),
            "margin_absorbed_pct": 75.0,
            "recommendations": recommendations
        }
