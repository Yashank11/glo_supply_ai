from llm_client import LLMClient
from database import Supplier, Product, Inventory, Warehouse, Port
from agents.risk_agent import RiskAgent
from agents.forecast_agent import ForecastAgent
from agents.simulation_engine import ScenarioSimulator
from agents.procurement_copilot import ProcurementCopilot
import json

class ExecutiveAgent:
    def __init__(self, db_session):
        self.db = db_session
        self.llm = LLMClient()
        self.risk_agent = RiskAgent()
        self.forecast_agent = ForecastAgent()
        self.simulator = ScenarioSimulator()
        self.procurement = ProcurementCopilot()
        self.system_prompt = (
            "You are the Lead Executive Advisor Agent for a Supply Chain Digital Twin. "
            "Your task is to take complex structural, logistic, financial, and simulation reports, "
            "and generate a clear, highly polished, executive-level summary. "
            "Use clear headings, bullet points, bold text, and markdown tables where appropriate. "
            "Always maintain a strategic, risk-aware, and decisive business tone."
        )

    def process_query(self, query: str) -> dict:
        """
        1. Classifies the executive query.
        2. Routes to appropriate sub-agents.
        3. Generates synthesized briefing.
        """
        # Step 1: Classify using LLM
        classification_prompt = f"""
        Classify the following executive question into one of these categories:
        - "RISK": Query about supplier risks, geopolitics, country risk, or sentiment.
        - "FORECAST": Query about future inventory levels, demand, stockouts, or commodity price trends.
        - "SIMULATION": Query asking "what if" a port/factory closes, exports stop, or prices spike.
        - "PROCUREMENT": Query asking to find/compare alternatives, summarize contracts, or manage spend.
        - "GENERAL": Other general supply chain questions.
        
        Question: "{query}"
        
        Respond with a JSON object:
        {{
          "category": "RISK/FORECAST/SIMULATION/PROCUREMENT/GENERAL",
          "intent": "Short summary of user intent",
          "entities": ["list of entities mentioned, e.g. TSMC, Shanghai Port, lithium, Taiwan"]
        }}
        
        JSON:
        """
        plan = self.llm.generate_json(classification_prompt, system_instruction="Identify query intent.")
        category = plan.get("category", "GENERAL")
        entities = plan.get("entities", [])
        
        data_collected = {}
        
        # Step 2: RAG Semantic Context Retrieval
        try:
            from rag_service import VectorRAGService
            rag_service = VectorRAGService()
            rag_matches = rag_service.search(query, top_k=2)
            data_collected["retrieved_contracts_and_policies"] = [
                {"id": m["id"], "text": m["text"], "relevance_score": round(m["similarity_score"], 3)}
                for m in rag_matches if m["similarity_score"] > 0.35 # relevance threshold
            ]
        except Exception as e:
            print(f"RAG search error: {e}")
        
        # Step 3: Route and execute agents
        if category == "RISK":
            # Find supplier or location risk
            suppliers = self.db.query(Supplier).all()
            risk_summary = []
            for s in suppliers:
                # Update risks
                self.risk_agent.calculate_supplier_risk(self.db, s.id)
                risk_summary.append({
                    "name": s.name,
                    "country": s.country,
                    "overall_risk": s.overall_risk,
                    "geopolitical": s.geopolitical_risk,
                    "climate": s.climate_risk,
                    "financial": s.financial_risk,
                    "logistics": s.logistics_risk
                })
            data_collected["suppliers"] = sorted(risk_summary, key=lambda x: x["overall_risk"], reverse=True)
            
        elif category == "FORECAST":
            # Grab products and current stock forecasting
            inventories = self.db.query(Inventory).all()
            forecast_summary = []
            for inv in inventories:
                prod = self.db.query(Product).filter(Product.id == inv.product_id).first()
                wh = self.db.query(Warehouse).filter(Warehouse.id == inv.warehouse_id).first()
                fc = self.forecast_agent.forecast_inventory(
                    current_stock=inv.current_stock,
                    daily_demand=inv.daily_demand,
                    safety_stock=inv.safety_stock,
                    lead_time_days=10
                )
                forecast_summary.append({
                    "product": prod.name,
                    "sku": prod.sku,
                    "warehouse": wh.name,
                    "current_stock": inv.current_stock,
                    "safety_stock": inv.safety_stock,
                    "depletion_days": fc["depletion_days"],
                    "stockout_probability": fc["stockout_probability"]
                })
            data_collected["forecasts"] = forecast_summary
            
        elif category == "SIMULATION":
            # Determine simulation type. If they mention Taiwan or port closure:
            # Let's see if we can trigger a port or export simulation
            target_port = "Shanghai Port"
            for ent in entities:
                if "port" in ent.lower() or "shanghai" in ent.lower():
                    target_port = "Shanghai Port"
            
            # If they query about Taiwan, let's mock/sim a Taiwan shipping halt or Kaohsiung closure
            is_taiwan = any("taiwan" in ent.lower() or "kaohsiung" in ent.lower() for ent in entities)
            if is_taiwan:
                target_port = "Kaohsiung Port"
                
            sim_result = self.simulator.simulate_port_closure(self.db, target_port, closure_duration_days=12)
            data_collected["simulation"] = sim_result
            
        elif category == "PROCUREMENT":
            # Sourcing alternative suppliers
            sku = "PROD-EVBAT" # default
            for ent in entities:
                if "battery" in ent.lower() or "lithium" in ent.lower():
                    sku = "PROD-EVBAT"
                elif "iphone" in ent.lower() or "chip" in ent.lower() or "tsmc" in ent.lower():
                    sku = "PROD-IPH17"
                elif "macbook" in ent.lower() or "asml" in ent.lower():
                    sku = "PROD-MACM4"
            
            alternatives = self.procurement.find_alternative_suppliers(self.db, sku)
            prod = self.db.query(Product).filter(Product.sku == sku).first()
            data_collected["sourcing"] = {
                "product_name": prod.name if prod else "Lithium Battery Pack",
                "sku": sku,
                "alternatives": alternatives
            }
            
        # Step 3: Synthesis Response using LLM
        synthesis_prompt = f"""
        You are the Executive Advisor Agent. Synthesize a professional briefing based on:
        
        User Query: "{query}"
        Category Routed: "{category}"
        Structured Data Collected:
        {json.dumps(data_collected, indent=2)}
        
        Write a concise, high-impact executive response in Markdown format.
        Structure:
        1. **Executive Summary**: 2-3 sentence strategic takeaway.
        2. **Core Insights / Data Presentation**: Use a Markdown table, key bullets, or metrics.
        3. **Simulation Impacts** (if applicable): Financial at-risk exposure, stockout times.
        4. **Actionable Recommendations**: Next steps for leadership (diversification, buffer inventory, hedging).
        
        Keep it direct. Do not write filler. Focus on margins, risk levels, and alternative pathways.
        """
        response_markdown = self.llm.generate_text(synthesis_prompt, system_instruction=self.system_prompt)
        
        return {
            "category": category,
            "intent": plan.get("intent", ""),
            "data": data_collected,
            "response": response_markdown
        }
