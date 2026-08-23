import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Overview = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/overview');
        setData(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    
    fetchOverview();
    const interval = setInterval(fetchOverview, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return <div className="p-4 text-secondary">Connecting to LambdaX...</div>;

  return (
    <div>
      <h1>Overview</h1>
      <p className="subtitle">What is LambdaX doing right now?</p>

      <div className="grid-3 mb-4">
        <div className="card stat-card">
          <span className="stat-label">Requests/sec</span>
          <span className="stat-value">{data.rps}</span>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Active Containers</span>
          <span className="stat-value">{data.active_containers}</span>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Queue Size</span>
          <span className="stat-value">{data.queue_size}</span>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Cold Starts</span>
          <span className="stat-value">{data.cold_start_pct}%</span>
        </div>
        <div className="card stat-card">
          <span className="stat-label">SLA Compliance</span>
          <span className="stat-value" style={{ color: data.sla_compliance >= 90 ? 'var(--success-color)' : 'var(--warning-color)'}}>
            {data.sla_compliance}%
          </span>
        </div>
        <div className="card stat-card">
          <span className="stat-label">P99 Latency</span>
          <span className="stat-value">{data.p99_latency} ms</span>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Demand vs Capacity</h2>
          <div className="mt-4" style={{ fontFamily: 'var(--font-mono)' }}>
            <div className="flex-row justify-between mb-2">
              <span>Demand</span>
              <span className="text-accent">{data.rps} RPS</span>
            </div>
            <div style={{ height: '8px', backgroundColor: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${Math.min(100, (data.rps / 50) * 100)}%`, height: '100%', backgroundColor: 'var(--accent-color)' }}></div>
            </div>
            
            <div className="flex-row justify-between mb-2 mt-4">
              <span>Capacity</span>
              <span className="text-success">{data.active_containers} Containers</span>
            </div>
            <div style={{ height: '8px', backgroundColor: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${Math.min(100, (data.active_containers / 20) * 100)}%`, height: '100%', backgroundColor: 'var(--success-color)' }}></div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2>Recent Decisions</h2>
          <table className="data-table mt-4">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Function</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_decisions.map((dec, i) => (
                <tr key={i}>
                  <td>{new Date(dec.timestamp * 1000).toLocaleTimeString()}</td>
                  <td style={{ color: dec.action.includes('PREWARM') ? 'var(--accent-color)' : dec.action.includes('RECLAIM') ? 'var(--error-color)' : 'var(--warning-color)' }}>
                    {dec.action} {dec.target_containers ? (dec.action === 'RECLAIM' ? `-${dec.target_containers}` : `+${dec.target_containers}`) : ''}
                  </td>
                  <td>{dec.function_id}</td>
                </tr>
              ))}
              {data.recent_decisions.length === 0 && (
                <tr><td colSpan="3" className="text-secondary">No recent decisions</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Overview;
