from llm_client import LLMClient
from database import Supplier, Product
import json

class ProcurementCopilot:
    def __init__(self):
        self.llm = LLMClient()
        self.system_prompt = (
            "You are a Procurement Specialist AI Copilot. Your job is to help supply chain managers "
            "evaluate alternative suppliers, draft negotiation strategies, and summarize vendor contracts. "
            "Keep insights professional, data-backed, and focused on risk mitigation."
        )

    def find_alternative_suppliers(self, db, product_sku: str) -> list:
        """
        Queries all suppliers that can provide products matching the SKU,
        compares costs, countries, and overall risk levels.
        """
        product = db.query(Product).filter(Product.sku == product_sku).first()
        if not product:
            return []

        alternatives = []
        for s in product.suppliers:
            # Determine cost tier for display
            cost_tier = "Medium"
            if product.base_cost < 500:
                cost_tier = "Low"
            elif product.base_cost > 2000:
                cost_tier = "High"

            alternatives.append({
                "supplier_name": s.name,
                "country": s.country,
                "overall_risk": s.overall_risk,
                "geopolitical_risk": s.geopolitical_risk,
                "climate_risk": s.climate_risk,
                "financial_risk": s.financial_risk,
                "cost_tier": cost_tier,
                "status": s.status
            })
            
        # We can also seed alternative mock options that are not in the primary path
        # to show active sourcing recommendations.
        if product_sku == "PROD-EVBAT":
            # Add LG Energy & Panasonic mock alternatives if not already fully linked
            if not any(a["supplier_name"] == "LG Energy Solution" for a in alternatives):
                alternatives.append({
                    "supplier_name": "LG Energy Solution",
                    "country": "South Korea",
                    "overall_risk": 27.0,
                    "geopolitical_risk": 35.0,
                    "climate_risk": 20.0,
                    "financial_risk": 20.0,
                    "cost_tier": "Medium",
                    "status": "Active"
                })
            if not any(a["supplier_name"] == "Panasonic" for a in alternatives):
                alternatives.append({
                    "supplier_name": "Panasonic",
                    "country": "Japan",
                    "overall_risk": 29.0,
                    "geopolitical_risk": 20.0,
                    "climate_risk": 45.0,
                    "financial_risk": 15.0,
                    "cost_tier": "High",
                    "status": "Active"
                })
        elif product_sku == "PROD-IPH17" or product_sku == "PROD-MACM4":
            if not any(a["supplier_name"] == "Samsung Foundry" for a in alternatives):
                alternatives.append({
                    "supplier_name": "Samsung Foundry",
                    "country": "South Korea",
                    "overall_risk": 26.0,
                    "geopolitical_risk": 35.0,
                    "climate_risk": 25.0,
                    "financial_risk": 10.0,
                    "cost_tier": "Medium",
                    "status": "Active"
                })
                
        return alternatives

    def generate_negotiation_insights(self, current_supplier: str, target_supplier: str, product_name: str) -> dict:
        """
        Uses Gemini to generate custom negotiation talking points and transition tactics.
        """
        prompt = f"""
        Provide negotiation talking points and a transition strategy for moving procurement 
        of "{product_name}" from the current supplier "{current_supplier}" to the backup/alternative supplier "{target_supplier}".
        
        Analyze structural leverage:
        1. Leverage points (tariffs, local geopolitical risk offsets, lead time differences).
        2. Suggested target pricing / cost targets.
        3. Risk mitigation terms to include in the new contract (e.g. force majeure clauses).
        
        Respond with a JSON object containing:
        {{
          "leverage_points": ["Point 1", "Point 2", "Point 3"],
          "negotiation_tactics": ["Tactic 1", "Tactic 2"],
          "contract_clauses_recommended": ["Clause 1", "Clause 2"],
          "estimated_transition_time_weeks": 8
        }}
        
        JSON:
        """
        return self.llm.generate_json(prompt, system_instruction=self.system_prompt)

    def summarize_contract(self, contract_text: str) -> dict:
        """
        Summarizes key terms, delivery timelines, payment terms, and liability.
        """
        prompt = f"""
        Summarize the following vendor contract. Highlight the critical terms, milestones, and liabilities.
        
        Contract Text:
        "{contract_text}"
        
        Respond with a JSON object:
        {{
          "parties": "Who is signing...",
          "effective_date": "Date...",
          "key_deliverables": ["Deliverable 1", "Deliverable 2"],
          "termination_terms": "Terms of termination...",
          "liability_limitation": "Financial liability limits...",
          "risk_exposure_rating": "Low/Medium/High"
        }}
        
        JSON:
        """
        return self.llm.generate_json(prompt, system_instruction=self.system_prompt)
