import os
import math
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from datetime import datetime

# Connection setup: Postgres if DATABASE_URL is defined, else local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Many-to-many relationship helper table for Products and Suppliers
product_supplier_association = Table(
    'product_supplier',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('supplier_id', Integer, ForeignKey('suppliers.id'), primary_key=True)
)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    base_cost = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    essential_materials = Column(String, default="oil,copper")
    
    # Relationships
    suppliers = relationship("Supplier", secondary=product_supplier_association, back_populates="products")
    inventories = relationship("Inventory", back_populates="product")

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    country = Column(String, nullable=False)
    city = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Risk Dimensions (0 - 100)
    geopolitical_risk = Column(Float, default=10.0)
    climate_risk = Column(Float, default=10.0)
    financial_risk = Column(Float, default=10.0)
    logistics_risk = Column(Float, default=10.0)
    overall_risk = Column(Float, default=10.0)
    
    status = Column(String, default="Active")  # Active, Disrupted, Suspended
    
    # Relationships
    products = relationship("Product", secondary=product_supplier_association, back_populates="suppliers")
    factories = relationship("Factory", back_populates="supplier")

class Factory(Base):
    __tablename__ = "factories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True) # None means internally owned
    country = Column(String, nullable=False)
    city = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_tpd = Column(Float, default=100.0) # Tons per day capacity
    operating_cost_per_day = Column(Float, default=5000.0)
    status = Column(String, default="Active")

    # Relationships
    supplier = relationship("Supplier", back_populates="factories")

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    country = Column(String, nullable=False)
    city = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_units = Column(Float, default=100000.0)
    
    # Relationships
    inventories = relationship("Inventory", back_populates="warehouse")

class Port(Base):
    __tablename__ = "ports"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    country = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    delay_days = Column(Float, default=0.0) # Average delay in days due to congestion
    status = Column(String, default="Open")  # Open, Congested, Closed

class ShippingRoute(Base):
    __tablename__ = "shipping_routes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    origin_type = Column(String, nullable=False)  # Supplier, Factory, Port, Warehouse
    origin_id = Column(Integer, nullable=False)
    dest_type = Column(String, nullable=False)    # Factory, Port, Warehouse, Customer
    dest_id = Column(Integer, nullable=False)
    transport_mode = Column(String, default="Ocean") # Ocean, Air, Rail, Road
    lead_time_days = Column(Float, default=5.0)
    cost_per_unit = Column(Float, default=1.0)
    status = Column(String, default="Active") # Active, Blocked, Congested
    alternative_route_id = Column(Integer, nullable=True) # Points to another route

class Inventory(Base):
    __tablename__ = "inventories"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    current_stock = Column(Float, default=1000.0)
    safety_stock = Column(Float, default=200.0)
    reorder_point = Column(Float, default=400.0)
    daily_demand = Column(Float, default=50.0)
    
    # Relationships
    product = relationship("Product", back_populates="inventories")
    warehouse = relationship("Warehouse", back_populates="inventories")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    country = Column(String, nullable=False)
    city = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    monthly_demand_units = Column(Float, default=1000.0)

class CountryRisk(Base):
    __tablename__ = "country_risks"
    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, unique=True, index=True)
    geopolitical_risk = Column(Float, default=10.0)
    climate_risk = Column(Float, default=10.0)
    overall_risk = Column(Float, default=10.0)

class ActiveDisruption(Base):
    __tablename__ = "active_disruptions"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False) # Typhoon, War, Tariff, Strike, etc.
    location = Column(String, nullable=False)
    severity = Column(String, nullable=False) # Low, Medium, High, Critical
    expected_duration_days = Column(Integer, default=5)
    impact_description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Integer, default=1) # 1 = Active, 0 = Resolved

# Database initialization & seeding helper
def seed_data(db):
    # 1. Add Country Risks
    country_risks = [
        CountryRisk(country="Taiwan", geopolitical_risk=85.0, climate_risk=45.0, overall_risk=65.0),
        CountryRisk(country="China", geopolitical_risk=70.0, climate_risk=40.0, overall_risk=55.0),
        CountryRisk(country="USA", geopolitical_risk=15.0, climate_risk=30.0, overall_risk=22.0),
        CountryRisk(country="Netherlands", geopolitical_risk=12.0, climate_risk=15.0, overall_risk=13.0),
        CountryRisk(country="South Korea", geopolitical_risk=35.0, climate_risk=25.0, overall_risk=30.0),
        CountryRisk(country="Japan", geopolitical_risk=20.0, climate_risk=50.0, overall_risk=35.0),
        CountryRisk(country="Germany", geopolitical_risk=10.0, climate_risk=20.0, overall_risk=15.0),
        CountryRisk(country="India", geopolitical_risk=40.0, climate_risk=60.0, overall_risk=50.0),
    ]
    for cr in country_risks:
        if not db.query(CountryRisk).filter(CountryRisk.country == cr.country).first():
            db.add(cr)

    # 2. Add Suppliers
    suppliers_data = [
        Supplier(name="TSMC", country="Taiwan", city="Hsinchu", latitude=24.77, longitude=120.96, geopolitical_risk=85.0, climate_risk=40.0, financial_risk=10.0, logistics_risk=30.0, overall_risk=68.0, status="Active"),
        Supplier(name="CATL", country="China", city="Ningde", latitude=26.66, longitude=119.54, geopolitical_risk=70.0, climate_risk=45.0, financial_risk=15.0, logistics_risk=35.0, overall_risk=59.0, status="Active"),
        Supplier(name="ASML", country="Netherlands", city="Veldhoven", latitude=51.41, longitude=5.40, geopolitical_risk=15.0, climate_risk=15.0, financial_risk=5.0, logistics_risk=20.0, overall_risk=14.0, status="Active"),
        Supplier(name="LG Energy Solution", country="South Korea", city="Seoul", latitude=37.56, longitude=126.97, geopolitical_risk=35.0, climate_risk=20.0, financial_risk=20.0, logistics_risk=25.0, overall_risk=27.0, status="Active"),
        Supplier(name="Panasonic", country="Japan", city="Osaka", latitude=34.69, longitude=135.50, geopolitical_risk=20.0, climate_risk=45.0, financial_risk=15.0, logistics_risk=25.0, overall_risk=29.0, status="Active"),
        Supplier(name="Samsung Foundry", country="South Korea", city="Suwon", latitude=37.26, longitude=127.02, geopolitical_risk=35.0, climate_risk=25.0, financial_risk=10.0, logistics_risk=25.0, overall_risk=26.0, status="Active"),
    ]
    
    suppliers = {}
    for s_data in suppliers_data:
        existing = db.query(Supplier).filter(Supplier.name == s_data.name).first()
        if not existing:
            db.add(s_data)
            suppliers[s_data.name] = s_data
        else:
            suppliers[s_data.name] = existing

    # 3. Add Products
    products_data = [
        Product(sku="PROD-IPH17", name="iPhone 17 Pro", description="Flagship next-gen smartphone", base_cost=450.0, selling_price=1199.0, essential_materials="semiconductors,cobalt,aluminum,copper"),
        Product(sku="PROD-MACM4", name="MacBook Pro M4", description="Professional high-performance laptop", base_cost=850.0, selling_price=1999.0, essential_materials="semiconductors,aluminum,copper"),
        Product(sku="PROD-EVBAT", name="Silicon Anode EV Battery", description="Next-generation high density EV cell pack", base_cost=3200.0, selling_price=5500.0, essential_materials="lithium,graphite,silicon,copper"),
    ]

    products = {}
    for p_data in products_data:
        existing = db.query(Product).filter(Product.sku == p_data.sku).first()
        if not existing:
            db.add(p_data)
            products[p_data.sku] = p_data
        else:
            products[p_data.sku] = existing

    db.commit()

    # Relate Products to Suppliers (Many-to-Many)
    # TSMC and ASML are linked to iPhone 17 and MacBook Pro M4
    # CATL is linked to EV Battery
    if suppliers["TSMC"] not in products["PROD-IPH17"].suppliers:
        products["PROD-IPH17"].suppliers.append(suppliers["TSMC"])
    if suppliers["ASML"] not in products["PROD-IPH17"].suppliers:
        products["PROD-IPH17"].suppliers.append(suppliers["ASML"])
        
    if suppliers["TSMC"] not in products["PROD-MACM4"].suppliers:
        products["PROD-MACM4"].suppliers.append(suppliers["TSMC"])
    if suppliers["ASML"] not in products["PROD-MACM4"].suppliers:
        products["PROD-MACM4"].suppliers.append(suppliers["ASML"])
        
    if suppliers["CATL"] not in products["PROD-EVBAT"].suppliers:
        products["PROD-EVBAT"].suppliers.append(suppliers["CATL"])
        
    db.commit()

    # 4. Add Factories
    factories_data = [
        Factory(name="TSMC Fab 18", supplier_id=suppliers["TSMC"].id, country="Taiwan", city="Tainan", latitude=23.01, longitude=120.21, capacity_tpd=250.0, operating_cost_per_day=45000.0, status="Active"),
        Factory(name="Shanghai Assembly Plant", supplier_id=None, country="China", city="Shanghai", latitude=31.23, longitude=121.47, capacity_tpd=500.0, operating_cost_per_day=75000.0, status="Active"), # Internally owned factory
        Factory(name="CATL GigaFactory", supplier_id=suppliers["CATL"].id, country="China", city="Ningde", latitude=26.65, longitude=119.53, capacity_tpd=350.0, operating_cost_per_day=55000.0, status="Active"),
        Factory(name="Eindhoven Litho Assembly", supplier_id=suppliers["ASML"].id, country="Netherlands", city="Eindhoven", latitude=51.44, longitude=5.48, capacity_tpd=50.0, operating_cost_per_day=120000.0, status="Active"),
    ]
    
    factories = {}
    for f_data in factories_data:
        existing = db.query(Factory).filter(Factory.name == f_data.name).first()
        if not existing:
            db.add(f_data)
            factories[f_data.name] = f_data
        else:
            factories[f_data.name] = existing

    # 5. Add Warehouses
    warehouses_data = [
        Warehouse(name="North America West Distribution Center", country="USA", city="Oakland", latitude=37.80, longitude=-122.27, capacity_units=500000.0),
        Warehouse(name="European Central Hub", country="Germany", city="Frankfurt", latitude=50.11, longitude=8.68, capacity_units=400000.0),
        Warehouse(name="Asia Pacific Logistics Center", country="Singapore", city="Singapore", latitude=1.35, longitude=103.81, capacity_units=600000.0),
    ]

    warehouses = {}
    for w_data in warehouses_data:
        existing = db.query(Warehouse).filter(Warehouse.name == w_data.name).first()
        if not existing:
            db.add(w_data)
            warehouses[w_data.name] = w_data
        else:
            warehouses[w_data.name] = existing

    # 6. Add Ports
    ports_data = [
        Port(name="Shanghai Port", country="China", latitude=30.62, longitude=122.06, delay_days=1.2, status="Open"),
        Port(name="Ningbo Port", country="China", latitude=29.86, longitude=121.54, delay_days=0.8, status="Open"),
        Port(name="Kaohsiung Port", country="Taiwan", latitude=22.61, longitude=120.27, delay_days=0.5, status="Open"),
        Port(name="Rotterdam Port", country="Netherlands", latitude=51.92, longitude=4.47, delay_days=1.5, status="Open"),
        Port(name="Los Angeles Port", country="USA", latitude=33.74, longitude=-118.26, delay_days=2.1, status="Open"),
        Port(name="Singapore Port", country="Singapore", latitude=1.26, longitude=103.83, delay_days=0.4, status="Open"),
    ]

    ports = {}
    for pt_data in ports_data:
        existing = db.query(Port).filter(Port.name == pt_data.name).first()
        if not existing:
            db.add(pt_data)
            ports[pt_data.name] = pt_data
        else:
            ports[pt_data.name] = existing

    # 7. Add Customers
    customers_data = [
        Customer(name="Apple Retail US", country="USA", city="Cupertino", latitude=37.33, longitude=-122.03, monthly_demand_units=50000.0),
        Customer(name="Apple Retail EU", country="Germany", city="Munich", latitude=48.13, longitude=11.58, monthly_demand_units=30000.0),
        Customer(name="Tesla US Factory", country="USA", city="Austin", latitude=30.22, longitude=-97.62, monthly_demand_units=5000.0),
    ]

    customers = {}
    for c_data in customers_data:
        existing = db.query(Customer).filter(Customer.name == c_data.name).first()
        if not existing:
            db.add(c_data)
            customers[c_data.name] = c_data
        else:
            customers[c_data.name] = existing

    db.commit()

    # 8. Add Inventories
    # Seed inventory records for products at warehouses
    inventories_data = [
        # iPhone at NA Hub
        Inventory(product_id=products["PROD-IPH17"].id, warehouse_id=warehouses["North America West Distribution Center"].id, current_stock=75000.0, safety_stock=15000.0, reorder_point=25000.0, daily_demand=1500.0),
        # iPhone at EU Hub
        Inventory(product_id=products["PROD-IPH17"].id, warehouse_id=warehouses["European Central Hub"].id, current_stock=42000.0, safety_stock=10000.0, reorder_point=18000.0, daily_demand=900.0),
        # MacBook at NA Hub
        Inventory(product_id=products["PROD-MACM4"].id, warehouse_id=warehouses["North America West Distribution Center"].id, current_stock=28000.0, safety_stock=8000.0, reorder_point=12000.0, daily_demand=600.0),
        # MacBook at AP Hub
        Inventory(product_id=products["PROD-MACM4"].id, warehouse_id=warehouses["Asia Pacific Logistics Center"].id, current_stock=35000.0, safety_stock=9000.0, reorder_point=15000.0, daily_demand=700.0),
        # EV Battery at AP Hub
        Inventory(product_id=products["PROD-EVBAT"].id, warehouse_id=warehouses["Asia Pacific Logistics Center"].id, current_stock=12000.0, safety_stock=3000.0, reorder_point=5000.0, daily_demand=250.0),
    ]

    for inv in inventories_data:
        existing = db.query(Inventory).filter(
            Inventory.product_id == inv.product_id,
            Inventory.warehouse_id == inv.warehouse_id
        ).first()
        if not existing:
            db.add(inv)

    # 9. Add Shipping Routes
    # Route mappings: Supplier/Factory -> Port -> Port -> Warehouse -> Customer
    routes_data = [
        # TSMC Fab 18 -> Kaohsiung Port (Road, 0.5 days)
        ShippingRoute(name="TSMC Fab to Kaohsiung Port", origin_type="Factory", origin_id=factories["TSMC Fab 18"].id, dest_type="Port", dest_id=ports["Kaohsiung Port"].id, transport_mode="Road", lead_time_days=0.5, cost_per_unit=0.1),
        
        # Kaohsiung Port -> Los Angeles Port (Ocean, 14 days)
        ShippingRoute(name="Kaohsiung to Los Angeles (Ocean Route)", origin_type="Port", origin_id=ports["Kaohsiung Port"].id, dest_type="Port", dest_id=ports["Los Angeles Port"].id, transport_mode="Ocean", lead_time_days=14.0, cost_per_unit=1.2),
        
        # Los Angeles Port -> NA Distribution Center (Road, 1 day)
        ShippingRoute(name="LA Port to NA DC", origin_type="Port", origin_id=ports["Los Angeles Port"].id, dest_type="Warehouse", dest_id=warehouses["North America West Distribution Center"].id, transport_mode="Road", lead_time_days=1.0, cost_per_unit=0.3),
        
        # NA Distribution Center -> Apple Retail US (Road, 0.5 days)
        ShippingRoute(name="NA DC to Retail US", origin_type="Warehouse", origin_id=warehouses["North America West Distribution Center"].id, dest_type="Customer", dest_id=customers["Apple Retail US"].id, transport_mode="Road", lead_time_days=0.5, cost_per_unit=0.2),

        # Shanghai Assembly -> Shanghai Port (Road, 0.5 days)
        ShippingRoute(name="Shanghai Plant to Port", origin_type="Factory", origin_id=factories["Shanghai Assembly Plant"].id, dest_type="Port", dest_id=ports["Shanghai Port"].id, transport_mode="Road", lead_time_days=0.5, cost_per_unit=0.08),
        
        # Shanghai Port -> Los Angeles Port (Ocean, 15 days)
        ShippingRoute(name="Shanghai to LA (Suez/Pacific)", origin_type="Port", origin_id=ports["Shanghai Port"].id, dest_type="Port", dest_id=ports["Los Angeles Port"].id, transport_mode="Ocean", lead_time_days=15.0, cost_per_unit=1.5),

        # Shanghai Port -> Rotterdam Port (Ocean Suez, 24 days) - Alternative via Cape
        ShippingRoute(name="Shanghai to Rotterdam (Suez Canal)", origin_type="Port", origin_id=ports["Shanghai Port"].id, dest_type="Port", dest_id=ports["Rotterdam Port"].id, transport_mode="Ocean", lead_time_days=24.0, cost_per_unit=2.0, alternative_route_id=None), # will update later
        
        # Shanghai Port -> Rotterdam Port (Ocean Cape of Good Hope, 36 days)
        ShippingRoute(name="Shanghai to Rotterdam (Cape Route)", origin_type="Port", origin_id=ports["Shanghai Port"].id, dest_type="Port", dest_id=ports["Rotterdam Port"].id, transport_mode="Ocean", lead_time_days=36.0, cost_per_unit=3.2),

        # Rotterdam Port -> European Central Hub (Road, 1.5 days)
        ShippingRoute(name="Rotterdam to EU Hub", origin_type="Port", origin_id=ports["Rotterdam Port"].id, dest_type="Warehouse", dest_id=warehouses["European Central Hub"].id, transport_mode="Road", lead_time_days=1.5, cost_per_unit=0.4),

        # European Central Hub -> Apple Retail EU (Road, 0.5 days)
        ShippingRoute(name="EU Hub to Retail EU", origin_type="Warehouse", origin_id=warehouses["European Central Hub"].id, dest_type="Customer", dest_id=customers["Apple Retail EU"].id, transport_mode="Road", lead_time_days=0.5, cost_per_unit=0.25),

        # CATL Factory -> Ningbo Port (Road, 0.8 days)
        ShippingRoute(name="CATL Factory to Ningbo Port", origin_type="Factory", origin_id=factories["CATL GigaFactory"].id, dest_type="Port", dest_id=ports["Ningbo Port"].id, transport_mode="Road", lead_time_days=0.8, cost_per_unit=0.15),

        # Ningbo Port -> Los Angeles Port (Ocean, 14 days)
        ShippingRoute(name="Ningbo to LA", origin_type="Port", origin_id=ports["Ningbo Port"].id, dest_type="Port", dest_id=ports["Los Angeles Port"].id, transport_mode="Ocean", lead_time_days=14.0, cost_per_unit=1.4),
        
        # Los Angeles Port -> Tesla Factory US (Road, 1.5 days)
        ShippingRoute(name="LA Port to Tesla Austin", origin_type="Port", origin_id=ports["Los Angeles Port"].id, dest_type="Customer", dest_id=customers["Tesla US Factory"].id, transport_mode="Road", lead_time_days=1.5, cost_per_unit=0.9),
    ]

    for r in routes_data:
        existing = db.query(ShippingRoute).filter(
            ShippingRoute.name == r.name,
            ShippingRoute.origin_type == r.origin_type,
            ShippingRoute.origin_id == r.origin_id,
            ShippingRoute.dest_type == r.dest_type,
            ShippingRoute.dest_id == r.dest_id
        ).first()
        if not existing:
            db.add(r)
            
    db.commit()

    # Link alternative routes
    suez = db.query(ShippingRoute).filter(ShippingRoute.name == "Shanghai to Rotterdam (Suez Canal)").first()
    cape = db.query(ShippingRoute).filter(ShippingRoute.name == "Shanghai to Rotterdam (Cape Route)").first()
    if suez and cape and suez.alternative_route_id is None:
        suez.alternative_route_id = cape.id
        db.commit()

def init_db():
    # Drop all tables first to handle schema updates/migrations and reset cleanly
    print("Dropping all tables and rebuilding schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Resetting database to default seeded data on server startup...")
        seed_data(db)
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded successfully.")
