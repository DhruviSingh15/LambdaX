import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Scheduler = () => {
  const [decision, setDecision] = useState(null);

  useEffect(() => {
    const fetchDecision = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/scheduler');
        if (res.data && Object.keys(res.data).length > 0) {
          setDecision(res.data);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchDecision();
    const interval = setInterval(fetchDecision, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!decision) return <div className="p-4 text-secondary">Awaiting first scheduler decision...</div>;

  const state = decision.current_state || {};
  const forecast = decision.forecast || [];
  
  // priority metric: expected wait / sla (mock logic to show the field as requested)
  const priority = (state.sla_ms > 0 && decision.expected_wait_ms > 0) ? (decision.expected_wait_ms / state.sla_ms).toFixed(2) : '0.00';

  return (
    <div>
      <h1>Adaptive Controller</h1>
      <p className="subtitle">Decision Engine Reasoning Pipeline</p>

      <div className="grid-2">
        
        {/* Left Side: The Pipeline View */}
        <div className="card" style={{ fontFamily: 'var(--font-mono)' }}>
          <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
            
            <div className="text-secondary mb-2 border-b border-gray-700 pb-1" style={{borderBottom: '1px solid #333d4b'}}>CURRENT STATE</div>
            <div className="flex-row justify-between mb-1"><span>Demand</span> <span style={{color: '#fff'}}>{decision.predicted_demand} RPS</span></div>
            <div className="flex-row justify-between mb-1"><span>Warm Containers</span> <span style={{color: '#fff'}}>{state.warm_containers || 0}</span></div>
            <div className="flex-row justify-between mb-1"><span>Busy Containers</span> <span style={{color: '#fff'}}>{state.busy_containers || 0}</span></div>
            <div className="flex-row justify-between mb-1"><span>Queue</span> <span style={{color: 'var(--warning-color)'}}>{state.queue_length || 0}</span></div>
            <div className="flex-row justify-between mb-4"><span>SLA Target</span> <span style={{color: '#fff'}}>{state.sla_ms || 1000} ms</span></div>

            <div className="text-secondary mb-2 pb-1" style={{borderBottom: '1px solid #333d4b'}}>FORECAST</div>
            {forecast.length > 0 ? forecast.map((f, i) => (
              <div key={i} className="flex-row justify-between mb-1">
                <span>+{(i+1)*5}s</span> 
                <span style={{color: 'var(--accent-color)'}}>{f.toFixed(1)} RPS</span>
              </div>
            )) : (
              <div className="text-secondary italic mb-4">Awaiting hybrid predictor...</div>
            )}
            <div className="mb-4"></div>

            <div className="text-secondary mb-2 pb-1" style={{borderBottom: '1px solid #333d4b'}}>DECISION ENGINE</div>
            <div className="flex-row justify-between mb-1"><span>SLA Margin</span> <span style={{color: decision.sla_budget_ms > 0 ? 'var(--success-color)' : 'var(--error-color)'}}>{decision.sla_budget_ms > 0 ? '+' : ''}{decision.sla_budget_ms} ms</span></div>
            <div className="flex-row justify-between mb-1"><span>Expected Wait</span> <span style={{color: '#fff'}}>{decision.expected_wait_ms} ms</span></div>
            <div className="flex-row justify-between mb-1"><span>Estimated Cost</span> <span style={{color: '#fff'}}>{decision.estimated_cost?.toFixed(2)}</span></div>
            <div className="flex-row justify-between mb-4"><span>Priority</span> <span style={{color: '#fff'}}>{priority}</span></div>

            <div className="text-center my-4">
              <div style={{color: 'var(--accent-secondary)'}}>↓</div>
            </div>

            <div className="text-center">
              <div style={{ 
                border: `1px solid ${decision.action.includes('PREWARM') ? 'var(--accent-color)' : decision.action.includes('RECLAIM') ? 'var(--error-color)' : 'var(--warning-color)'}`, 
                display: 'inline-block', 
                padding: '0.5rem 2rem', 
                borderRadius: '4px', 
                fontWeight: 'bold',
                color: decision.action.includes('PREWARM') ? 'var(--accent-color)' : decision.action.includes('RECLAIM') ? 'var(--error-color)' : 'var(--warning-color)'
              }}>
                → {decision.action} {decision.available_containers ? `(Target: ${decision.available_containers})` : ''}
              </div>
            </div>
            
          </div>
        </div>

        {/* Right Side: Context and Reason */}
        <div>
          <div className="card mb-4">
            <h2>Decision Context</h2>
            <div className="mono mt-4">
              <div className="flex-row justify-between mb-2"><span>Target Function:</span> <span style={{color: 'var(--accent-color)'}}>{decision.function}</span></div>
              <div className="flex-row justify-between mb-2"><span>Action Taken:</span> <span style={{fontWeight: 'bold'}}>{decision.action}</span></div>
              <div className="flex-row justify-between mb-2"><span>Timestamp:</span> <span>{new Date(decision.timestamp * 1000).toLocaleTimeString()}</span></div>
            </div>
          </div>
          
          <div className="card" style={{ borderLeft: '4px solid var(--accent-secondary)' }}>
            <h2>REASON</h2>
            <p className="mt-4 mono" style={{ lineHeight: '1.6', fontSize: '0.95rem', color: '#ccc' }}>
              {decision.reason}
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Scheduler;
