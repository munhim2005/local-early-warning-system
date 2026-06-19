import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Database, MapPin, Building2, Server, Key, Save, Plus, Trash2, Navigation } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function AdminPanel() {
  const [bunkerForm, setBunkerForm] = useState({
    name: '',
    latitude: '',
    longitude: '',
    capacity: ''
  });
  
  const [configForm, setConfigForm] = useState({
    sources: {
      usgs: true,
      nasa_eonet: true,
      gdacs: true
    }
  });
  
  const [bunkers, setBunkers] = useState([]);
  const [bunkerStatus, setBunkerStatus] = useState(null);
  const [configStatus, setConfigStatus] = useState(null);
  
  const [locatorForm, setLocatorForm] = useState({ latitude: '', longitude: '' });
  const [nearestBunker, setNearestBunker] = useState(null);
  const [locatorStatus, setLocatorStatus] = useState(null);

  useEffect(() => {
    fetchBunkers();
  }, []);

  const fetchBunkers = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/bunkers/`);
      setBunkers(res.data);
    } catch (error) {
      console.error('Error fetching bunkers:', error);
    }
  };

  const handleBunkerChange = (e) => {
    const { name, value } = e.target;
    setBunkerForm({ ...bunkerForm, [name]: value });
  };

  const handleSourceToggle = (sourceId) => {
    setConfigForm(prev => ({
      ...prev,
      sources: {
        ...prev.sources,
        [sourceId]: !prev.sources[sourceId]
      }
    }));
  };

  const handleLocatorChange = (e) => {
    const { name, value } = e.target;
    setLocatorForm({ ...locatorForm, [name]: value });
  };

  const submitBunker = async (e) => {
    e.preventDefault();
    setBunkerStatus('submitting');
    try {
      const payload = {
        name: bunkerForm.name,
        latitude: parseFloat(bunkerForm.latitude),
        longitude: parseFloat(bunkerForm.longitude),
        capacity: parseInt(bunkerForm.capacity, 10)
      };
      
      await axios.post(`${API_BASE_URL}/bunkers/`, payload);
      setBunkerStatus('success');
      setBunkerForm({ name: '', latitude: '', longitude: '', capacity: '' });
      fetchBunkers();
      setTimeout(() => setBunkerStatus(null), 3000);
    } catch (error) {
      console.error('Error adding bunker:', error);
      setBunkerStatus('error');
    }
  };

  const deleteBunker = async (id) => {
    if (!window.confirm("Are you sure you want to remove this bunker from the network?")) return;
    try {
      await axios.delete(`${API_BASE_URL}/bunkers/${id}`);
      fetchBunkers();
    } catch (error) {
      console.error('Error deleting bunker:', error);
    }
  };

  const submitConfig = async (e) => {
    e.preventDefault();
    setConfigStatus('saving');
    try {
      const activeSources = Object.entries(configForm.sources)
        .filter(([_, isEnabled]) => isEnabled)
        .map(([id, _]) => id);
        
      const payload = { sources: activeSources };
      await axios.post(`${API_BASE_URL}/ingestion/config`, payload);
      setConfigStatus('success');
      setTimeout(() => setConfigStatus(null), 3000);
    } catch (error) {
      console.error('Error applying config:', error);
      setConfigStatus('error');
    }
  };

  const submitLocator = async (e) => {
    e.preventDefault();
    setLocatorStatus('searching');
    setNearestBunker(null);
    try {
      const res = await axios.get(`${API_BASE_URL}/bunkers/nearest`, {
        params: { user_lat: locatorForm.latitude, user_lon: locatorForm.longitude, limit: 1 }
      });
      if (res.data && res.data.length > 0) {
        setNearestBunker(res.data[0]);
      } else {
        setNearestBunker({ notFound: true });
      }
      setLocatorStatus('success');
    } catch (error) {
      console.error('Error locating bunker:', error);
      setLocatorStatus('error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-100">Administration</h2>
        <p className="text-sm text-slate-500 mt-1">Manage network nodes and external data configurations.</p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Manage Bunkers */}
        <div className="bg-[#111111] border border-white/10 p-6 rounded-lg shadow-sm flex flex-col h-full">
          <div className="flex items-center space-x-2 mb-6 border-b border-white/5 pb-4">
            <Building2 className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200">Safe Bunkers Network</h3>
          </div>
          
          <div className="overflow-y-auto max-h-[300px] mb-6 space-y-3 flex-1 pr-2">
            {bunkers.length === 0 ? (
              <p className="text-xs text-slate-500 italic text-center py-4">No bunkers registered in the system.</p>
            ) : (
              bunkers.map((bunker) => (
                <div key={bunker.id} className="bg-[#1a1a1a] border border-white/5 p-3 rounded-md flex justify-between items-center">
                  <div>
                    <h4 className="text-sm font-medium text-slate-200">{bunker.name}</h4>
                    <p className="text-[10px] text-slate-500 mt-0.5 uppercase tracking-wider">ID: {bunker.bunker_id} • Cap: {bunker.capacity}</p>
                  </div>
                  <button 
                    onClick={() => deleteBunker(bunker.id)}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    title="Remove Bunker"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
          
          <form onSubmit={submitBunker} className="space-y-4 pt-4 border-t border-white/5 mt-auto">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Register New Bunker</h4>
            <div>
              <input
                type="text"
                name="name"
                value={bunkerForm.name}
                onChange={handleBunkerChange}
                required
                className="w-full bg-[#1a1a1a] border border-white/10 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder-slate-600"
                placeholder="Bunker Name (e.g. F-10 Shelter)"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="number"
                    step="any"
                    name="latitude"
                    value={bunkerForm.latitude}
                    onChange={handleBunkerChange}
                    required
                    className="w-full bg-[#1a1a1a] border border-white/10 rounded-md pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder-slate-600"
                    placeholder="Latitude"
                  />
                </div>
              </div>
              <div>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="number"
                    step="any"
                    name="longitude"
                    value={bunkerForm.longitude}
                    onChange={handleBunkerChange}
                    required
                    className="w-full bg-[#1a1a1a] border border-white/10 rounded-md pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder-slate-600"
                    placeholder="Longitude"
                  />
                </div>
              </div>
            </div>
            
            <div>
              <input
                type="number"
                name="capacity"
                value={bunkerForm.capacity}
                onChange={handleBunkerChange}
                required
                className="w-full bg-[#1a1a1a] border border-white/10 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder-slate-600"
                placeholder="Capacity (e.g. 250)"
              />
            </div>
            
            <div className="pt-2">
              <button
                type="submit"
                disabled={bunkerStatus === 'submitting'}
                className="w-full flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
              >
                {bunkerStatus === 'submitting' ? (
                  <span className="animate-pulse">Registering...</span>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    <span>Register Bunker</span>
                  </>
                )}
              </button>
            </div>
            
            {bunkerStatus === 'success' && (
              <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-emerald-400 text-xs text-center font-medium">
                Bunker successfully registered.
              </div>
            )}
            {bunkerStatus === 'error' && (
              <div className="p-2 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-xs text-center font-medium">
                Failed to register bunker.
              </div>
            )}
          </form>
        </div>

        {/* Right Column */}
        <div className="flex flex-col space-y-6">
          {/* System Configuration Panel */}
          <div className="bg-[#111111] border border-white/10 p-6 rounded-lg shadow-sm h-fit">
          <div className="flex items-center space-x-2 mb-6 border-b border-white/5 pb-4">
            <Server className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200">Data Source Configuration</h3>
          </div>
          
          <form onSubmit={submitConfig} className="space-y-4">
            <div className="space-y-3">
              <label className="block text-xs font-medium text-slate-400 mb-2">Active Data Providers</label>
              
              <label className="flex items-center space-x-3 cursor-pointer group">
                <div className="relative flex items-center justify-center">
                  <input
                    type="checkbox"
                    checked={configForm.sources.usgs}
                    onChange={() => handleSourceToggle('usgs')}
                    className="peer sr-only"
                  />
                  <div className="w-5 h-5 rounded border border-white/20 bg-[#1a1a1a] peer-checked:bg-indigo-500 peer-checked:border-indigo-500 transition-colors"></div>
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 peer-checked:opacity-100 transition-opacity">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  </div>
                </div>
                <span className="text-sm text-slate-300 group-hover:text-slate-100 transition-colors">USGS Earthquake Network</span>
              </label>

              <label className="flex items-center space-x-3 cursor-pointer group">
                <div className="relative flex items-center justify-center">
                  <input
                    type="checkbox"
                    checked={configForm.sources.nasa_eonet}
                    onChange={() => handleSourceToggle('nasa_eonet')}
                    className="peer sr-only"
                  />
                  <div className="w-5 h-5 rounded border border-white/20 bg-[#1a1a1a] peer-checked:bg-indigo-500 peer-checked:border-indigo-500 transition-colors"></div>
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 peer-checked:opacity-100 transition-opacity">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  </div>
                </div>
                <span className="text-sm text-slate-300 group-hover:text-slate-100 transition-colors">NASA EONET Events</span>
              </label>

              <label className="flex items-center space-x-3 cursor-pointer group">
                <div className="relative flex items-center justify-center">
                  <input
                    type="checkbox"
                    checked={configForm.sources.gdacs}
                    onChange={() => handleSourceToggle('gdacs')}
                    className="peer sr-only"
                  />
                  <div className="w-5 h-5 rounded border border-white/20 bg-[#1a1a1a] peer-checked:bg-indigo-500 peer-checked:border-indigo-500 transition-colors"></div>
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 peer-checked:opacity-100 transition-opacity">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  </div>
                </div>
                <span className="text-sm text-slate-300 group-hover:text-slate-100 transition-colors">GDACS Alerts</span>
              </label>
            </div>
            
            <div className="pt-2">
              <button
                type="submit"
                disabled={configStatus === 'saving'}
                className="w-full flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
              >
                {configStatus === 'saving' ? (
                  <span className="animate-pulse">Applying...</span>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>Apply Configuration</span>
                  </>
                )}
              </button>
            </div>

            {configStatus === 'success' && (
              <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-emerald-400 text-xs text-center font-medium">
                Provider network switch successful.
              </div>
            )}
            {configStatus === 'error' && (
              <div className="p-2 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-xs text-center font-medium">
                Failed to apply configuration.
              </div>
            )}
          </form>
        </div>

        {/* Locate Nearest Bunker Panel */}
        <div className="bg-[#111111] border border-white/10 p-6 rounded-lg shadow-sm h-fit">
          <div className="flex items-center space-x-2 mb-6 border-b border-white/5 pb-4">
            <Navigation className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200">Locate Nearest Bunker</h3>
          </div>
          
          <form onSubmit={submitLocator} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">User Latitude</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="number"
                    step="any"
                    name="latitude"
                    value={locatorForm.latitude}
                    onChange={handleLocatorChange}
                    required
                    className="w-full bg-[#1a1a1a] border border-white/10 rounded-md pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder-slate-600"
                    placeholder="e.g. 33.6844"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">User Longitude</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="number"
                    step="any"
                    name="longitude"
                    value={locatorForm.longitude}
                    onChange={handleLocatorChange}
                    required
                    className="w-full bg-[#1a1a1a] border border-white/10 rounded-md pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder-slate-600"
                    placeholder="e.g. 73.0479"
                  />
                </div>
              </div>
            </div>
            
            <div className="pt-2">
              <button
                type="submit"
                disabled={locatorStatus === 'searching'}
                className="w-full flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
              >
                {locatorStatus === 'searching' ? (
                  <span className="animate-pulse">Searching...</span>
                ) : (
                  <>
                    <MapPin className="w-4 h-4" />
                    <span>Find Nearest Bunker</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {nearestBunker && !nearestBunker.notFound && (
            <div className="mt-4 p-4 bg-[#1a1a1a] border border-white/10 rounded-md">
              <h4 className="text-sm font-medium text-emerald-400 mb-1">Closest Match Found</h4>
              <p className="text-sm text-slate-200">{nearestBunker.bunker.name}</p>
              <div className="flex justify-between items-center mt-2 text-xs">
                <span className="text-slate-400">Distance: <span className="text-slate-200 font-medium">{nearestBunker.distance_km} km</span></span>
                <span className="text-slate-400">Capacity: <span className="text-slate-200 font-medium">{nearestBunker.bunker.current_occupants}/{nearestBunker.bunker.capacity}</span></span>
              </div>
            </div>
          )}

          {nearestBunker && nearestBunker.notFound && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-xs text-center font-medium">
              No operational bunkers found.
            </div>
          )}
        </div>
        </div>
        
      </div>
    </div>
  );
}

export default AdminPanel;
