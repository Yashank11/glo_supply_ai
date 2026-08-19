import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Play, TrendingUp, Ship, DollarSign, Clock, ShieldAlert } from 'lucide-react';

export default function ScenarioSimulator() {
  const [activeTab, setActiveTab] = useState<'port' | 'commodity'>('port');
  
  // Port closure inputs
  const [portName, setPortName] = useState('Shanghai Port');
  const [duration, setDuration] = useState(10);
  const [portResult, setPortResult] = useState<any>(null);
  
  // Commodity inputs
  const [commodity, setCommodity] = useState('lithium');
  const [priceSpike, setPriceSpike] = useState(30);
  const [commodityResult, setCommodityResult] = useState<any>(null);
  
  const [ports, setPorts] = useState<any[]>([]);
  const [commodities, setCommodities] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadDropdownData = async () => {
      try {
        const portsRes = await fetch('http://localhost:8001/api/ports');
        const portsData = await portsRes.json();
        setPorts(portsData);
        if (portsData.length > 0) {
          setPortName(portsData[0].name);
        }
        
        const commsRes = await fetch('http://localhost:8001/api/commodities');
        const commsData = await commsRes.json();
        setCommodities(commsData);
        if (commsData.length > 0) {
          setCommodity(commsData[0]);
        }
      } catch (err) {
        console.error('Failed to fetch dropdown data:', err);
      }
    };
    loadDropdownData();
  }, []);

  const runPortSimulation = async () => {
    setLoading(true);
    setPortResult(null);
    try {
      const res = await fetch('http://localhost:8001/api/simulate/port', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port_name: portName, duration_days: duration })
      });
      const data = await res.json();
      setPortResult(data);
    } catch (err) {
      console.error('Error running port simulation:', err);
    } finally {
      setLoading(false);
    }
  };

  const runCommoditySimulation = async () => {
    setLoading(true);
    setCommodityResult(null);
    try {
      const res = await fetch('http://localhost:8001/api/simulate/commodity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ commodity_name: commodity, price_increase_pct: priceSpike })
      });
      const data = await res.json();
      setCommodityResult(data);
    } catch (err) {
      console.error('Error running commodity simulation:', err);
    } finally {
      setLoading(false);
    }
  };

  // Generate chart data based on port simulation result
  const getChartData = () => {
    if (!portResult || !portResult.inventory_status || portResult.inventory_status.length === 0) return [];
    
    // Plot a simple daily rundown for 30 days
    const horizon = 30;
    const chartData = [];
    const firstStatus = portResult.inventory_status[0];
    let stock = firstStatus.current_stock;
    const dailyDemand = stock / 15; // approximate demand
    const safety = firstStatus.safety_stock;

    for (let day = 0; day <= horizon; day++) {
      chartData.push({
        day: `Day ${day}`,
        StockLevel: Math.round(Math.max(0, stock)),
        SafetyStock: safety,
      });
      
      // Stock starts depleting. After delay, replenishment hits (if delay < 30)
      const replenishmentDelay = portResult.alternative_route 
        ? portResult.alternative_route.delay_added_days 
        : duration;
      const isReplenishing = day >= replenishmentDelay;
      if (isReplenishing) {
        stock += dailyDemand * 0.8; // partial replenishment
      }
      stock -= dailyDemand;
    }
    return chartData;
  };

  const formatCurrency = (val: number) => {
    if (val >= 1000000) return `$${(val / 1000000).toFixed(2)}M`;
    return `$${val.toLocaleString()}`;
  };

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 70px)', overflowY: 'auto' }}>
      <div>
        <h2>Scenario Simulation Engine</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
          Evaluate the financial exposure, operational delay, and stockout timelines of global supply disruptions.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button 
          className={`btn ${activeTab === 'port' ? 'btn-primary' : 'btn-secondary'}`} 
          onClick={() => setActiveTab('port')}
        >
          Seaport Closure
        </button>
        <button 
          className={`btn ${activeTab === 'commodity' ? 'btn-primary' : 'btn-secondary'}`} 
          onClick={() => setActiveTab('commodity')}
        >
          Commodity Price Spike
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: '20px', alignItems: 'start' }}>
        
        {/* Left Side: Inputs */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {activeTab === 'port' ? (
            <>
              <h3 style={{ fontSize: '1.15rem' }}>Port Closure Parameters</h3>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Select Seaport</label>
                <select value={portName} onChange={(e) => setPortName(e.target.value)}>
                  {ports.map((p: any) => (
                    <option key={p.id} value={p.name}>
                      {p.name} ({p.country})
                    </option>
                  ))}
                  {ports.length === 0 && <option value="">No Ports Available</option>}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Closure Duration (Days)</label>
                <input 
                  type="number" 
                  value={duration} 
                  onChange={(e) => setDuration(parseInt(e.target.value) || 1)} 
                  min={1} 
                  max={60} 
                />
              </div>

              <button className="btn btn-primary" onClick={runPortSimulation} disabled={loading} style={{ justifyContent: 'center' }}>
                <Play size={16} /> {loading ? 'Running Simulation...' : 'Execute Simulation'}
              </button>
            </>
          ) : (
            <>
              <h3 style={{ fontSize: '1.15rem' }}>Commodity Cost Parameters</h3>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Select Commodity</label>
                <select value={commodity} onChange={(e) => setCommodity(e.target.value)}>
                  {commodities.map((c: string) => (
                    <option key={c} value={c}>
                      {c.charAt(0).toUpperCase() + c.slice(1)} {c === 'oil' ? '(Global logistics fuel)' : '(Product raw material)'}
                    </option>
                  ))}
                  {commodities.length === 0 && <option value="">No Commodities Available</option>}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Price Spike (%)</label>
                <input 
                  type="number" 
                  value={priceSpike} 
                  onChange={(e) => setPriceSpike(parseInt(e.target.value) || 5)} 
                  min={5} 
                  max={200} 
                />
              </div>

              <button className="btn btn-primary" onClick={runCommoditySimulation} disabled={loading} style={{ justifyContent: 'center' }}>
                <Play size={16} /> {loading ? 'Running Simulation...' : 'Execute Simulation'}
              </button>
            </>
          )}
        </div>

        {/* Right Side: Simulation Outcomes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Port Closure Outcome */}
          {activeTab === 'port' && portResult && !portResult.error && !portResult.detail && (
            <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h3 style={{ fontSize: '1.3rem', color: 'var(--accent-red)' }}>Disruption Assessment Summary</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>{portResult.scenario}</p>
              </div>

              {/* Financial & Time Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Revenue at Risk</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-red)', marginTop: '4px' }}>
                    {formatCurrency(portResult.revenue_at_risk)}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Estimated Profit Loss</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-orange)', marginTop: '4px' }}>
                    {formatCurrency(portResult.total_financial_impact)}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Products Affected</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 'bold', marginTop: '4px' }}>
                    {portResult.products_affected_count}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Rerouting Delay</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-cyan)', marginTop: '4px' }}>
                    {portResult.alternative_route 
                      ? `+${portResult.alternative_route.delay_added_days} Days`
                      : 'N/A (No Alt Route)'}
                  </div>
                </div>
              </div>

              {/* Depletion Rundown Line Chart */}
              <div>
                <h4 style={{ fontSize: '1rem', marginBottom: '12px', color: 'var(--text-secondary)' }}>Inventory Stock Rundown (30-Day Projection)</h4>
                <div style={{ width: '100%', height: 200 }}>
                  <ResponsiveContainer>
                    <AreaChart data={getChartData()} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorStock" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={10} />
                      <YAxis stroke="var(--text-muted)" fontSize={10} />
                      <Tooltip contentStyle={{ background: '#0c0f1d', borderColor: 'rgba(255,255,255,0.1)' }} />
                      <Area type="monotone" dataKey="StockLevel" stroke="var(--accent-cyan)" fillOpacity={1} fill="url(#colorStock)" />
                      <Area type="monotone" dataKey="SafetyStock" stroke="var(--accent-red)" strokeDasharray="4 4" fill="none" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Inventory Table */}
              <div>
                <h4 style={{ fontSize: '1rem', marginBottom: '10px', color: 'var(--text-secondary)' }}>Downstream Warehouse Impact Table</h4>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '8px' }}>Warehouse</th>
                      <th style={{ padding: '8px' }}>Product SKU</th>
                      <th style={{ padding: '8px' }}>Stock Status</th>
                      <th style={{ padding: '8px' }}>Depletion Days</th>
                      <th style={{ padding: '8px' }}>Stockout Prob.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.isArray(portResult.inventory_status) && portResult.inventory_status.map((item: any, i: number) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                        <td style={{ padding: '8px' }}>{item.warehouse_name}</td>
                        <td style={{ padding: '8px' }}>{item.product_name}</td>
                        <td style={{ padding: '8px' }}>
                          <span className={`status-badge ${item.stockout_risk_level === 'High' ? 'status-high' : 'status-low'}`}>
                            {item.stockout_risk_level} Risk
                          </span>
                        </td>
                        <td style={{ padding: '8px' }}>{item.depletion_days} Days</td>
                        <td style={{ padding: '8px' }}>{item.stockout_probability}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Actionable Recommendations */}
              <div style={{ background: 'rgba(0, 240, 255, 0.04)', border: '1px solid rgba(0, 240, 255, 0.15)', borderRadius: '8px', padding: '16px' }}>
                <h4 style={{ fontSize: '1rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <ShieldAlert size={18} />
                  Mitigation Action Plan
                </h4>
                <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  {Array.isArray(portResult.recommendations) && portResult.recommendations.map((rec: string, i: number) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Commodity outcome */}
          {activeTab === 'commodity' && commodityResult && !commodityResult.error && !commodityResult.detail && (
            <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h3 style={{ fontSize: '1.3rem', color: 'var(--accent-orange)' }}>Margin Impact Assessment</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>{commodityResult.scenario}</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Gross Annual Cost Spike</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--accent-red)', marginTop: '4px' }}>
                    {formatCurrency(commodityResult.annual_gross_cost_increase)}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Net Margin Reduction</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--accent-orange)', marginTop: '4px' }}>
                    {formatCurrency(commodityResult.expected_annual_loss)}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Production Cost Inflation</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--accent-purple)', marginTop: '4px' }}>
                    +{commodityResult.production_cost_increase_pct}%
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(255, 159, 28, 0.04)', border: '1px solid rgba(255, 159, 28, 0.15)', borderRadius: '8px', padding: '16px' }}>
                <h4 style={{ fontSize: '1rem', color: 'var(--accent-orange)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <TrendingUp size={18} />
                  Sourcing & Price Hedging Recommendations
                </h4>
                <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  {Array.isArray(commodityResult.recommendations) && commodityResult.recommendations.map((rec: string, i: number) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Display error alert if either simulation returned error */}
          {portResult && (portResult.error || portResult.detail) && (
            <div className="glass-panel" style={{ borderLeft: '4px solid var(--accent-red)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h3 style={{ color: 'var(--accent-red)', fontSize: '1.15rem' }}>Simulation Run Failed</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                {typeof (portResult.error || portResult.detail) === 'string'
                  ? (portResult.error || portResult.detail)
                  : JSON.stringify(portResult.error || portResult.detail)}
              </p>
            </div>
          )}

          {commodityResult && (commodityResult.error || commodityResult.detail) && (
            <div className="glass-panel" style={{ borderLeft: '4px solid var(--accent-red)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h3 style={{ color: 'var(--accent-red)', fontSize: '1.15rem' }}>Simulation Run Failed</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                {typeof (commodityResult.error || commodityResult.detail) === 'string'
                  ? (commodityResult.error || commodityResult.detail)
                  : JSON.stringify(commodityResult.error || commodityResult.detail)}
              </p>
            </div>
          )}

          {!portResult && !commodityResult && (
            <div style={{ height: '250px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', border: '1px dashed var(--border-color)', borderRadius: '12px' }}>
              <span>Adjust parameters and execute simulation above.</span>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
