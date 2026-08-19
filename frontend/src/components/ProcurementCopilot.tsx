import React, { useState } from 'react';
import { Search, Compass, MessageSquareCode, ShieldCheck, HelpCircle } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface AlternativeSupplier {
  supplier_name: string;
  country: string;
  overall_risk: number;
  geopolitical_risk: number;
  climate_risk: number;
  financial_risk: number;
  cost_tier: string;
  status: string;
}

export default function ProcurementCopilot() {
  const [sku, setSku] = useState('PROD-EVBAT');
  const [suppliers, setSuppliers] = useState<AlternativeSupplier[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<AlternativeSupplier | null>(null);
  const [negotiationData, setNegotiationData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [negLoading, setNegLoading] = useState(false);

  const searchAlternatives = async () => {
    setLoading(true);
    setSelectedSupplier(null);
    setNegotiationData(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/procurement/alternatives`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku })
      });
      const data = await res.json();
      setSuppliers(data);
    } catch (err) {
      console.error('Error finding alternatives:', err);
    } finally {
      setLoading(false);
    }
  };

  const getNegotiationInsights = async (target: AlternativeSupplier) => {
    setSelectedSupplier(target);
    setNegLoading(true);
    setNegotiationData(null);

    // Set default primary suppliers to compare against
    const currentSupplierMap: any = {
      'PROD-EVBAT': 'CATL',
      'PROD-IPH17': 'TSMC',
      'PROD-MACM4': 'TSMC'
    };
    
    const productNameMap: any = {
      'PROD-EVBAT': 'Silicon Anode EV Battery Pack',
      'PROD-IPH17': 'iPhone 17 Pro Chipsets',
      'PROD-MACM4': 'MacBook Pro M4 Logic Boards'
    };

    try {
      const res = await fetch(`${API_BASE_URL}/api/procurement/negotiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_supplier: currentSupplierMap[sku] || 'Primary Vendor',
          target_supplier: target.supplier_name,
          product_name: productNameMap[sku] || 'Components'
        })
      });
      const data = await res.json();
      setNegotiationData(data);
    } catch (err) {
      console.error('Error generating negotiation insights:', err);
    } finally {
      setNegLoading(false);
    }
  };

  const getSkuLabel = (skuStr: string) => {
    switch (skuStr) {
      case 'PROD-EVBAT': return 'EV Battery Pack (Current: CATL)';
      case 'PROD-IPH17': return 'iPhone 17 Pro A19 Chipset (Current: TSMC)';
      case 'PROD-MACM4': return 'MacBook Pro M4 Logic Board (Current: TSMC)';
      default: return skuStr;
    }
  };

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 70px)' }}>
      <div>
        <h2>Procurement Copilot</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
          Discover alternative suppliers, assess cost vs. risk trade-offs, and generate negotiation talking points.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Sourcing Panel */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '1.15rem' }}>Alternative Supplier Sourcing</h3>
          
          <div>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Select Vulnerable SKU</label>
            <select value={sku} onChange={(e) => setSku(e.target.value)}>
              <option value="PROD-EVBAT">{getSkuLabel('PROD-EVBAT')}</option>
              <option value="PROD-IPH17">{getSkuLabel('PROD-IPH17')}</option>
              <option value="PROD-MACM4">{getSkuLabel('PROD-MACM4')}</option>
            </select>
          </div>

          <button className="btn btn-primary" onClick={searchAlternatives} disabled={loading} style={{ justifyContent: 'center' }}>
            <Search size={16} /> {loading ? 'Searching Database...' : 'Find Alternative Suppliers'}
          </button>
        </div>

        {/* Results Panel */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', minHeight: 0 }}>
          
          {/* Supplier Table */}
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
            <h3 style={{ fontSize: '1.15rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>Alternative Supplier Options</h3>
            
            {suppliers.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', gap: '12px' }}>
                <Compass size={36} />
                <span>Search alternatives to view comparison table</span>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {suppliers.map((s, idx) => (
                  <div 
                    key={idx} 
                    className="glass-panel" 
                    onClick={() => getNegotiationInsights(s)}
                    style={{ 
                      cursor: 'pointer', 
                      background: selectedSupplier?.supplier_name === s.supplier_name ? 'var(--bg-surface-hover)' : 'rgba(0,0,0,0.15)',
                      borderColor: selectedSupplier?.supplier_name === s.supplier_name ? 'var(--accent-cyan)' : 'var(--border-color)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontWeight: '700', fontSize: '1rem' }}>{s.supplier_name}</span>
                      <span className={`status-badge ${s.overall_risk > 50 ? 'status-high' : 'status-low'}`}>
                        Risk: {s.overall_risk}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span>Country: {s.country}</span>
                      <span>Cost: <strong>{s.cost_tier}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Negotiation Insights */}
          <div className="glass-panel" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              <MessageSquareCode size={18} color="var(--accent-purple)" />
              Negotiation Playbook
            </h3>

            {negLoading && (
              <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <span className="pulse-dot" style={{ color: 'var(--accent-cyan)' }}>Generating AI Strategy Playbook...</span>
              </div>
            )}

            {!selectedSupplier && !negLoading && (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', gap: '12px' }}>
                <ShieldCheck size={36} />
                <span>Select an alternative supplier to compile negotiation talking points</span>
              </div>
            )}

            {selectedSupplier && negotiationData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '0.9rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target Backup Partner</div>
                  <strong style={{ fontSize: '1.1rem' }}>{selectedSupplier.supplier_name} ({selectedSupplier.country})</strong>
                </div>

                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                  <h4 style={{ color: 'var(--accent-cyan)', fontSize: '0.95rem', marginBottom: '8px' }}>Sourcing Leverage Points</h4>
                  <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)' }}>
                    {negotiationData.leverage_points?.map((pt: string, i: number) => (
                      <li key={i}>{pt}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 style={{ color: 'var(--accent-orange)', fontSize: '0.95rem', marginBottom: '8px' }}>Negotiation Tactics</h4>
                  <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)' }}>
                    {negotiationData.negotiation_tactics?.map((pt: string, i: number) => (
                      <li key={i}>{pt}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 style={{ color: 'var(--accent-purple)', fontSize: '0.95rem', marginBottom: '8px' }}>Recommended Contract Clauses</h4>
                  <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)' }}>
                    {negotiationData.contract_clauses_recommended?.map((pt: string, i: number) => (
                      <li key={i}>{pt}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px', fontSize: '0.85rem' }}>
                  <span>Transition Timeline:</span>
                  <strong>{negotiationData.estimated_transition_time_weeks} Weeks</strong>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
