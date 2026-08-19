import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Cpu, Sparkles } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface ChatMessage {
  sender: 'user' | 'agent';
  text: string;
  category?: string;
  timestamp: string;
}

export default function ExecutiveChat() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'agent',
      text: "Welcome to the Executive AI Control Center. Ask me complex strategic questions about your supply chain.\n\nExamples:\n- *What will happen if Taiwan exports stop?*\n- *Which suppliers are at highest risk right now?*\n- *Find alternative suppliers for lithium batteries.*",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, {
      sender: 'user',
      text: userMsg,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await res.json();
      
      setMessages(prev => [...prev, {
        sender: 'agent',
        text: data.response,
        category: data.category,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [...prev, {
        sender: 'agent',
        text: "Error connecting to the Multi-Agent framework. Please make sure the FastAPI backend is running.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setLoading(false);
    }
  };

  // A very lightweight, robust custom Markdown formatter for React
  const formatMarkdown = (text: string) => {
    const lines = text.split('\n');
    let insideTable = false;
    let tableHeaders: string[] = [];
    let tableRows: string[][] = [];

    return lines.map((line, idx) => {
      // 1. Table Detection
      if (line.trim().startsWith('|')) {
        const parts = line.split('|').map(p => p.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
        if (line.includes('---')) {
          // delimiter line, skip
          return null;
        }
        if (!insideTable) {
          insideTable = true;
          tableHeaders = parts;
          return null;
        } else {
          tableRows.push(parts);
          // If the next line is not a table row, render the table
          const nextLine = lines[idx + 1];
          if (!nextLine || !nextLine.trim().startsWith('|')) {
            insideTable = false;
            const currentRows = [...tableRows];
            const currentHeaders = [...tableHeaders];
            tableRows = [];
            tableHeaders = [];
            return (
              <div key={idx} style={{ overflowX: 'auto', margin: '14px 0', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      {currentHeaders.map((h, i) => <th key={i} style={{ padding: '8px 12px', fontWeight: 'bold' }}>{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {currentRows.map((row, rIdx) => (
                      <tr key={rIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                        {row.map((cell, cIdx) => <td key={cIdx} style={{ padding: '8px 12px' }}>{cell}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }
          return null;
        }
      }

      if (insideTable) return null; // skipped as accumulated

      // 2. Heading 3
      if (line.startsWith('### ')) {
        return <h4 key={idx} style={{ color: 'var(--text-primary)', fontSize: '1.05rem', margin: '14px 0 8px 0', fontWeight: 650 }}>{parseInline(line.substring(4))}</h4>;
      }
      // 3. Heading 2
      if (line.startsWith('## ')) {
        return <h3 key={idx} style={{ color: 'var(--accent-cyan)', fontSize: '1.2rem', margin: '18px 0 10px 0', fontWeight: 700, borderBottom: '1px solid var(--border-color)', paddingBottom: '4px' }}>{parseInline(line.substring(3))}</h3>;
      }
      // 4. Heading 1
      if (line.startsWith('# ')) {
        return <h2 key={idx} style={{ color: 'var(--text-primary)', fontSize: '1.4rem', margin: '22px 0 12px 0', fontWeight: 800 }}>{parseInline(line.substring(2))}</h2>;
      }
      // 5. Bullet List Items
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        return (
          <li key={idx} style={{ marginLeft: '20px', paddingLeft: '4px', margin: '6px 0', color: 'var(--text-secondary)' }}>
            {parseInline(line.trim().substring(2))}
          </li>
        );
      }
      // 6. Numbered List Items
      if (/^\d+\.\s/.test(line.trim())) {
        const content = line.trim().replace(/^\d+\.\s/, '');
        return (
          <li key={idx} style={{ marginLeft: '20px', listStyleType: 'decimal', paddingLeft: '4px', margin: '6px 0', color: 'var(--text-secondary)' }}>
            {parseInline(content)}
          </li>
        );
      }
      // 7. Empty lines
      if (!line.trim()) {
        return <div key={idx} style={{ height: '8px' }} />;
      }
      
      // 8. Normal text lines
      return <p key={idx} style={{ margin: '6px 0', lineHeight: 1.5, color: 'var(--text-secondary)' }}>{parseInline(line)}</p>;
    });
  };

  // Formatter for bold ** and italic * inline tags
  const parseInline = (text: string) => {
    let parts: React.ReactNode[] = [text];
    
    // Bold parser
    const boldRegex = /\*\*(.*?)\*\*/g;
    let hasBold = false;
    
    // Process bolds
    const tempBolds: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;
    
    while ((match = boldRegex.exec(text)) !== null) {
      hasBold = true;
      if (match.index > lastIndex) {
        tempBolds.push(text.substring(lastIndex, match.index));
      }
      tempBolds.push(<strong key={match.index} style={{ color: '#fff', fontWeight: 700 }}>{match[1]}</strong>);
      lastIndex = boldRegex.lastIndex;
    }
    if (hasBold) {
      if (lastIndex < text.length) {
        tempBolds.push(text.substring(lastIndex));
      }
      parts = tempBolds;
    }

    return parts;
  };

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 70px)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div>
          <h2>Executive AI Chat</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
            Multi-Agent interface: Planner routes inputs to Risk, Forecast, and Scenario Agents for a unified answer.
          </p>
        </div>
      </div>

      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, padding: 0, overflow: 'hidden' }}>
        {/* Chat History */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {messages.map((msg, idx) => (
            <div 
              key={idx} 
              style={{ 
                display: 'flex', 
                gap: '12px', 
                flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start'
              }}
            >
              {/* Avatar */}
              <div 
                style={{ 
                  width: '36px', 
                  height: '36px', 
                  borderRadius: '8px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  background: msg.sender === 'user' ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))' : 'rgba(255,255,255,0.05)',
                  border: '1px solid var(--border-color)',
                  color: msg.sender === 'user' ? '#000' : '#fff'
                }}
              >
                {msg.sender === 'user' ? <User size={18} /> : <Bot size={18} />}
              </div>

              {/* Message bubble */}
              <div 
                style={{ 
                  maxWidth: '75%', 
                  background: msg.sender === 'user' ? 'rgba(0, 240, 255, 0.05)' : 'rgba(255,255,255,0.02)',
                  border: msg.sender === 'user' ? '1px solid rgba(0, 240, 255, 0.2)' : '1px solid var(--border-color)',
                  borderRadius: '12px', 
                  padding: '16px',
                  position: 'relative'
                }}
              >
                {/* Agent workflow route tag */}
                {msg.category && (
                  <span 
                    style={{ 
                      fontSize: '0.65rem', 
                      position: 'absolute', 
                      top: '-8px', 
                      right: '12px', 
                      background: 'var(--bg-secondary)', 
                      border: '1px solid var(--accent-cyan)', 
                      color: 'var(--accent-cyan)', 
                      padding: '2px 8px', 
                      borderRadius: '10px', 
                      fontWeight: 700 
                    }}
                  >
                    Routed: {msg.category} Agent
                  </span>
                )}

                <div style={{ fontSize: '0.95rem' }}>
                  {formatMarkdown(msg.text)}
                </div>

                <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))}
          
          {loading && (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)' }}>
                <Cpu size={18} className="pulse-dot" style={{ color: 'var(--accent-cyan)' }} />
              </div>
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={16} className="pulse-dot" style={{ color: 'var(--accent-purple)' }} />
                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>AI Agent Orchestrator Planning Response...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form 
          onSubmit={handleSendMessage} 
          style={{ 
            padding: '16px', 
            borderTop: '1px solid var(--border-color)', 
            background: 'var(--bg-secondary)', 
            display: 'flex', 
            gap: '12px' 
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AI Orchestrator (e.g. What happens if Shanghai Port closes for 10 days?)"
            style={{ flex: 1 }}
            required
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
            <Send size={16} /> Send
          </button>
        </form>
      </div>
    </div>
  );
}
