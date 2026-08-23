import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Functions = () => {
  const [functions, setFunctions] = useState([]);
  const [selectedFunc, setSelectedFunc] = useState(null);

  useEffect(() => {
    const fetchFuncs = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/functions');
        setFunctions(res.data);
        if (selectedFunc) {
          const updated = res.data.find(f => f.id === selectedFunc.id);
          if (updated) setSelectedFunc(updated);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchFuncs();
    const interval = setInterval(fetchFuncs, 1000);
    return () => clearInterval(interval);
  }, [selectedFunc]);

  return (
    <div>
      <h1>Functions</h1>
      <p className="subtitle">What is happening to my serverless functions/requests?</p>

      <div className="card mb-8">
        <table className="data-table">
          <thead>
            <tr>
              <th>Function</th>
              <th>RPS</th>
              <th>P50</th>
              <th>P99</th>
              <th>SLA</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {functions.map(f => (
              <tr 
                key={f.id} 
                onClick={() => setSelectedFunc(f)}
                style={{ cursor: 'pointer', backgroundColor: selectedFunc?.id === f.id ? 'rgba(255,255,255,0.05)' : '' }}
              >
                <td style={{ color: 'var(--accent-color)' }}>{f.id}</td>
                <td>{f.rps}</td>
                <td>{f.p50_ms} ms</td>
                <td>{f.p99_ms} ms</td>
                <td>{f.sla_pct}%</td>
                <td>
                  <span className={`status-badge ${f.status === 'Healthy' ? 'healthy' : 'warning'}`}>
                    {f.status}
                  </span>
                </td>
              </tr>
            ))}
            {functions.length === 0 && <tr><td colSpan="6" className="text-secondary text-center">No functions found</td></tr>}
          </tbody>
        </table>
      </div>

      {selectedFunc && (
        <div className="card mt-8">
          <h2>Request Lifecycle: {selectedFunc.id}</h2>
          <div className="grid-2 mt-4">
            <div>
              <div className="mono mb-4">
                <div style={{ paddingLeft: '1rem', borderLeft: '2px solid var(--border-color)'}}>
                  <div>ARRIVED</div>
                  <div className="text-secondary text-sm">↓</div>
                  <div>QUEUED</div>
                  <div className="text-secondary text-sm">↓</div>
                  <div>ASSIGNED</div>
                  <div className="text-secondary text-sm">↓</div>
                  <div>CONTAINER STARTED</div>
                  <div className="text-secondary text-sm">↓</div>
                  <div>EXECUTING</div>
                  <div className="text-secondary text-sm">↓</div>
                  <div>COMPLETED</div>
                </div>
              </div>
            </div>
            
            {selectedFunc.recent_requests && selectedFunc.recent_requests.length > 0 ? (
              <div className="mono">
                <h3 className="text-secondary mb-2" style={{ fontSize: '0.85rem' }}>LATEST REQUEST TIMING</h3>
                {(() => {
                  const req = selectedFunc.recent_requests[0];
                  const qTime = req.assigned_at ? ((req.assigned_at - req.created_at) * 1000).toFixed(0) : 0;
                  const cTime = req.is_cold_start ? ((req.started_at - req.assigned_at) * 1000).toFixed(0) : 0;
                  const eTime = req.completed_at ? ((req.completed_at - req.started_at) * 1000).toFixed(0) : 0;
                  const total = req.completed_at ? ((req.completed_at - req.created_at) * 1000).toFixed(0) : 0;
                  
                  return (
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '4px' }}>
                      <div className="flex-row justify-between mb-1"><span>Queue</span><span>{qTime} ms</span></div>
                      <div className="flex-row justify-between mb-1"><span>Cold start</span><span>{cTime} ms</span></div>
                      <div className="flex-row justify-between mb-1"><span>Execution</span><span>{eTime} ms</span></div>
                      <div style={{ borderTop: '1px dashed var(--border-color)', margin: '0.5rem 0' }}></div>
                      <div className="flex-row justify-between" style={{ color: 'var(--accent-color)'}}><span>Total</span><span>{total} ms</span></div>
                    </div>
                  )
                })()}
              </div>
            ) : (
              <div className="text-secondary">No recent requests</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Functions;
