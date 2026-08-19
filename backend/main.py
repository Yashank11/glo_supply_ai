import os
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from database import init_db, SessionLocal, Supplier, Factory, Warehouse, Port, Customer, ShippingRoute, Inventory, ActiveDisruption, CountryRisk, Product, product_supplier_association
from neo4j_service import Neo4jService
from agents.event_agent import EventIntelligenceAgent
from agents.risk_agent import RiskAgent
from agents.forecast_agent import ForecastAgent
from agents.simulation_engine import ScenarioSimulator
from agents.procurement_copilot import ProcurementCopilot
from agents.executive_agent import ExecutiveAgent

# Initialize DB on startup
init_db()

app = FastAPI(title="Global Supply Chain Digital Twin API", version="1.0.0")

# Enable CORS for frontend Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic schemas for request validation
class NewsFeedRequest(BaseModel):
    text: str

class SimulationRequest(BaseModel):
    port_name: str
    duration_days: int

class CommoditySimulationRequest(BaseModel):
    commodity_name: str
    price_increase_pct: float

class SourcingRequest(BaseModel):
    sku: str

class NegotiationRequest(BaseModel):
    current_supplier: str
    target_supplier: str
    product_name: str

class ChatRequest(BaseModel):
    message: str

class SupplierCreate(BaseModel):
    name: str
    country: str
    city: str
    latitude: float
    longitude: float
    geopolitical_risk: Optional[float] = 20.0
    climate_risk: Optional[float] = 20.0
    financial_risk: Optional[float] = 20.0
    logistics_risk: Optional[float] = 20.0

class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = ""
    base_cost: float
    selling_price: float

class RouteCreate(BaseModel):
    name: str
    origin_type: str
    origin_id: int
    dest_type: str
    dest_id: int
    transport_mode: str
    lead_time_days: float
    cost_per_unit: float

class NetworkImportRequest(BaseModel):
    suppliers: List[SupplierCreate]
    products: List[ProductCreate]
    routes: List[RouteCreate]

# API Routes

@app.get("/api/kpis")
def get_kpis(db: Session = Depends(get_db)):
    """
    Computes and returns high-level dashboard KPIs.
    """
    total_suppliers = db.query(Supplier).count()
    at_risk_suppliers = db.query(Supplier).filter(Supplier.overall_risk > 50).count()
    active_disruptions = db.query(ActiveDisruption).filter(ActiveDisruption.active == 1).count()
    
    # Calculate avg stockout probability
    forecast_agent = ForecastAgent()
    inventories = db.query(Inventory).all()
    stockout_probs = []
    for inv in inventories:
        fc = forecast_agent.forecast_inventory(
            current_stock=inv.current_stock,
            daily_demand=inv.daily_demand,
            safety_stock=inv.safety_stock,
            lead_time_days=10
        )
        stockout_probs.append(fc["stockout_probability"])
        
    avg_stockout_prob = round(sum(stockout_probs) / len(stockout_probs), 1) if stockout_probs else 0.0
    
    # Delayed shipments mock count (active disruptions increase this)
    delayed_shipments = active_disruptions * 12 + 5
    
    # Expected Revenue Impact (sum of revenue at risk from active events)
    revenue_impact = active_disruptions * 2500000.0 # $2.5M per active event average
    
    return {
        "total_suppliers": total_suppliers,
        "at_risk_suppliers": at_risk_suppliers,
        "active_disruptions": active_disruptions,
        "avg_stockout_probability": avg_stockout_prob,
        "delayed_shipments": delayed_shipments,
        "expected_revenue_impact": revenue_impact
    }

@app.get("/api/graph")
def get_graph(db: Session = Depends(get_db)):
    """
    Syncs relational entities to Neo4j/NetworkX and returns the graph data.
    """
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
        data = graph.get_graph_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph database: {str(e)}")
    finally:
        graph.close()

@app.get("/api/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    """
    Returns list of suppliers with details, dynamic risk ratings, and live weather.
    """
    risk_agent = RiskAgent()
    suppliers = db.query(Supplier).all()
    
    # Import connector to call Open-Meteo REST API
    from api_connectors import GlobalDataConnectors
    connectors = GlobalDataConnectors()
    
    result = []
    for s in suppliers:
        # Dynamically recalculate risk based on active events
        risk_data = risk_agent.calculate_supplier_risk(db, s.id)
        
        # Fetch live weather at the supplier's coordinate in real-time
        live_weather = connectors.get_live_weather(s.latitude, s.longitude)
        
        result.append({
            "id": s.id,
            "name": s.name,
            "country": s.country,
            "city": s.city,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "risks": risk_data,
            "weather": live_weather,
            "status": s.status
        })
    return result

@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    """
    Returns active disruption events.
    """
    events = db.query(ActiveDisruption).filter(ActiveDisruption.active == 1).order_by(ActiveDisruption.created_at.desc()).all()
    return events

@app.post("/api/events/ingest")
def ingest_event(req: NewsFeedRequest, db: Session = Depends(get_db)):
    """
    Ingests raw news or alerts, uses Event Intelligence Agent to parse,
    saves the disruption to DB, and recalculates affected supplier risk.
    """
    event_agent = EventIntelligenceAgent()
    parsed_event = event_agent.analyze_disruption(req.text)
    
    # Save disruption to DB
    disruption = ActiveDisruption(
        event_type=parsed_event["event"],
        location=parsed_event["location"],
        severity=parsed_event["severity"],
        expected_duration_days=parsed_event.get("expected_duration_days", 10),
        impact_description=parsed_event["description"],
        active=1
    )
    db.add(disruption)
    db.commit()
    db.refresh(disruption)
    
    # Recalculate risks for all suppliers in that country
    risk_agent = RiskAgent()
    affected_suppliers = db.query(Supplier).filter(Supplier.country == parsed_event["location"]).all()
    recalculated = []
    
    for s in affected_suppliers:
        risk_data = risk_agent.calculate_supplier_risk(db, s.id)
        recalculated.append({
            "supplier_name": s.name,
            "new_overall_risk": risk_data["overall_risk"]
        })
        
    # Re-sync graph
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
    except Exception as e:
        print(f"Post-ingest graph sync error: {e}")
    finally:
        graph.close()

    return {
        "status": "Event Ingested Successfully",
        "event_extracted": parsed_event,
        "affected_suppliers_count": len(affected_suppliers),
        "recalculated_supplier_risks": recalculated
    }

@app.post("/api/events/fetch-live")
def fetch_live_events(db: Session = Depends(get_db)):
    """
    Automatically queries GDELT for recent supply chain disruptions,
    parses them with the Event Intelligence Agent, and saves active events.
    """
    from api_connectors import GlobalDataConnectors
    connectors = GlobalDataConnectors()
    
    # Query GDELT public news API
    news_list = connectors.query_gdelt_geopolitical_news("supply chain disruption")
    
    event_agent = EventIntelligenceAgent()
    risk_agent = RiskAgent()
    ingested_events = []
    
    # Process the top 2 articles from GDELT
    for news in news_list[:2]:
        headline = news["title"]
        # Analyze and extract location/severity with Gemini
        parsed_event = event_agent.analyze_disruption(headline)
        
        # Avoid duplicate active events for the same type and country
        existing = db.query(ActiveDisruption).filter(
            ActiveDisruption.event_type == parsed_event["event"],
            ActiveDisruption.location == parsed_event["location"],
            ActiveDisruption.active == 1
        ).first()
        
        # Save if unique and not a generic fallback alert
        if not existing and parsed_event["event"] != "Disruption Alert" and parsed_event["location"] != "Global":
            disruption = ActiveDisruption(
                event_type=parsed_event["event"],
                location=parsed_event["location"],
                severity=parsed_event["severity"],
                expected_duration_days=parsed_event.get("expected_duration_days", 7),
                impact_description=f"{parsed_event['description']} (Source: {news['source']})",
                active=1
            )
            db.add(disruption)
            db.commit()
            db.refresh(disruption)
            
            # Update risks for suppliers in that region
            affected_suppliers = db.query(Supplier).filter(Supplier.country == parsed_event["location"]).all()
            for s in affected_suppliers:
                risk_agent.calculate_supplier_risk(db, s.id)
                
            ingested_events.append({
                "headline": headline,
                "event_extracted": parsed_event
            })
            
    # Sync Graph DB
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
    finally:
        graph.close()
        
    return {
        "status": f"Successfully fetched recent news. Auto-ingested {len(ingested_events)} disruptions.",
        "ingested_events": ingested_events
    }

@app.post("/api/events/clear")
def clear_events(db: Session = Depends(get_db)):
    """
    Clears active disruptions to reset risks.
    """
    db.query(ActiveDisruption).update({ActiveDisruption.active: 0})
    db.commit()
    
    # Reset all suppliers risk scores
    suppliers = db.query(Supplier).all()
    risk_agent = RiskAgent()
    for s in suppliers:
        # Reset multiplier values to default base country scores
        country_risk = db.query(CountryRisk).filter(CountryRisk.country == s.country).first()
        base_risk = country_risk.overall_risk if country_risk else 25.0
        
        s.geopolitical_risk = country_risk.geopolitical_risk if country_risk else 20.0
        s.climate_risk = country_risk.climate_risk if country_risk else 20.0
        s.logistics_risk = 20.0
        s.overall_risk = base_risk
    db.commit()
    
    return {"status": "Disruptions cleared. Risks reset to baseline."}

@app.post("/api/simulate/port")
def simulate_port(req: SimulationRequest, db: Session = Depends(get_db)):
    """
    Simulates the closure of a specific port.
    """
    simulator = ScenarioSimulator()
    result = simulator.simulate_port_closure(db, req.port_name, req.duration_days)
    return result

@app.post("/api/simulate/commodity")
def simulate_commodity(req: CommoditySimulationRequest, db: Session = Depends(get_db)):
    """
    Simulates commodity cost spike impact.
    """
    simulator = ScenarioSimulator()
    result = simulator.simulate_commodity_price_spike(db, req.commodity_name, req.price_increase_pct)
    return result

@app.post("/api/procurement/alternatives")
def get_alternatives(req: SourcingRequest, db: Session = Depends(get_db)):
    """
    Finds alternative suppliers for a given product SKU.
    """
    procurement = ProcurementCopilot()
    alternatives = procurement.find_alternative_suppliers(db, req.sku)
    return alternatives

@app.post("/api/procurement/negotiate")
def get_negotiation(req: NegotiationRequest, db: Session = Depends(get_db)):
    """
    Generates negotiation strategy and talking points.
    """
    procurement = ProcurementCopilot()
    result = procurement.generate_negotiation_insights(
        req.current_supplier, req.target_supplier, req.product_name
    )
    return result

@app.post("/api/chat")
def executive_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Executes natural language queries through the Executive Multi-Agent planner.
    """
    exec_agent = ExecutiveAgent(db)
    result = exec_agent.process_query(req.message)
    return result

class RAGQueryRequest(BaseModel):
    query: str

@app.post("/api/rag/query")
def query_rag(req: RAGQueryRequest):
    """
    Executes semantic document search and returns a fact-grounded RAG response.
    """
    from rag_service import VectorRAGService
    rag_service = VectorRAGService()
    answer = rag_service.generate_rag_answer(req.query)
    matches = rag_service.search(req.query, top_k=2)
    return {
        "answer": answer,
        "sources": [
            {"id": m["id"], "text": m["text"], "score": round(m["similarity_score"], 3)}
            for m in matches
        ]
    }

@app.post("/api/suppliers")
def create_supplier(req: SupplierCreate, db: Session = Depends(get_db)):
    """
    Registers a new supplier in the database.
    """
    existing = db.query(Supplier).filter(Supplier.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier already exists.")
    s = Supplier(
        name=req.name, country=req.country, city=req.city,
        latitude=req.latitude, longitude=req.longitude,
        geopolitical_risk=req.geopolitical_risk, climate_risk=req.climate_risk,
        financial_risk=req.financial_risk, logistics_risk=req.logistics_risk,
        overall_risk=(req.geopolitical_risk + req.climate_risk + req.financial_risk + req.logistics_risk) / 4.0
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    
    # Sync to Graph DB
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
    finally:
        graph.close()
        
    return s

@app.post("/api/products")
def create_product(req: ProductCreate, db: Session = Depends(get_db)):
    """
    Registers a new product SKU in the database.
    """
    existing = db.query(Product).filter(Product.sku == req.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists.")
    p = Product(sku=req.sku, name=req.name, description=req.description, base_cost=req.base_cost, selling_price=req.selling_price)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@app.post("/api/routes")
def create_route(req: RouteCreate, db: Session = Depends(get_db)):
    """
    Creates a shipping route connecting two supply chain entities.
    """
    r = ShippingRoute(
        name=req.name, origin_type=req.origin_type, origin_id=req.origin_id,
        dest_type=req.dest_type, dest_id=req.dest_id,
        transport_mode=req.transport_mode, lead_time_days=req.lead_time_days, cost_per_unit=req.cost_per_unit
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    
    # Sync Graph DB
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
    finally:
        graph.close()
        
    return r

@app.post("/api/network/import")
def import_network(req: NetworkImportRequest, db: Session = Depends(get_db)):
    """
    Clears the current supply chain state and loads a new corporate twin network in mass.
    """
    # 1. Clear database
    db.query(Inventory).delete()
    db.query(ShippingRoute).delete()
    db.query(Factory).delete()
    db.query(Warehouse).delete()
    db.query(Customer).delete()
    db.query(Supplier).delete()
    db.query(Product).delete()
    db.query(Port).delete()
    db.execute(product_supplier_association.delete())
    db.commit()
    
    # 2. Load Suppliers
    for s_req in req.suppliers:
        s = Supplier(
            name=s_req.name, country=s_req.country, city=s_req.city,
            latitude=s_req.latitude, longitude=s_req.longitude,
            geopolitical_risk=s_req.geopolitical_risk, climate_risk=s_req.climate_risk,
            financial_risk=s_req.financial_risk, logistics_risk=s_req.logistics_risk,
            overall_risk=(s_req.geopolitical_risk + s_req.climate_risk + s_req.financial_risk + s_req.logistics_risk) / 4.0
        )
        db.add(s)
    db.commit()

    # 3. Load Products
    for p_req in req.products:
        p = Product(sku=p_req.sku, name=p_req.name, description=p_req.description, base_cost=p_req.base_cost, selling_price=p_req.selling_price)
        db.add(p)
    db.commit()

    # 4. Load Routes
    for r_req in req.routes:
        r = ShippingRoute(
            name=r_req.name, origin_type=r_req.origin_type, origin_id=r_req.origin_id,
            dest_type=r_req.dest_type, dest_id=r_req.dest_id,
            transport_mode=r_req.transport_mode, lead_time_days=r_req.lead_time_days, cost_per_unit=r_req.cost_per_unit
        )
        db.add(r)
    db.commit()
    
    # Sync Graph DB
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
    finally:
        graph.close()

    return {
        "status": "Network imported successfully.",
        "suppliers_loaded": len(req.suppliers),
        "products_loaded": len(req.products),
        "routes_loaded": len(req.routes)
    }

@app.get("/api/ports")
def get_ports(db: Session = Depends(get_db)):
    """
    Returns a list of all ports currently in the relational database.
    """
    ports = db.query(Port).all()
    return [{"id": p.id, "name": p.name, "country": p.country} for p in ports]

@app.get("/api/commodities")
def get_commodities(db: Session = Depends(get_db)):
    """
    Returns a list of all unique essential materials (commodities) from the products in the database.
    """
    products = db.query(Product).all()
    commodities = set()
    for p in products:
        if p.essential_materials:
            mats = p.essential_materials.split(",")
            for m in mats:
                if m.strip():
                    commodities.add(m.strip().lower())
    
    # Always include 'oil' as a global logistics commodity
    commodities.add("oil")
    return sorted(list(commodities))

class NetworkGenerateRequest(BaseModel):
    company_name: str

@app.post("/api/network/generate")
def generate_network(req: NetworkGenerateRequest, db: Session = Depends(get_db)):
    """
    Dynamically generates and loads a complete supply chain network for a target company using Gemini-3.1-flash-lite.
    """
    prompt = f"""
    Construct a realistic global supply chain network structure for the company "{req.company_name}".
    
    You must output a JSON object containing:
    1. "suppliers": A list of 3 major suppliers relevant to this company. Each supplier needs:
       - "name": Supplier name (e.g. Foxconn, TSMC, Samsung, BASF, Corning)
       - "country": Country of operation
       - "city": City of operation
       - "latitude": Latitude float coordinate
       - "longitude": Longitude float coordinate
       - "geopolitical_risk": Risk score float (0.0 to 100.0)
       - "climate_risk": Risk score float (0.0 to 100.0)
       - "financial_risk": Risk score float (0.0 to 100.0)
       - "logistics_risk": Risk score float (0.0 to 100.0)
    2. "products": A list of 2 primary products sold by "{req.company_name}". Each product needs:
       - "sku": Product SKU string (e.g. SKU-SAMS-S24)
       - "name": Product name
       - "description": Description of product
       - "base_cost": Float of manufacturing cost (e.g. 350.00)
       - "selling_price": Float of retail price (e.g. 999.00)
       - "essential_materials": A list of 3-4 essential raw materials or components needed for this product (e.g. ["lithium", "semiconductors", "copper", "aluminum"])
       
    Example output JSON structure:
    {{
      "suppliers": [
        {{"name": "TSMC Hsinchu", "country": "Taiwan", "city": "Hsinchu", "latitude": 24.77, "longitude": 120.96, "geopolitical_risk": 85.0, "climate_risk": 35.0, "financial_risk": 10.0, "logistics_risk": 20.0}}
      ],
      "products": [
        {{"sku": "SKU-H100", "name": "H100 GPU", "description": "AI Chip", "base_cost": 3000.0, "selling_price": 25000.0, "essential_materials": ["semiconductors", "copper", "silicon"]}}
      ]
    }}
    
    JSON:
    """
    
    from llm_client import LLMClient
    client = LLMClient()
    
    # 1. Generate JSON structure using Gemini
    generated_data = client.generate_json(prompt, system_instruction="You are a Supply Chain Architecture builder.")
    
    if "error" in generated_data:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {generated_data['error']}")
        
    suppliers_list = generated_data.get("suppliers", [])
    products_list = generated_data.get("products", [])
    
    if not suppliers_list or not products_list:
        raise HTTPException(status_code=500, detail="LLM returned incomplete or empty supply chain data.")

    # 2. Clear current database tables
    db.query(Inventory).delete()
    db.query(ShippingRoute).delete()
    db.query(Factory).delete()
    db.query(Warehouse).delete()
    db.query(Customer).delete()
    db.query(Supplier).delete()
    db.query(Product).delete()
    db.query(Port).delete()
    db.execute(product_supplier_association.delete())
    db.commit()

    # 3. Create Suppliers
    db_suppliers = []
    for s_data in suppliers_list:
        s = Supplier(
            name=s_data["name"], country=s_data["country"], city=s_data.get("city", "HQ"),
            latitude=s_data["latitude"], longitude=s_data["longitude"],
            geopolitical_risk=s_data.get("geopolitical_risk", 20.0),
            climate_risk=s_data.get("climate_risk", 20.0),
            financial_risk=s_data.get("financial_risk", 20.0),
            logistics_risk=s_data.get("logistics_risk", 20.0),
            overall_risk=(s_data.get("geopolitical_risk", 20.0) + s_data.get("climate_risk", 20.0) + s_data.get("financial_risk", 20.0) + s_data.get("logistics_risk", 20.0)) / 4.0
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        db_suppliers.append(s)

    # 4. Create Products
    db_products = []
    for p_data in products_list:
        essential_mats_list = p_data.get("essential_materials", [])
        essential_mats_str = ",".join([m.lower().strip() for m in essential_mats_list if m.strip()])
        p = Product(
            sku=p_data["sku"], name=p_data["name"],
            description=p_data.get("description", ""),
            base_cost=p_data["base_cost"], selling_price=p_data["selling_price"],
            essential_materials=essential_mats_str
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        db_products.append(p)
        
    # Relate generated products to suppliers
    for p in db_products:
        for s in db_suppliers:
            p.suppliers.append(s)
    db.commit()

    # 5. Create default warehouses, factories, ports, customers, routes, and inventories
    # Factories: Create one factory for each supplier located nearby
    factories = []
    for s in db_suppliers:
        f = Factory(
            name=f"{s.name} Production Hub", supplier_id=s.id,
            country=s.country, city=s.city,
            latitude=s.latitude + 0.02, longitude=s.longitude + 0.02,
            capacity_tpd=300.0, operating_cost_per_day=50000.0
        )
        db.add(f)
        db.commit()
        db.refresh(f)
        factories.append(f)

    # Ports: Default regional ports
    ports_seed = [
        Port(name="Shanghai Port", country="China", latitude=30.62, longitude=122.06, delay_days=1.0),
        Port(name="Kaohsiung Port", country="Taiwan", latitude=22.61, longitude=120.27, delay_days=0.5),
        Port(name="Los Angeles Port", country="USA", latitude=33.74, longitude=-118.26, delay_days=2.0),
        Port(name="Rotterdam Port", country="Netherlands", latitude=51.92, longitude=4.47, delay_days=1.2),
    ]
    db_ports = []
    for pt in ports_seed:
        db.add(pt)
        db.commit()
        db.refresh(pt)
        db_ports.append(pt)

    # Warehouses: Default global DCs
    wh_seed = [
        Warehouse(name="North America Logistics DC", country="USA", city="Oakland", latitude=37.80, longitude=-122.27),
        Warehouse(name="European Distribution Hub", country="Germany", city="Frankfurt", latitude=50.11, longitude=8.68),
    ]
    db_whs = []
    for wh in wh_seed:
        db.add(wh)
        db.commit()
        db.refresh(wh)
        db_whs.append(wh)

    # Customers: Default Retailers
    cust_seed = [
        Customer(name=f"{req.company_name} Retail Americas", country="USA", city="San Jose", latitude=37.33, longitude=-121.89, monthly_demand_units=40000.0),
        Customer(name=f"{req.company_name} Retail Europe", country="Germany", city="Berlin", latitude=52.52, longitude=13.40, monthly_demand_units=25000.0),
    ]
    db_custs = []
    for c in cust_seed:
        db.add(c)
        db.commit()
        db.refresh(c)
        db_custs.append(c)

    # 6. Create Inventories for each product at each warehouse so the forecast and charts run correctly
    for p in db_products:
        for wh in db_whs:
            inv = Inventory(
                product_id=p.id, warehouse_id=wh.id,
                current_stock=50000.0, safety_stock=12000.0,
                reorder_point=20000.0, daily_demand=1200.0
            )
            db.add(inv)
    db.commit()

    # 7. Create Shipping Routes connecting them
    # Route 1: Factory to nearest Seaport
    for idx, f in enumerate(factories):
        # Link to first or second port depending on index
        port_target = db_ports[0] if idx % 2 == 0 else db_ports[1]
        r1 = ShippingRoute(
            name=f"{f.name} to Port Transport", origin_type="Factory", origin_id=f.id,
            dest_type="Port", dest_id=port_target.id,
            transport_mode="Road", lead_time_days=0.5, cost_per_unit=0.1
        )
        db.add(r1)
        
        # Route 2: Port to US Seaport (LA) or Rotterdam Seaport
        dest_port = db_ports[2] if idx % 2 == 0 else db_ports[3]
        r2 = ShippingRoute(
            name=f"{port_target.name} to {dest_port.name} Ocean Lane", origin_type="Port", origin_id=port_target.id,
            dest_type="Port", dest_id=dest_port.id,
            transport_mode="Ocean", lead_time_days=15.0, cost_per_unit=1.8
        )
        db.add(r2)
        db.commit() # Commit to generate ID for r2
        
        # Create alternative ocean lane using the other port as origin
        alt_origin_port = db_ports[1] if idx % 2 == 0 else db_ports[0]
        alt_r2 = ShippingRoute(
            name=f"{alt_origin_port.name} to {dest_port.name} Alternative Lane", origin_type="Port", origin_id=alt_origin_port.id,
            dest_type="Port", dest_id=dest_port.id,
            transport_mode="Ocean", lead_time_days=18.0 if idx % 2 == 0 else 20.0, cost_per_unit=2.5 if idx % 2 == 0 else 2.8
        )
        db.add(alt_r2)
        db.commit() # Commit to generate ID for alt_r2
        
        r2.alternative_route_id = alt_r2.id
        db.commit()

        # Route 3: Port to Warehouse
        target_wh = db_whs[0] if idx % 2 == 0 else db_whs[1]
        r3 = ShippingRoute(
            name=f"{dest_port.name} to {target_wh.name} Delivery", origin_type="Port", origin_id=dest_port.id,
            dest_type="Warehouse", dest_id=target_wh.id,
            transport_mode="Road", lead_time_days=1.5, cost_per_unit=0.3
        )
        db.add(r3)

        # Route 4: Warehouse to Customer
        target_cust = db_custs[0] if idx % 2 == 0 else db_custs[1]
        r4 = ShippingRoute(
            name=f"{target_wh.name} to {target_cust.name} Fulfillment", origin_type="Warehouse", origin_id=target_wh.id,
            dest_type="Customer", dest_id=target_cust.id,
            transport_mode="Road", lead_time_days=0.5, cost_per_unit=0.2
        )
        db.add(r4)

    db.commit()

    # 8. Re-sync Neo4j/NetworkX graph
    graph = Neo4jService()
    try:
        graph.sync_from_relational_db(db)
    finally:
        graph.close()

    return {
        "status": f"AI constructed supply chain for {req.company_name} successfully.",
        "suppliers_generated": [s.name for s in db_suppliers],
        "products_generated": [p.name for p in db_products]
    }

if __name__ == "__main__":
    import uvicorn
    # Read port from env or default to 8001
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
