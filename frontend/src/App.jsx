import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { LayoutDashboard, Settings, RefreshCcw, Activity, ShieldAlert, CheckCircle2 } from 'lucide-react';
import MapDashboard from './components/MapDashboard';
import SimulationControl from './components/SimulationControl';
import AdminPanel from './components/AdminPanel';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [alerts, setAlerts] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [isRefreshing, setIsRefreshing] = useState(true);
  
  const fetchCurrentData = useCallback(async (silent = false) => {
    try {
      if (!silent) setIsRefreshing(true);
      const alertsRes = await axios.get(`${API_BASE_URL}/alerts?include_resolved=false&limit=10`);
      setAlerts(alertsRes.data);
      
      const nodesRes = await axios.get(`${API_BASE_URL}/alerts/nodes/status`);
      setNodes(nodesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentData(false);
    // Silent auto-refresh every 10 seconds
    const interval = setInterval(() => fetchCurrentData(true), 10000);
    return () => clearInterval(interval);
  }, [fetchCurrentData]);
  
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'simulation', label: 'Simulation', icon: Activity },
    { id: 'admin', label: 'Administration', icon: Settings }
  ];
  
  const isThreatNear = (alert) => {
    const ISB_LAT = 33.6844;
    const ISB_LON = 73.0479;
    const R = 6371;
    const dLat = (ISB_LAT - alert.source_latitude) * Math.PI / 180;
    const dLon = (ISB_LON - alert.source_longitude) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(alert.source_latitude * Math.PI / 180) * Math.cos(ISB_LAT * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distance = R * c;
    return distance <= (alert.affected_radius_km + 50);
  };

  const activeThreats = alerts.filter(isThreatNear);
  
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-slate-200 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* Header */}
      <header className="bg-[#111111] border-b border-white/5 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-md bg-indigo-500 flex items-center justify-center shadow-sm shadow-indigo-500/20">
              <ShieldAlert className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-slate-100">LOCAL EWS</h1>
              <p className="text-[10px] text-slate-500 tracking-widest uppercase">System Control</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-8">
            <nav className="hidden md:flex space-x-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-white/10 text-white'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                    }`}
                  >
                    <Icon className={`w-4 h-4 mr-2 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                    {tab.label}
                  </button>
                );
              })}
            </nav>

            <div className="h-6 w-px bg-white/10"></div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                {activeThreats.length > 0 ? (
                  <>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                    </span>
                    <span className="text-xs font-medium text-red-400">Threat Active</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-medium text-slate-400">System Normal</span>
                  </>
                )}
              </div>
              <button
                onClick={() => fetchCurrentData(false)}
                disabled={isRefreshing}
                className="p-1.5 rounded-md hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
                title="Manual Refresh"
              >
                <RefreshCcw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </header>
      
      {/* Mobile Nav */}
      <nav className="md:hidden bg-[#111111] border-b border-white/5 sticky top-[65px] z-40 overflow-x-auto">
        <div className="flex p-2 space-x-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center px-4 py-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-slate-400'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="max-w-7xl w-full mx-auto px-4 py-6 flex-1 flex flex-col relative z-10">
        {activeTab === 'dashboard' && <MapDashboard alerts={alerts} nodes={nodes} onAlertClick={fetchCurrentData} />}
        {activeTab === 'simulation' && <SimulationControl />}
        {activeTab === 'admin' && <AdminPanel />}
      </main>
      
      {/* Footer */}
      <footer className="border-t border-white/5 bg-[#111111]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col md:flex-row justify-between items-center text-[11px] text-slate-500">
          <p>© {new Date().getFullYear()} CTPN • Local Emergency Warning System</p>
          <div className="flex items-center space-x-2 mt-2 md:mt-0">
            <div className={`w-1.5 h-1.5 rounded-full ${nodes.filter(n => n.is_online).length > 0 ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
            <p>Nodes Online: <span className="text-slate-300 font-medium">{nodes.filter(n => n.is_online).length}</span> / {nodes.length}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;