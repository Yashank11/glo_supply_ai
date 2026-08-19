from llm_client import LLMClient
from database import Supplier, CountryRisk, ActiveDisruption
import json

class RiskAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.system_prompt = (
            "You are a Risk Assessment Agent for a Global Supply Chain Digital Twin. "
            "Your job is to analyze geopolitical news, climate forecasts, and financial updates, "
            "and compute risk dimensions for suppliers. You must output ONLY a valid JSON object."
        )

    def calculate_supplier_risk(self, db, supplier_id: int) -> dict:
        """
        Dynamically calculates numeric risk metrics (0-100) based on DB records
        and active disruptions in the supplier's country or region.
        """
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            return {"error": "Supplier not found"}

        # Get base country risk
        country_risk = db.query(CountryRisk).filter(CountryRisk.country == supplier.country).first()
        base_geo = country_risk.geopolitical_risk if country_risk else 20.0
        base_climate = country_risk.climate_risk if country_risk else 20.0
        
        # Calculate dynamic offsets based on active disruptions in that country
        disruptions = db.query(ActiveDisruption).filter(
            ActiveDisruption.location == supplier.country,
            ActiveDisruption.active == 1
        ).all()
        
        geo_multiplier = 1.0
        climate_multiplier = 1.0
        logistics_multiplier = 1.0
        
        for d in disruptions:
            severity_weight = {
                "Low": 1.1,
                "Medium": 1.3,
                "High": 1.6,
                "Critical": 2.0
            }.get(d.severity, 1.0)
            
            if d.event_type in ["War", "Tariff", "Sanction", "Political Instability"]:
                geo_multiplier *= severity_weight
            elif d.event_type in ["Typhoon", "Cyclone", "Flood", "Wildfire", "Heatwave"]:
                climate_multiplier *= severity_weight
            elif d.event_type in ["Port Closure", "Strike", "Container Shortage", "Congestion"]:
                logistics_multiplier *= severity_weight

        # Apply multiplier cap at 100
        geo_risk = min(base_geo * geo_multiplier, 100.0)
        climate_risk = min(base_climate * climate_multiplier, 100.0)
        logistics_risk = min(supplier.logistics_risk * logistics_multiplier, 100.0)
        financial_risk = supplier.financial_risk  # Assume relatively stable unless financial event occurs
        
        # Calculate weighted overall risk
        overall_risk = (geo_risk * 0.3) + (climate_risk * 0.2) + (financial_risk * 0.25) + (logistics_risk * 0.25)
        overall_risk = round(overall_risk, 1)

        # Update in database
        supplier.geopolitical_risk = round(geo_risk, 1)
        supplier.climate_risk = round(climate_risk, 1)
        supplier.logistics_risk = round(logistics_risk, 1)
        supplier.overall_risk = overall_risk
        db.commit()

        return {
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "geopolitical_risk": supplier.geopolitical_risk,
            "climate_risk": supplier.climate_risk,
            "financial_risk": supplier.financial_risk,
            "logistics_risk": supplier.logistics_risk,
            "overall_risk": supplier.overall_risk
        }

    def generate_detailed_risk_report(self, supplier_name: str, supplier_country: str, recent_news: str) -> dict:
        """
        Uses Gemini to generate a qualitative risk assessment summary.
        """
        prompt = f"""
        Generate a detailed supplier risk profile for the following:
        
        Supplier: "{supplier_name}"
        Country: "{supplier_country}"
        Recent Context/News: "{recent_news}"
        
        Compute and explain:
        1. Geopolitical Risk Profile
        2. Climate/Natural Disaster Risk Profile
        3. Financial/Health Risk Profile
        4. Logistics/Delivery Delay Risk Profile
        
        Output a JSON object with the following structure:
        {{
          "geopolitical_analysis": "Explanation of geopolitical factors...",
          "climate_analysis": "Explanation of climate and weather risks...",
          "financial_analysis": "Explanation of financial and operational risks...",
          "logistics_analysis": "Explanation of shipping and logistics risks...",
          "risk_warnings": ["List of 2-3 specific bullet warning signs"],
          "mitigation_priority": "High/Medium/Low"
        }}
        
        JSON:
        """
        return self.llm.generate_json(prompt, system_instruction=self.system_prompt)
