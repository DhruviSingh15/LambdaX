import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Containers = () => {
  const [containers, setContainers] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const fetchContainers = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/containers');
        setContainers(res.data);
        if (selected) {
          const updated = res.data.find(c => c.id === selected.id);
          if (updated) setSelected(updated);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchContainers();
    const interval = setInterval(fetchContainers, 1000);
    return () => clearInterval(interval);
  }, [selected]);

  const activeCount = containers.filter(c => ['RUNNING', 'BUSY', 'STARTING', 'IDLE'].includes(c.state)).length;

  return (
    <div>
      <h1>Containers</h1>
      <p className="subtitle">What is happening inside the infrastructure?</p>

      <div className="card mb-8">
        <div className="flex-row justify-between mb-4">
          <h2>Container Pool</h2>
          <span className="mono text-secondary">{activeCount} containers active</span>
        </div>
        
        <div className="container-grid">
          {containers.map(c => (
            <div 
              key={c.id} 
              className="container-node"
              style={{ borderColor: selected?.id === c.id ? 'var(--accent-color)' : '' }}
              onClick={() => setSelected(c)}
            >
              <span className={`state ${c.state}`}>[ {c.state} ]</span>
              <span className="id">{c.function_id}</span>
              <span className="text-secondary text-sm mt-2" style={{fontSize: '0.75rem'}}>{c.id.substring(0,8)}</span>
            </div>
          ))}
          {containers.length === 0 && <div className="text-secondary">No active containers</div>}
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Lifecycle Transitions</h2>
          <div className="mono mt-4 text-center p-4" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
            <span style={{color: 'var(--accent-color)'}}>STARTING</span>
            <span className="text-secondary mx-2"> → </span>
            <span style={{color: 'var(--success-color)'}}>WARM</span>
            <span className="text-secondary mx-2"> → </span>
            <span style={{color: 'var(--warning-color)'}}>BUSY</span>
            <span className="text-secondary mx-2"> → </span>
            <span style={{color: 'var(--text-secondary)'}}>IDLE</span>
            <span className="text-secondary mx-2"> → </span>
            <span style={{color: 'var(--error-color)'}}>RECLAIMED</span>
          </div>
        </div>

        {selected && (
          <div className="card">
            <h2>Container Details</h2>
            <div className="mono mt-4">
              <div className="flex-row justify-between mb-2"><span>ID:</span> <span className="text-secondary">{selected.id}</span></div>
              <div className="flex-row justify-between mb-2"><span>State:</span> <span className={`state ${selected.state}`}>{selected.state}</span></div>
              <div className="flex-row justify-between mb-2"><span>Function:</span> <span>{selected.function_id}</span></div>
              <div className="flex-row justify-between mb-2"><span>Started:</span> <span>{new Date(selected.created_at).toLocaleTimeString()}</span></div>
              <div className="flex-row justify-between mb-2"><span>Last Used:</span> <span>{new Date(selected.last_used_at).toLocaleTimeString()}</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Containers;
