import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Network, Radio, Zap, ShoppingCart, MessageSquare, ShieldAlert, RefreshCw } from 'lucide-react';
import ControlTower from './components/ControlTower';
import KnowledgeGraph from './components/KnowledgeGraph';
import EventMonitor from './components/EventMonitor';
import ScenarioSimulator from './components/ScenarioSimulator';
import ProcurementCopilot from './components/ProcurementCopilot';
import ExecutiveChat from './components/ExecutiveChat';

type TabType = 'control' | 'graph' | 'events' | 'simulator' | 'procurement' | 'chat';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('control');
  const [time, setTime] = useState(new Date());
  
  // Twin Generator States
  const [companyName, setCompanyName] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleGenerateTwin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) return;

    setGenerating(true);
    setGenError(null);

    try {
      const res = await fetch('http://localhost:8001/api/network/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName })
      });
      
      const data = await res.json();
      if (!res.ok || data.detail || data.error) {
        throw new Error(data.detail || data.error || 'Failed to construct twin.');
      }
      
      // Success! Reload the window to clear states and fetch the new supply chain
      window.location.reload();
    } catch (err: any) {
      console.error('Error generating supply chain twin:', err);
      setGenError(err.message || 'Server error during generation.');
      setGenerating(false);
    }
  };

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'control':
        return <ControlTower />;
      case 'graph':
        return <KnowledgeGraph />;
      case 'events':
        return <EventMonitor />;
      case 'simulator':
        return <ScenarioSimulator />;
      case 'procurement':
        return <ProcurementCopilot />;
      case 'chat':
        return <ExecutiveChat />;
      default:
        return <ControlTower />;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        {/* Brand logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
          <div style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))', width: '32px', height: '32px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={18} color="#000" style={{ margin: 'auto' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', lineHeight: '1.2rem', display: 'block', background: 'none', WebkitTextFillColor: 'initial', color: '#fff', fontWeight: 800 }}>SupplyTwin</h1>
            <span style={{ fontSize: '0.65rem', color: 'var(--accent-cyan)', letterSpacing: '1px', textTransform: 'uppercase', fontWeight: 700 }}>Digital Twin AI</span>
          </div>
        </div>

        {/* Tab Items */}
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div className={`tab-nav-item ${activeTab === 'control' ? 'active' : ''}`} onClick={() => setActiveTab('control')}>
            <LayoutDashboard size={18} />
            <span>Control Tower</span>
          </div>
          <div className={`tab-nav-item ${activeTab === 'graph' ? 'active' : ''}`} onClick={() => setActiveTab('graph')}>
            <Network size={18} />
            <span>Knowledge Graph</span>
          </div>
          <div className={`tab-nav-item ${activeTab === 'events' ? 'active' : ''}`} onClick={() => setActiveTab('events')}>
            <Radio size={18} />
            <span>Event Monitor</span>
          </div>
          <div className={`tab-nav-item ${activeTab === 'simulator' ? 'active' : ''}`} onClick={() => setActiveTab('simulator')}>
            <ShieldAlert size={18} />
            <span>Scenario Simulator</span>
          </div>
          <div className={`tab-nav-item ${activeTab === 'procurement' ? 'active' : ''}`} onClick={() => setActiveTab('procurement')}>
            <ShoppingCart size={18} />
            <span>Procurement Copilot</span>
          </div>
          <div className={`tab-nav-item ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            <MessageSquare size={18} />
            <span>Executive Chat</span>
          </div>
        </nav>

        {/* Footer brand indicator */}
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <div>System Engine v1.0.0</div>
          <div style={{ color: 'var(--accent-cyan)', marginTop: '2px', fontWeight: 'bold' }}>All Agents Active</div>
        </div>
      </div>

      {/* Main Panel Content Area */}
      <div className="main-content">
        <header className="header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ background: 'var(--accent-green)', width: '8px', height: '8px', borderRadius: '50%', boxShadow: '0 0 10px var(--accent-green)' }} className="pulse-dot" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Active Twin Connected</span>
          </div>

          {/* AI Digital Twin Generator Form */}
          <form onSubmit={handleGenerateTwin} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input 
              type="text" 
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Generate new company twin (e.g. Nike, NVIDIA)..." 
              style={{ 
                padding: '6px 12px', 
                borderRadius: '6px', 
                border: '1px solid var(--border-color)', 
                background: 'rgba(0,0,0,0.4)', 
                color: '#fff', 
                fontSize: '0.85rem',
                width: '260px'
              }}
              required
              disabled={generating}
            />
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ padding: '6px 12px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              disabled={generating}
            >
              {generating ? (
                <>
                  <RefreshCw size={14} className="spin-loader" />
                  <span>Building Twin...</span>
                </>
              ) : (
                <>
                  <Zap size={14} />
                  <span>AI Twin Builder</span>
                </>
              )}
            </button>
          </form>
          
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center', fontSize: '0.85rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Local Time: </span>
              <strong style={{ fontFamily: 'monospace', color: '#fff' }}>{time.toLocaleTimeString()}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Database: </span>
              <strong style={{ color: 'var(--accent-cyan)' }}>PostgreSQL & Neo4j Active</strong>
            </div>
          </div>
        </header>

        {renderActiveComponent()}
      </div>

      {/* Loading Overlay */}
      {generating && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(3, 4, 8, 0.85)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          gap: '20px'
        }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            border: '3px solid rgba(0, 240, 255, 0.1)',
            borderTopColor: 'var(--accent-cyan)',
          }} className="spin-loader" />
          <div style={{ textAlign: 'center' }}>
            <h3 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-cyan)' }}>Constructing Digital Twin</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '6px' }}>
              AI Agent searching registers, identifying suppliers & assembling supply chain graph for <strong>{companyName}</strong>...
            </p>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {genError && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          background: 'var(--accent-red)',
          color: '#fff',
          padding: '16px 20px',
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div>
            <strong style={{ display: 'block', fontSize: '0.9rem' }}>Generation Failed</strong>
            <span style={{ fontSize: '0.8rem', opacity: 0.9 }}>{genError}</span>
          </div>
          <button 
            onClick={() => setGenError(null)}
            style={{ 
              background: 'rgba(0,0,0,0.2)', 
              border: 'none', 
              color: '#fff', 
              borderRadius: '4px', 
              padding: '4px 8px', 
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
