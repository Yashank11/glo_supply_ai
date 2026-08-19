import React, { useEffect, useState } from 'react';
import { Radio, AlertTriangle, Play, RefreshCw, Layers } from 'lucide-react';

interface DisruptionEvent {
  id: number;
  event_type: string;
  location: string;
  severity: string;
  expected_duration_days: number;
  impact_description: string;
  created_at: string;
}

export default function EventMonitor() {
  const [events, setEvents] = useState<DisruptionEvent[]>([]);
  const [newsInput, setNewsInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState<any>(null);
  const [fetching, setFetching] = useState(false);

  const handleFetchLiveNews = async () => {
    setFetching(true);
    setIngestResult(null);
    try {
      const res = await fetch('http://localhost:8001/api/events/fetch-live', { method: 'POST' });
      const data = await res.json();
      
      // Load top ingested result or fallback status
      const topIngested = data.ingested_events && data.ingested_events[0];
      setIngestResult({
        event_extracted: topIngested ? topIngested.event_extracted : {
          event: "GDELT System Polled",
          location: "Global",
          severity: "Low",
          industry: "General Sourcing",
          expected_duration_days: 0,
          description: data.status
        },
        affected_suppliers_count: data.ingested_events ? data.ingested_events.length : 0,
        recalculated_supplier_risks: []
      });
      fetchEvents(); // reload active feed list
    } catch (err) {
      console.error('Error fetching live news:', err);
    } finally {
      setFetching(false);
    }
  };

  const fetchEvents = async () => {
    try {
      const res = await fetch('http://localhost:8001/api/events');
      const data = await res.json();
      setEvents(data);
    } catch (err) {
      console.error('Error fetching events:', err);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newsInput.trim()) return;

    setLoading(true);
    setIngestResult(null);

    try {
      const res = await fetch('http://localhost:8001/api/events/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: newsInput })
      });
      const data = await res.json();
      setIngestResult(data);
      setNewsInput('');
      fetchEvents(); // reload list
    } catch (err) {
      console.error('Error ingesting alert:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      await fetch('http://localhost:8001/api/events/clear', { method: 'POST' });
      setIngestResult(null);
      fetchEvents();
    } catch (err) {
      console.error('Error resetting events:', err);
    }
  };

  const getSeverityClass = (sev: string | null | undefined) => {
    if (!sev) return 'status-low';
    switch (sev.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'status-high';
      case 'medium':
        return 'status-medium';
      default:
        return 'status-low';
    }
  };

  return (
    <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', height: 'calc(100vh - 70px)' }}>
      {/* Left side: Alert feed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Real-Time Disruption Monitor</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
              Autonomous extraction and logging of geopolitical, climate, and logistical risks.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-primary" onClick={handleFetchLiveNews} disabled={fetching} style={{ fontSize: '0.85rem' }}>
              <Radio size={16} className={fetching ? 'pulse-dot' : ''} /> {fetching ? 'Polling GDELT...' : 'Pull Live News'}
            </button>
            <button className="btn btn-secondary" onClick={handleReset} style={{ fontSize: '0.85rem' }}>
              <RefreshCw size={16} /> Reset Engine
            </button>
          </div>
        </div>

        {/* List of active disruptions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', flex: 1, paddingRight: '4px' }}>
          {!Array.isArray(events) || events.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '10px' }}>
              <Radio size={36} className="pulse-dot" style={{ color: 'var(--accent-cyan)' }} />
              <span>Scanning global channels... No active disruptions.</span>
            </div>
          ) : (
            events.map((evt) => (
              <div key={evt.id} className="glass-panel" style={{ borderLeft: `4px solid ${evt.severity && (evt.severity === 'High' || evt.severity === 'Critical') ? 'var(--accent-red)' : 'var(--accent-orange)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertTriangle size={18} color="var(--accent-orange)" />
                    <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{evt.event_type}</span>
                  </div>
                  <span className={`status-badge ${getSeverityClass(evt.severity)}`}>{(evt.severity || 'Low')} Impact</span>
                </div>
                
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>{evt.impact_description}</p>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '8px' }}>
                  <span>Location: <strong>{evt.location}</strong></span>
                  <span>Estimated Duration: <strong>{evt.expected_duration_days} days</strong></span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right side: Alert ingest console */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
        <h3 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
          <Layers size={20} color="var(--accent-cyan)" />
          Event Intelligence Ingestion
        </h3>

        <form onSubmit={handleIngest} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              Paste News Feed / Trade Notification Text
            </label>
            <textarea
              value={newsInput}
              onChange={(e) => setNewsInput(e.target.value)}
              placeholder="Example: Bloomberg reports that a Category 4 typhoon has made landfall in Taiwan, disrupting semiconductor chip exports out of Hsinchu Science Park. Severe logistical delays are expected for the next 7 days..."
              rows={6}
              style={{ resize: 'none' }}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ justifyContent: 'center' }}>
            {loading ? <RefreshCw size={16} className="pulse-dot" /> : <Play size={16} />}
            {loading ? 'Processing Agent Extraction...' : 'Extract Disruption Parameters'}
          </button>
        </form>

        {/* Display extraction outcomes */}
        {ingestResult && !ingestResult.detail && !ingestResult.error && ingestResult.event_extracted && (
          <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '16px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <h4 style={{ fontSize: '1rem', color: 'var(--accent-green)' }}>Extraction Results & Risk Propagation</h4>
            
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div><strong>Extracted Event:</strong> {ingestResult.event_extracted.event}</div>
              <div><strong>Location:</strong> {ingestResult.event_extracted.location}</div>
              <div><strong>Severity:</strong> {ingestResult.event_extracted.severity}</div>
              <div><strong>Impacted Industry:</strong> {ingestResult.event_extracted.industry}</div>
              <div><strong>Expected Duration:</strong> {ingestResult.event_extracted.expected_duration_days} Days</div>
              <div><strong>Detail:</strong> {ingestResult.event_extracted.description}</div>
            </div>

            {ingestResult.affected_suppliers_count > 0 && Array.isArray(ingestResult.recalculated_supplier_risks) && (
              <div>
                <h5 style={{ fontSize: '0.85rem', marginBottom: '8px' }}>Affected Suppliers Recalculated</h5>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {ingestResult.recalculated_supplier_risks.map((sup: any, i: number) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', background: 'rgba(255, 255, 255, 0.02)', padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                      <span>{sup.supplier_name}</span>
                      <span style={{ color: sup.new_overall_risk > 50 ? 'var(--accent-red)' : 'var(--accent-orange)', fontWeight: 'bold' }}>
                        Risk Score: {sup.new_overall_risk}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {ingestResult && (ingestResult.detail || ingestResult.error) && (
          <div className="glass-panel" style={{ borderLeft: '4px solid var(--accent-red)', marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <h4 style={{ color: 'var(--accent-red)', fontSize: '1.1rem' }}>Ingestion Failed</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              {typeof (ingestResult.detail || ingestResult.error) === 'string' 
                ? (ingestResult.detail || ingestResult.error) 
                : JSON.stringify(ingestResult.detail || ingestResult.error)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
