# SupplyTwin: Global Supply Chain Digital Twin AI

SupplyTwin is an AI-powered global supply chain digital twin application. It integrates relational modeling (SQLite/PostgreSQL) and graph databases (Neo4j/NetworkX) with a Vite-based React frontend to model, visualize, simulate, and optimize complex corporate supply chain networks.

Through multi-agent orchestration powered by Google Gemini, the platform enables real-time risk assessment, automated news ingestion, interactive dependency tracking, seaport closure and commodity cost spike simulations, and procurement optimization.

---

## 🌟 Key Modules

### 1. Control Tower (Dashboard)
- Displays critical metrics: Total Suppliers, At-Risk Suppliers, Active Disruptions, Average Stockout Probability, and Expected Revenue Impact.
- Interactive global map showcasing supplier geographic distribution and live weather conditions.
- Real-time KPI indicators reflecting active geopolitical or environmental disruptions.

### 2. Knowledge Graph (Cytoscape.js)
- Renders an interactive multi-node dependency graph (Suppliers, Factories, Ports, Warehouses, Customers, and Products).
- Features **BFS Downstream Blast Radius Tracing**: click any node to immediately see all downstream entities and logistics paths affected by a failure.

### 3. Event Monitor
- Ingests raw news or system alerts manually or automatically from public channels (via GDELT API).
- Employs an **Event Intelligence Agent** to parse headlines, extract locations/severity, write active disruptions, and automatically recalculate risk metrics for regional suppliers.

### 4. Scenario Simulator
- **Seaport Closure Engine**: Evaluates the cost, delays, and inventory depletion timelines of port shutdowns. Dynamically recommends alternative routes, calculates rerouting delays, and maps safety stock status.
- **Commodity Price Spike Engine**: Dynamically calculates production cost inflation, margin absorption, and annual financial loss when raw materials (e.g., Lithium, Copper, Crude Oil, Semiconductors) rise. Calculations are grounded in actual product bill-of-materials and warehouse demand volumes.

### 5. Procurement Copilot
- Locates alternative suppliers for specific product SKUs using risk-versus-cost efficiency ratings.
- Generates tailored negotiation strategies, target price points, and talking points using Gemini AI.

### 6. Executive Chat
- A natural-language interface allowing leadership to query their supply chain.
- An **Executive Advisor Agent** parses the intent, routes tasks to sub-agents (Risk, Forecast, Logistics, Finance, Simulation), and synthesizes multi-dimensional executive briefings.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database ORM**: SQLAlchemy (supporting PostgreSQL & SQLite)
- **Graph Databases**: Neo4j (Graph Database Driver) with NetworkX (in-memory graph fallback)
- **LLM / Agent Client**: Google Generative AI (Gemini 3.5 Flash & 3.1 Flash-Lite)
- **Data Analytics**: Pandas, Scikit-Learn

### Frontend
- **Framework**: React 18, TypeScript, Vite
- **Graph Visualization**: Cytoscape.js
- **Charts**: Recharts
- **Styling**: Vanilla CSS (Premium glassmorphism dark-theme layout)
- **Icons**: Lucide React

---

## ⚙️ Configuration & Environment Setup

### Backend Environment (`backend/.env`)
Create a `.env` file inside the `backend/` directory with the following keys:
```env
# Server Port (optional, defaults to 8001)
PORT=8001

# Database (defaults to SQLite if left empty)
DATABASE_URL=sqlite:///./supply_chain.db

# Neo4j Graph DB (falls back to in-memory NetworkX if left empty)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# Gemini LLM API Key (Required for AI features)
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🚀 Setup & Launch Instructions

### 1. Initialize the Relational Database
The database automatically drops outdated tables and seeds default data (like TSMC, CATL, ASML, iPhone 17, and EV Battery networks) upon server start or by executing the database script directly.

```bash
cd backend
# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run initial seed
python database.py
```

### 2. Start the Backend Server
Run the FastAPI application locally on port 8001:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Start the Frontend Application
In a separate terminal, install the frontend packages and launch the Vite development server:
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser to interact with the SupplyTwin Digital Twin.
