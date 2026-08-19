import os
import logging
from neo4j import GraphDatabase
import networkx as nx

logger = logging.getLogger(__name__)

class Neo4jService:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "")
        self.user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.driver = None
        self.use_fallback = True
        
        # Fallback NetworkX graph
        self.nx_graph = nx.DiGraph()

        if self.uri and self.user and self.password:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                # Test connection
                self.driver.verify_connectivity()
                self.use_fallback = False
                logger.info("Successfully connected to Neo4j database.")
                print("Successfully connected to Neo4j database.")
            except Exception as e:
                logger.warning(f"Failed to connect to Neo4j at {self.uri}. Falling back to NetworkX. Error: {e}")
                print(f"Failed to connect to Neo4j. Falling back to in-memory NetworkX graph. Error: {e}")
        else:
            logger.info("Neo4j credentials not provided. Using in-memory NetworkX fallback.")
            print("Neo4j credentials not provided. Using in-memory NetworkX fallback.")

    def close(self):
        if self.driver:
            self.driver.close()

    def sync_from_relational_db(self, db):
        """
        Pulls nodes and links from PostgreSQL/SQLite and populates the graph database.
        """
        from database import Supplier, Factory, Warehouse, Port, Customer, ShippingRoute, Product
        
        # Fetch entities
        suppliers = db.query(Supplier).all()
        factories = db.query(Factory).all()
        warehouses = db.query(Warehouse).all()
        ports = db.query(Port).all()
        customers = db.query(Customer).all()
        products = db.query(Product).all()
        routes = db.query(ShippingRoute).all()

        if not self.use_fallback:
            # Neo4j implementation
            with self.driver.session() as session:
                # 1. Clear database
                session.run("MATCH (n) DETACH DELETE n")
                
                # 2. Add nodes
                for s in suppliers:
                    session.run(
                        "CREATE (n:Supplier {id: $id, name: $name, country: $country, risk: $risk, latitude: $lat, longitude: $lng})",
                        id=f"supplier_{s.id}", name=s.name, country=s.country, risk=s.overall_risk, lat=s.latitude, lng=s.longitude
                    )
                for f in factories:
                    session.run(
                        "CREATE (n:Factory {id: $id, name: $name, country: $country, capacity: $capacity, latitude: $lat, longitude: $lng})",
                        id=f"factory_{f.id}", name=f.name, country=f.country, capacity=f.capacity_tpd, lat=f.latitude, lng=f.longitude
                    )
                for w in warehouses:
                    session.run(
                        "CREATE (n:Warehouse {id: $id, name: $name, country: $country, latitude: $lat, longitude: $lng})",
                        id=f"warehouse_{w.id}", name=w.name, country=w.country, lat=w.latitude, lng=w.longitude
                    )
                for p_node in ports:
                    session.run(
                        "CREATE (n:Port {id: $id, name: $name, country: $country, latitude: $lat, longitude: $lng, status: $status})",
                        id=f"port_{p_node.id}", name=p_node.name, country=p_node.country, lat=p_node.latitude, lng=p_node.longitude, status=p_node.status
                    )
                for c in customers:
                    session.run(
                        "CREATE (n:Customer {id: $id, name: $name, country: $country, latitude: $lat, longitude: $lng})",
                        id=f"customer_{c.id}", name=c.name, country=c.country, lat=c.latitude, lng=c.longitude
                    )
                for prod in products:
                    session.run(
                        "CREATE (n:Product {id: $id, name: $name, sku: $sku, cost: $cost})",
                        id=f"product_{prod.id}", name=prod.name, sku=prod.sku, cost=prod.base_cost
                    )
                
                # 3. Create relationship edges
                # Product-Supplier many-to-many
                for prod in products:
                    for s in prod.suppliers:
                        session.run(
                            "MATCH (a:Product {sku: $sku}), (b:Supplier {name: $sname}) CREATE (b)-[:SUPPLIES]->(a)",
                            sku=prod.sku, sname=s.name
                        )
                
                # Supplier-Factory relationship
                for f in factories:
                    if f.supplier_id:
                        session.run(
                            "MATCH (a:Supplier {id: $sid}), (b:Factory {id: $fid}) CREATE (a)-[:OWNS]->(b)",
                            sid=f"supplier_{f.supplier_id}", fid=f"factory_{f.id}"
                        )
                
                # Shipping Routes
                for r in routes:
                    orig_id_str = f"{r.origin_type.lower()}_{r.origin_id}"
                    dest_id_str = f"{r.dest_type.lower()}_{r.dest_id}"
                    session.run(
                        """
                        MATCH (a {id: $orig_id}), (b {id: $dest_id}) 
                        CREATE (a)-[:SHIPS_TO {id: $route_id, mode: $mode, lead_time: $lead_time, cost: $cost, status: $status}]->(b)
                        """,
                        orig_id=orig_id_str, dest_id=dest_id_str, route_id=r.id,
                        mode=r.transport_mode, lead_time=r.lead_time_days, cost=r.cost_per_unit, status=r.status
                    )
            logger.info("Neo4j database synced successfully.")
            
        else:
            # NetworkX fallback implementation
            self.nx_graph.clear()
            
            # 1. Add nodes
            for s in suppliers:
                self.nx_graph.add_node(f"supplier_{s.id}", type="Supplier", name=s.name, country=s.country, risk=s.overall_risk, latitude=s.latitude, longitude=s.longitude)
            for f in factories:
                self.nx_graph.add_node(f"factory_{f.id}", type="Factory", name=f.name, country=f.country, capacity=f.capacity_tpd, latitude=f.latitude, longitude=f.longitude)
            for w in warehouses:
                self.nx_graph.add_node(f"warehouse_{w.id}", type="Warehouse", name=w.name, country=w.country, latitude=w.latitude, longitude=w.longitude)
            for p_node in ports:
                self.nx_graph.add_node(f"port_{p_node.id}", type="Port", name=p_node.name, country=p_node.country, latitude=p_node.latitude, longitude=p_node.longitude, status=p_node.status)
            for c in customers:
                self.nx_graph.add_node(f"customer_{c.id}", type="Customer", name=c.name, country=c.country, latitude=c.latitude, longitude=c.longitude)
            for prod in products:
                self.nx_graph.add_node(f"product_{prod.id}", type="Product", name=prod.name, sku=prod.sku, cost=prod.base_cost)
                
            # 2. Add Edges
            for prod in products:
                for s in prod.suppliers:
                    self.nx_graph.add_edge(f"supplier_{s.id}", f"product_{prod.id}", rel_type="SUPPLIES")
            for f in factories:
                if f.supplier_id:
                    self.nx_graph.add_edge(f"supplier_{f.supplier_id}", f"factory_{f.id}", rel_type="OWNS")
            for r in routes:
                orig_id_str = f"{r.origin_type.lower()}_{r.origin_id}"
                dest_id_str = f"{r.dest_type.lower()}_{r.dest_id}"
                if self.nx_graph.has_node(orig_id_str) and self.nx_graph.has_node(dest_id_str):
                    self.nx_graph.add_edge(
                        orig_id_str, dest_id_str, 
                        rel_type="SHIPS_TO", id=r.id, mode=r.transport_mode, 
                        lead_time=r.lead_time_days, cost=r.cost_per_unit, status=r.status
                    )
            logger.info("NetworkX in-memory database synced successfully.")

    def get_graph_data(self):
        """
        Returns all nodes and links for dashboard visualization.
        """
        if not self.use_fallback:
            nodes = []
            links = []
            with self.driver.session() as session:
                result_nodes = session.run("MATCH (n) RETURN n, labels(n)[0] as label")
                for record in result_nodes:
                    node_properties = dict(record["n"])
                    node_properties["id"] = record["n"].element_id if "id" not in node_properties else node_properties["id"]
                    node_properties["label"] = record["label"]
                    nodes.append(node_properties)
                
                result_rels = session.run("MATCH (a)-[r]->(b) RETURN a.id as source, b.id as target, type(r) as type, r")
                for record in result_rels:
                    rel_properties = dict(record["r"])
                    rel_properties["source"] = record["source"]
                    rel_properties["target"] = record["target"]
                    rel_properties["type"] = record["type"]
                    links.append(rel_properties)
            return {"nodes": nodes, "links": links}
        else:
            nodes = []
            links = []
            for n_id, n_data in self.nx_graph.nodes(data=True):
                node_item = dict(n_data)
                node_item["id"] = n_id
                node_item["label"] = n_data.get("type", "Unknown")
                nodes.append(node_item)
                
            for u, v, e_data in self.nx_graph.edges(data=True):
                edge_item = dict(e_data)
                edge_item["source"] = u
                edge_item["target"] = v
                edge_item["type"] = e_data.get("rel_type", "SHIPS_TO")
                links.append(edge_item)
            return {"nodes": nodes, "links": links}

    def get_blast_radius(self, node_id, node_type):
        """
        Returns downstream nodes impacted by a failure at node_id.
        In a DiGraph, these are all nodes reachable from the target node.
        """
        target_id = f"{node_type.lower()}_{node_id}" if "_" not in str(node_id) else str(node_id)
        
        if not self.use_fallback:
            with self.driver.session() as session:
                query = """
                MATCH (start {id: $target_id})
                CALL apoc.path.subgraphAll(start, {relationshipFilter: "SHIPS_TO>|OWNS>|SUPPLIES>", maxLevel: 10})
                YIELD nodes, relationships
                RETURN [n in nodes | {id: n.id, name: n.name, label: labels(n)[0]}] as affected_nodes
                """
                # Check if APOC is installed, fallback if not
                try:
                    result = session.run(query, target_id=target_id)
                    record = result.single()
                    if record:
                        return record["affected_nodes"]
                except Exception:
                    # fallback cypher path traversal without APOC
                    query_basic = """
                    MATCH (start {id: $target_id})-[r:SHIPS_TO|OWNS|SUPPLIES*0..6]->(downstream)
                    RETURN DISTINCT downstream.id as id, downstream.name as name, labels(downstream)[0] as label
                    """
                    result = session.run(query_basic, target_id=target_id)
                    return [{"id": r["id"], "name": r["name"], "label": r["label"]} for r in result]
            return []
        else:
            if not self.nx_graph.has_node(target_id):
                return []
            
            # Use NetworkX DFS/BFS to find all reachable downstream nodes
            descendants = nx.descendants(self.nx_graph, target_id)
            affected = []
            
            # Include start node
            start_data = self.nx_graph.nodes[target_id]
            affected.append({
                "id": target_id, 
                "name": start_data.get("name", target_id), 
                "label": start_data.get("type", "Unknown")
            })
            
            for desc in descendants:
                node_data = self.nx_graph.nodes[desc]
                affected.append({
                    "id": desc,
                    "name": node_data.get("name", desc),
                    "label": node_data.get("type", "Unknown")
                })
            return affected
