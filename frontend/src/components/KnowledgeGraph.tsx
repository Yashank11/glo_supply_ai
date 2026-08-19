import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { Network, HelpCircle, Activity } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface GraphNode {
  id: string;
  name: string;
  label: string;
  country?: string;
  risk?: number;
  capacity?: number;
  status?: string;
}

interface GraphLink {
  source: string;
  target: string;
  type: string;
  mode?: string;
  lead_time?: number;
  cost?: number;
}

export default function KnowledgeGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [downstreamNodes, setDownstreamNodes] = useState<string[]>([]);
  const [cyInstance, setCyInstance] = useState<cytoscape.Core | null>(null);

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/graph`);
        const data = await res.json();
        
        if (!containerRef.current) return;

        // Map elements for Cytoscape
        const elements: cytoscape.ElementDefinition[] = [];
        
        // Add nodes
        data.nodes.forEach((n: any) => {
          elements.push({
            data: {
              id: n.id,
              name: n.name || n.id,
              type: n.label, // Supplier, Factory, Port, Warehouse, Customer, Product
              ...n
            }
          });
        });

        // Add edges
        data.links.forEach((l: any, index: number) => {
          elements.push({
            data: {
              id: `edge_${index}`,
              source: l.source,
              target: l.target,
              relationship: l.type,
              ...l
            }
          });
        });

        // Initialize Cytoscape
        const cy = cytoscape({
          container: containerRef.current,
          elements: elements,
          style: [
            {
              selector: 'node',
              style: {
                'label': 'data(name)',
                'color': '#cbd5e1',
                'font-size': '10px',
                'font-family': 'Outfit, sans-serif',
                'text-valign': 'bottom',
                'text-margin-y': 6,
                'background-color': '#475569',
                'width': 25,
                'height': 25,
                'transition-property': 'background-color, line-color, target-arrow-color',
                'transition-duration': 0.3
              }
            },
            {
              selector: 'node[type="Supplier"]',
              style: {
                'background-color': '#bd00ff', // Purple
                'shape': 'hexagon'
              }
            },
            {
              selector: 'node[type="Factory"]',
              style: {
                'background-color': '#ff9f1c', // Orange
                'shape': 'triangle'
              }
            },
            {
              selector: 'node[type="Port"]',
              style: {
                'background-color': '#00f0ff', // Cyan
                'shape': 'rectangle'
              }
            },
            {
              selector: 'node[type="Warehouse"]',
              style: {
                'background-color': '#00f5d4', // Green
                'shape': 'octagon'
              }
            },
            {
              selector: 'node[type="Customer"]',
              style: {
                'background-color': '#ff0054', // Red
                'shape': 'diamond'
              }
            },
            {
              selector: 'node[type="Product"]',
              style: {
                'background-color': '#ffffff',
                'shape': 'ellipse',
                'width': 18,
                'height': 18
              }
            },
            {
              selector: 'edge',
              style: {
                'width': 1.5,
                'line-color': 'rgba(255,255,255,0.15)',
                'target-arrow-color': 'rgba(255,255,255,0.15)',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'font-size': '8px',
                'color': '#64748b',
                'text-margin-y': -8
              }
            },
            {
              selector: 'edge[relationship="SHIPS_TO"]',
              style: {
                'line-color': '#00f0ff',
                'target-arrow-color': '#00f0ff',
                'line-style': 'dashed'
              }
            },
            {
              selector: 'edge[relationship="SUPPLIES"]',
              style: {
                'line-color': '#bd00ff',
                'target-arrow-color': '#bd00ff'
              }
            },
            {
              selector: '.highlighted',
              style: {
                'background-color': '#00ff66',
                'line-color': '#00ff66',
                'target-arrow-color': '#00ff66',
                'width': 3.5
              }
            }
          ],
          layout: {
            name: 'cose', // force-directed layout
            idealEdgeLength: () => 100,
            nodeOverlap: 20,
            refresh: 20,
            fit: true,
            padding: 30,
            randomize: false,
            componentSpacing: 100,
            nodeRepulsion: () => 400000,
            edgeElasticity: () => 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0
          }
        });

        // Click handler
        cy.on('tap', 'node', (evt) => {
          const node = evt.target;
          const nodeData = node.data() as GraphNode;
          setSelectedNode(nodeData);

          // Reset styles
          cy.elements().removeClass('highlighted');

          // Highlight downstream BFS blast radius
          const bfs = cy.elements().bfs({
            roots: node,
            directed: true,
            visit: () => {}
          });

          const pathIds: string[] = [];
          bfs.path.forEach((ele) => {
            ele.addClass('highlighted');
            if (ele.isNode()) {
              pathIds.push(ele.data('name'));
            }
          });
          setDownstreamNodes(pathIds);
        });

        cy.on('tap', (evt) => {
          if (evt.target === cy) {
            setSelectedNode(null);
            setDownstreamNodes([]);
            cy.elements().removeClass('highlighted');
          }
        });

        setCyInstance(cy);

      } catch (err) {
        console.error('Error rendering cytoscape graph:', err);
      }
    };
    fetchGraph();
  }, []);

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 70px)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Supply Chain Knowledge Graph</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
            Interactive dependency mapping. Click nodes to trace downstream paths ("blast radius").
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem' }}>
          <span style={{ color: '#bd00ff', display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ background: '#bd00ff', width: 8, height: 8, borderRadius: '50%' }}/> Supplier</span>
          <span style={{ color: '#ff9f1c', display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ background: '#ff9f1c', width: 8, height: 8, borderRadius: '50%' }}/> Factory</span>
          <span style={{ color: '#00f0ff', display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ background: '#00f0ff', width: 8, height: 8, borderRadius: '50%' }}/> Port</span>
          <span style={{ color: '#00f5d4', display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ background: '#00f5d4', width: 8, height: 8, borderRadius: '50%' }}/> Warehouse</span>
          <span style={{ color: '#ff0054', display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ background: '#ff0054', width: 8, height: 8, borderRadius: '50%' }}/> Customer</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Cytoscape container */}
        <div 
          ref={containerRef} 
          style={{ 
            borderRadius: '12px', 
            border: '1px solid var(--border-color)', 
            background: 'rgba(0,0,0,0.2)', 
            height: '100%' 
          }} 
        />

        {/* Info panel */}
        <div className="glass-panel" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {!selectedNode ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', gap: '12px' }}>
              <Network size={40} />
              <span>Click a node to inspect relationships</span>
            </div>
          ) : (
            <>
              <div>
                <span className="status-badge status-low" style={{ background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid var(--border-color)' }}>
                  {selectedNode.label}
                </span>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '8px' }}>{selectedNode.name}</h3>
                {selectedNode.country && (
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>Country: {selectedNode.country}</p>
                )}
              </div>

              {/* Node statistics */}
              <div style={{ borderTop: '1px solid var(--border-color)', borderBottom: '1px solid var(--border-color)', padding: '16px 0', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {selectedNode.risk !== undefined && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Overall Risk:</span>
                    <span style={{ fontWeight: 'bold', color: selectedNode.risk > 50 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                      {selectedNode.risk} / 100
                    </span>
                  </div>
                )}
                {selectedNode.capacity !== undefined && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Daily Capacity:</span>
                    <span style={{ fontWeight: 'bold' }}>{selectedNode.capacity} Tons</span>
                  </div>
                )}
                {selectedNode.status && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>System Status:</span>
                    <span className={`status-badge ${selectedNode.status === 'Active' || selectedNode.status === 'Open' ? 'status-low' : 'status-high'}`}>
                      {selectedNode.status}
                    </span>
                  </div>
                )}
              </div>

              {/* Downstream dependencies list */}
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                  <Activity size={16} color="var(--accent-green)" />
                  Downstream Blast Radius ({downstreamNodes.length - 1})
                </h4>
                
                {downstreamNodes.length <= 1 ? (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No downstream nodes impacted.</p>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {downstreamNodes
                      .filter(name => name !== selectedNode.name)
                      .map((name, i) => (
                        <span 
                          key={i} 
                          style={{ 
                            background: 'rgba(0, 245, 212, 0.08)', 
                            border: '1px solid rgba(0, 245, 212, 0.2)', 
                            color: 'var(--accent-green)', 
                            fontSize: '0.75rem', 
                            padding: '4px 8px', 
                            borderRadius: '4px' 
                          }}
                        >
                          {name}
                        </span>
                      ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
