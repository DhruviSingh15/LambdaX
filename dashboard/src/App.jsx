import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Activity, Code2, Box, GitMerge, LineChart, FlaskConical } from 'lucide-react';
import Overview from './pages/Overview';
import Functions from './pages/Functions';
import Containers from './pages/Containers';
import Scheduler from './pages/Scheduler';
import Forecast from './pages/Forecast';
import Experiments from './pages/Experiments';

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      <nav className="sidebar">
        <div className="brand">LambdaX</div>
        
        <NavLink to="/overview" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
          <Activity size={18} />
          Overview
        </NavLink>
        
        <NavLink to="/functions" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
          <Code2 size={18} />
          Functions
        </NavLink>
        
        <NavLink to="/containers" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
          <Box size={18} />
          Containers
        </NavLink>
        
        <NavLink to="/scheduler" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
          <GitMerge size={18} />
          Scheduler
        </NavLink>
        
        <NavLink to="/forecast" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
          <LineChart size={18} />
          Forecast
        </NavLink>
        
        <NavLink to="/experiments" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
          <FlaskConical size={18} />
          Experiments
        </NavLink>
      </nav>
      
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

const App = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/functions" element={<Functions />} />
          <Route path="/containers" element={<Containers />} />
          <Route path="/scheduler" element={<Scheduler />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/experiments" element={<Experiments />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};

export default App;
