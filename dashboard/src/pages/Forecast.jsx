import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Forecast = () => {
  const [data, setData] = useState({ history: [], forecast: [] });

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/dashboard/forecast');
        if (res.data) {
          setData(res.data);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchForecast();
    const interval = setInterval(fetchForecast, 2000);
    return () => clearInterval(interval);
  }, []);

  // Format data for recharts
  const chartData = [];
  let t = -10;
  data.history.forEach(val => {
    chartData.push({ time: t, actual: val, predicted: null });
    t += 1;
  });
  
  // Last history point connects to first forecast point
  if (data.history.length > 0 && data.forecast.length > 0) {
    chartData[chartData.length - 1].predicted = data.history[data.history.length - 1];
  }
  
  t = 1;
  data.forecast.forEach(val => {
    chartData.push({ time: `+${t}s`, actual: null, predicted: val });
    t += 1;
  });

  return (
    <div>
      <h1>Demand Forecast</h1>
      <p className="subtitle">What does LambdaX think will happen next?</p>

      <div className="card mb-8" style={{ height: '400px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333d4b" />
            <XAxis dataKey="time" stroke="#8c92ac" />
            <YAxis stroke="#8c92ac" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2833', border: '1px solid #333d4b' }} />
            <Line type="monotone" dataKey="actual" stroke="#8c92ac" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="predicted" stroke="#66fcf1" strokeWidth={2} strokeDasharray="5 5" dot={{r: 4}} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Model Information</h2>
          <div className="mono mt-4">
            <div className="flex-row justify-between mb-2"><span>Architecture:</span> <span style={{color: 'var(--accent-color)'}}>ARIMA + XGBoost Hybrid</span></div>
            <div className="flex-row justify-between mb-2"><span>Horizon:</span> <span>10 steps (seconds)</span></div>
            <div className="flex-row justify-between mb-2"><span>Current Demand:</span> <span>{data.history.length > 0 ? data.history[data.history.length - 1].toFixed(1) : 0} RPS</span></div>
            {data.forecast.slice(0, 5).map((val, idx) => (
              <div key={idx} className="flex-row justify-between mb-2">
                <span>Predicted +{idx+1}s:</span>
                <span style={{color: 'var(--accent-secondary)'}}>{val.toFixed(1)} RPS</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Hybrid Model Architecture</h2>
          <div className="mono mt-4 text-center">
            <div className="text-secondary mb-1">Historical demand</div>
            <div className="text-secondary my-1">↓</div>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px' }}>ARIMA</div>
            <div className="text-secondary my-1">↓</div>
            <div className="text-secondary mb-1">Baseline forecast</div>
            <div style={{color: 'var(--accent-color)'}}>+</div>
            <div style={{ background: 'rgba(102,252,241,0.1)', color: 'var(--accent-color)', padding: '0.5rem', borderRadius: '4px' }}>XGBoost residual</div>
            <div className="text-secondary my-1">↓</div>
            <div style={{ fontWeight: 'bold' }}>Hybrid forecast</div>
            <div className="text-secondary my-1">↓</div>
            <div className="text-secondary mb-1">Adaptive Scheduler</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Forecast;
