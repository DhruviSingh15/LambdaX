import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList, Cell } from 'recharts';

const Experiments = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchExp = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/experiments');
        setData(res.data.phase9);
      } catch (err) {
        console.error(err);
      }
    };
    fetchExp();
  }, []);

  if (!data) return <div className="p-4 text-secondary">Loading experiment data...</div>;

  const paretoData = [
    { name: 'Reactive', cost: 288.7, p99: 4983.8, fill: '#8c92ac' },
    { name: 'EMA', cost: 284.7, p99: 5079.5, fill: '#8c92ac' },
    { name: 'Hybrid', cost: 289.4, p99: 4699.7, fill: '#4ade80' },
    { name: 'MPC', cost: 328.0, p99: 4760.3, fill: '#facc15' },
    { name: 'Adaptive', cost: 264.2, p99: 5532.9, fill: '#66fcf1' }
  ];

  return (
    <div>
      <h1>Phase 9 Research Evidence</h1>
      <p className="subtitle">Does LambdaX actually outperform alternatives?</p>

      <div className="card mb-8">
        <h2>Policy Comparison (Static Benchmark Results)</h2>
        <table className="data-table mt-4">
          <thead>
            <tr>
              <th>Policy</th>
              <th>Cost (Container-s)</th>
              <th>P99 Latency (ms)</th>
              <th>SLA Compliance</th>
              <th>Cold Starts</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Reactive</td>
              <td>288.7</td>
              <td>4983.8</td>
              <td>47.1%</td>
              <td>6.5%</td>
            </tr>
            <tr>
              <td>Predictive (EMA)</td>
              <td>284.7</td>
              <td>5079.5</td>
              <td>47.4%</td>
              <td>6.6%</td>
            </tr>
            <tr>
              <td>Predictive (Hybrid ML)</td>
              <td>289.4</td>
              <td>4699.7</td>
              <td>47.1%</td>
              <td>6.5%</td>
            </tr>
            <tr>
              <td style={{ color: 'var(--warning-color)'}}>Model Predictive Control (MPC)</td>
              <td>{data.mpc_cost.toFixed(1)}</td>
              <td>{data.mpc_p99.toFixed(1)}</td>
              <td>{data.mpc_sla.toFixed(1)}%</td>
              <td>{data.mpc_cs.toFixed(1)}%</td>
            </tr>
            <tr style={{ backgroundColor: 'rgba(102, 252, 241, 0.05)'}}>
              <td style={{ color: 'var(--accent-color)', fontWeight: 'bold'}}>Adaptive (LambdaX)</td>
              <td style={{ fontWeight: 'bold'}}>{data.adaptive_cost.toFixed(1)}</td>
              <td style={{ fontWeight: 'bold'}}>{data.adaptive_p99.toFixed(1)}</td>
              <td style={{ fontWeight: 'bold'}}>{data.adaptive_sla.toFixed(1)}%</td>
              <td style={{ fontWeight: 'bold'}}>{data.adaptive_cs.toFixed(1)}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Pareto Frontier (Cost vs P99)</h2>
          <div style={{ height: '300px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333d4b" />
                <XAxis type="number" dataKey="cost" name="Cost" stroke="#8c92ac" domain={['dataMin - 10', 'dataMax + 10']} label={{ value: 'Cost (s)', position: 'bottom', fill: '#8c92ac' }} />
                <YAxis type="number" dataKey="p99" name="P99" stroke="#8c92ac" domain={['dataMin - 200', 'dataMax + 200']} label={{ value: 'P99 (ms)', angle: -90, position: 'insideLeft', fill: '#8c92ac' }} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#1f2833', border: '1px solid #333d4b' }} />
                <Scatter name="Policies" data={paretoData}>
                  {paretoData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                  <LabelList dataKey="name" position="top" fill="#c5c6c7" fontSize={12} offset={10} />
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h2>What LambdaX adds</h2>
          <div className="mono mt-4 text-center">
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>Forecasting</div>
            <div className="text-secondary my-1" style={{color: 'var(--accent-color)'}}>+</div>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>SLA awareness</div>
            <div className="text-secondary my-1" style={{color: 'var(--accent-color)'}}>+</div>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>Queue awareness</div>
            <div className="text-secondary my-1" style={{color: 'var(--accent-color)'}}>+</div>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>Cost model</div>
            <div className="text-secondary my-1" style={{color: 'var(--accent-color)'}}>+</div>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>Predictive reclamation</div>
            <div className="text-secondary my-2">↓</div>
            <div style={{ color: 'var(--accent-color)', fontWeight: 'bold', fontSize: '1.2rem' }}>Adaptive Scheduler</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Experiments;
