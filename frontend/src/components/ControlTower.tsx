import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Shield, AlertTriangle, Ship, TrendingDown, Users, DollarSign } from 'lucide-react';

// Use the user's Mapbox token from env
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN || '';

interface KPIState {
  total_suppliers: number;
  at_risk_suppliers: number;
  active_disruptions: number;
  avg_stockout_probability: number;
  delayed_shipments: number;
  expected_revenue_impact: number;
}

interface SupplierData {
  id: number;
  name: string;
  country: string;
  city: string;
  latitude: number;
  longitude: number;
  status: string;
  risks: {
    overall_risk: number;
    geopolitical_risk: number;
    climate_risk: number;
    financial_risk: number;
    logistics_risk: number;
  };
}

export default function ControlTower() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [kpis, setKpis] = useState<KPIState>({
    total_suppliers: 0,
    at_risk_suppliers: 0,
    active_disruptions: 0,
    avg_stockout_probability: 0,
    delayed_shipments: 0,
    expected_revenue_impact: 0,
  });
  const [suppliers, setSuppliers] = useState<SupplierData[]>([]);

  useEffect(() => {
    // 1. Fetch KPIs and Suppliers
    const fetchData = async () => {
      try {
        const kpiRes = await fetch('http://localhost:8001/api/kpis');
        const kpiData = await kpiRes.json();
        setKpis(kpiData);

        const supRes = await fetch('http://localhost:8001/api/suppliers');
        const supData = await supRes.json();
        setSuppliers(supData);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (!mapContainer.current) return;
    if (map.current) return; // initialize map only once

    try {
      // Create Mapbox Map
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [15, 20],
        zoom: 1.6,
        projection: 'globe'
      });

      map.current.on('style.load', () => {
        try {
          if (!map.current) return;
          
          // Set atmospheric space lighting
          map.current.setFog({
            color: 'rgb(8, 12, 33)',
            'high-color': 'rgb(4, 6, 20)',
            'horizon-blend': 0.02,
            'space-color': 'rgb(3, 4, 8)',
            'star-intensity': 0.8
          });

          // Add route lines data source
          const routesGeoJSON: any = {
            type: 'FeatureCollection',
            features: [
              // Shanghai Port -> Los Angeles Port (Ocean Route)
              {
                type: 'Feature',
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [122.06, 30.62], // Shanghai Port
                    [-118.26, 33.74] // LA Port
                  ]
                },
                properties: { name: 'Shanghai to LA Shipping Lane' }
              },
              // Kaohsiung Port -> Los Angeles Port (Ocean Route)
              {
                type: 'Feature',
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [120.27, 22.61], // Kaohsiung
                    [-118.26, 33.74] // LA Port
                  ]
                },
                properties: { name: 'Kaohsiung to LA Shipping Lane' }
              },
              // Shanghai Port -> Rotterdam Port (Suez Route)
              {
                type: 'Feature',
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [122.06, 30.62], // Shanghai Port
                    [103.83, 1.26],  // Singapore Port
                    [42.50, 20.0],   // Red Sea/Suez
                    [4.47, 51.92]    // Rotterdam Port
                  ]
                },
                properties: { name: 'Shanghai to Rotterdam (Suez)' }
              }
            ]
          };

          map.current.addSource('shipping-routes', {
            type: 'geojson',
            data: routesGeoJSON
          });

          // Add line layer with custom glow properties
          map.current.addLayer({
            id: 'routes-layer',
            type: 'line',
            source: 'shipping-routes',
            layout: {
              'line-join': 'round',
              'line-cap': 'round'
            },
            paint: {
              'line-color': '#00f0ff',
              'line-width': 2,
              'line-opacity': 0.6
            }
          });
        } catch (styleErr) {
          console.error("Error setting up Mapbox styles/layers:", styleErr);
        }
      });
    } catch (err) {
      console.error("Mapbox GL failed to initialize:", err);
    }

    // Clean up map on unmount
    return () => {
      if (map.current) {
        try {
          map.current.remove();
        } catch (e) {
          console.error(e);
        }
        map.current = null;
      }
    };
  }, []);

  // Update map markers when suppliers data loads
  useEffect(() => {
    try {
      if (!map.current || suppliers.length === 0) return;

      suppliers.forEach((sup) => {
        if (!map.current) return;
        
        // Determine marker color based on overall risk
        let color = '#00f5d4'; // green
        if (sup.risks.overall_risk > 55) color = '#ff0054'; // red
        else if (sup.risks.overall_risk > 35) color = '#ff9f1c'; // orange

        // Create a HTML element for the marker
        const el = document.createElement('div');
        el.className = 'custom-marker';
        el.style.backgroundColor = color;
        el.style.width = '12px';
        el.style.height = '12px';
        el.style.borderRadius = '50%';
        el.style.border = '2px solid #ffffff';
        el.style.boxShadow = `0 0 10px ${color}`;
        el.style.cursor = 'pointer';

        // Create Popup
        const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
          <div style="padding: 4px;">
            <h4 style="font-weight: 700; color: #fff; margin-bottom: 4px;">${sup.name}</h4>
            <p style="margin: 0; color: #a0aec0; font-size: 0.85rem;">Location: ${sup.city}, ${sup.country}</p>
            <div style="margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px;">
              <span style="font-weight: 600; color: #fff;">Overall Risk Score: </span>
              <span style="font-weight: 700; color: ${color};">${sup.risks.overall_risk}</span>
            </div>
          </div>
        `);

        // Add to map
        new mapboxgl.Marker(el)
          .setLngLat([sup.longitude, sup.latitude])
          .setPopup(popup)
          .addTo(map.current);
      });

      // Add Port Markers
      const mockPorts = [
        { name: 'Shanghai Port', lon: 122.06, lat: 30.62 },
        { name: 'Rotterdam Port', lon: 4.47, lat: 51.92 },
        { name: 'Los Angeles Port', lon: -118.26, lat: 33.74 },
        { name: 'Kaohsiung Port', lon: 120.27, lat: 22.61 }
      ];

      mockPorts.forEach((p) => {
        if (!map.current) return;
        const el = document.createElement('div');
        el.className = 'custom-marker';
        el.style.backgroundColor = '#ffffff';
        el.style.width = '10px';
        el.style.height = '10px';
        el.style.clipPath = 'polygon(50% 0%, 0% 100%, 100% 100%)'; // triangle for ports
        el.style.cursor = 'pointer';

        const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
          <div style="padding: 4px;">
            <h4 style="font-weight: 700; color: #fff;">${p.name}</h4>
            <p style="margin: 0; color: #a0aec0; font-size: 0.8rem;">Infrastructure Type: Seaport Hub</p>
          </div>
        `);

        new mapboxgl.Marker(el)
          .setLngLat([p.lon, p.lat])
          .setPopup(popup)
          .addTo(map.current);
      });
    } catch (markerErr) {
      console.error("Error setting up map markers:", markerErr);
    }

  }, [suppliers]);

  const formatCurrency = (val: number) => {
    if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
    return `$${val.toLocaleString()}`;
  };

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 70px)' }}>
      {/* 1. KPIs */}
      <div className="kpi-grid">
        <div className="glass-panel kpi-card glow-cyan-hover">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>Total Suppliers</span>
            <Users size={20} color="var(--accent-cyan)" />
          </div>
          <div className="kpi-value">{kpis?.total_suppliers ?? 0}</div>
        </div>

        <div className="glass-panel kpi-card glow-cyan-hover">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>At Risk Suppliers</span>
            <Shield size={20} color="var(--accent-red)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>{kpis?.at_risk_suppliers ?? 0}</div>
        </div>

        <div className="glass-panel kpi-card glow-cyan-hover">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>Active Disruptions</span>
            <AlertTriangle size={20} color="var(--accent-orange)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-orange)' }}>{kpis?.active_disruptions ?? 0}</div>
        </div>

        <div className="glass-panel kpi-card glow-cyan-hover">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>Stockout Probability</span>
            <TrendingDown size={20} color="var(--accent-purple)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-purple)' }}>{kpis?.avg_stockout_probability ?? 0}%</div>
        </div>

        <div className="glass-panel kpi-card glow-cyan-hover">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>Delayed Shipments</span>
            <Ship size={20} color="var(--accent-cyan)" />
          </div>
          <div className="kpi-value">{kpis?.delayed_shipments ?? 0}</div>
        </div>

        <div className="glass-panel kpi-card glow-cyan-hover">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>Revenue Impact</span>
            <DollarSign size={20} color="var(--accent-red)" />
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>{formatCurrency(kpis?.expected_revenue_impact ?? 0)}</div>
        </div>
      </div>

      {/* 2. Map and Side Info Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Mapbox container */}
        <div ref={mapContainer} style={{ borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden', height: '100%', position: 'relative' }} />
        
        {/* Country Risk panel */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>Country Risk Scores</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Taiwan</span>
              <span className="status-badge status-high">65.0 - High</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>China</span>
              <span className="status-badge status-medium">55.0 - Mid</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>India</span>
              <span className="status-badge status-medium">50.0 - Mid</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>South Korea</span>
              <span className="status-badge status-low">30.0 - Low</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Netherlands</span>
              <span className="status-badge status-low">13.0 - Low</span>
            </div>
          </div>

          <h3 style={{ fontSize: '1.2rem', fontWeight: 600, borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', marginTop: '10px' }}>Upcoming Risks</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span style={{ color: 'var(--accent-red)', fontWeight: 'bold' }}>Q3</span>
              <span>Predicted typhoon activity spikes in South China Sea, threatening Ningbo shipping lanes.</span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span style={{ color: 'var(--accent-orange)', fontWeight: 'bold' }}>Q4</span>
              <span>Potential labor union renegotiation and contract freezes at LA Port.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


