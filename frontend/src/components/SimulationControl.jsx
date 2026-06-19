import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// SIMULATION PIN - In production, this should never be visible!
const SIMULATION_PIN = 'ADMIN_SIM_2026_SECURE';

function SimulationControl() {
  const [enteredPin, setEnteredPin] = useState('');
  const [pinVerified, setPinVerified] = useState(false);
  const [scenarios, setScenarios] = useState([]);
  const [triggering, setTriggering] = useState(false);
  const [result, setResult] = useState(null);
  const [showError, setShowError] = useState(false);
  
  useEffect(() => {
    fetchScenarios();
  }, []);
  
  const fetchScenarios = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/simulation/available-scenarios`);
      setScenarios(res.data.scenarios);
    } catch (error) {
      console.error('Error fetching scenarios:', error);
    }
  };
  
  const handleVerifyPin = () => {
    if (enteredPin === SIMULATION_PIN) {
      setPinVerified(true);
      setShowError(false);
    } else {
      setShowError(true);
      setTimeout(() => setShowError(false), 2000);
    }
  };
  
  const handleTriggerScenario = async (scenarioId) => {
    try {
      setTriggering(true);
      setResult(null);
      
      const res = await axios.post(`${API_BASE_URL}/simulation/trigger`, {
        pin: enteredPin,
        scenario_type: scenarioId,
        parameters: {
          variance_km: 15,
          manual_trigger: true
        }
      });
      
      setResult(res.data);
      
    } catch (error) {
      setResult({
        status: 'error',
        message: error.response?.data?.detail || 'Failed to trigger simulation'
      });
    } finally {
      setTriggering(false);
    }
  };
  
  const handleResetSimulations = async () => {
    if (!confirm('Are you sure you want to reset all simulation data?')) {
      return;
    }
    
    try {
      const res = await axios.post(`${API_BASE_URL}/simulation/reset-all`);
      setResult({
        status: 'success',
        message: 'All simulation events have been reset'
      });
    } catch (error) {
      setResult({
        status: 'error',
        message: 'Failed to reset simulations'
      });
    }
  };
  
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold mb-2">🧪 Simulation Control Panel</h2>
        <p className="text-gray-400">
          Manually trigger disaster scenarios for testing purposes
        </p>
      </div>
      
      {/* PIN Entry (Required for Security) */}
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h3 className="text-xl font-bold mb-4 flex items-center">
          <span className="mr-2">🔐</span> Administrator Access
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Enter Simulation PIN</label>
            <input
              type="password"
              value={enteredPin}
              onChange={(e) => setEnteredPin(e.target.value)}
              placeholder="Enter PIN..."
              className="w-full px-4 py-2 bg-gray-900 border border-gray-600 rounded text-white focus:border-blue-500 outline-none"
              disabled={pinVerified}
            />
            {showError && (
              <p className="text-red-500 text-sm mt-1">Invalid PIN. Please try again.</p>
            )}
          </div>
          
          {!pinVerified && (
            <button
              onClick={handleVerifyPin}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded transition font-bold"
            >
              Verify PIN
            </button>
          )}
          
          {pinVerified && (
            <div className="bg-green-900/50 border border-green-700 p-3 rounded flex items-center">
              <span className="text-green-400 mr-2">✓</span>
              <span className="text-green-300">PIN Verified - Simulation Mode Active</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Scenario Triggers */}
      {pinVerified && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h3 className="text-xl font-bold mb-4 flex items-center">
            <span className="mr-2">🚨</span> Available Scenarios
          </h3>
          
          <div className="space-y-3">
            {scenarios.map((scenario) => (
              <button
                key={scenario.id}
                onClick={() => handleTriggerScenario(scenario.id)}
                disabled={triggering}
                className={`w-full text-left p-4 rounded-lg border-2 transition ${
                  scenario.danger_level === 'critical'
                    ? 'bg-red-900/30 border-red-600 hover:border-red-500'
                    : 'bg-gray-900 border-gray-600 hover:border-blue-500'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-lg">{scenario.name}</h4>
                    <p className="text-sm text-gray-400 capitalize">ID: {scenario.id}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                    scenario.danger_level === 'critical'
                      ? 'bg-red-600 text-white animate-pulse'
                      : scenario.danger_level === 'high'
                        ? 'bg-orange-600 text-white'
                        : 'bg-yellow-600 text-white'
                  }`}>
                    {scenario.danger_level.toUpperCase()}
                  </span>
                </div>
              </button>
            ))}
          </div>
          
          {/* Reset Button */}
          <div className="mt-6 pt-6 border-t border-gray-700">
            <button
              onClick={handleResetSimulations}
              disabled={triggering}
              className="w-full py-3 bg-gray-700 hover:bg-gray-600 rounded transition font-bold disabled:opacity-50"
            >
              🔄 Reset All Simulation Data
            </button>
          </div>
        </div>
      )}
      
      {/* Result Display */}
      {result && (
        <div className={`p-6 rounded-lg border-2 ${
          result.status === 'success'
            ? 'bg-green-900/30 border-green-600'
            : 'bg-red-900/30 border-red-600'
        }`}>
          <h3 className="text-xl font-bold mb-3">
            {result.status === 'success' ? '✓ Success' : '✗ Error'}
          </h3>
          <p className="text-gray-300 mb-4">{result.message}</p>
          
          {result.event_id && (
            <div className="bg-gray-900 p-4 rounded text-sm space-y-2">
              <p><strong>Event ID:</strong> {result.event_id}</p>
              {result.generated_coordinates && (
                <>
                  <p><strong>Latitude:</strong> {result.generated_coordinates.latitude}</p>
                  <p><strong>Longitude:</strong> {result.generated_coordinates.longitude}</p>
                </>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Safety Notice */}
      <div className="bg-yellow-900/30 border border-yellow-700 p-4 rounded-lg">
        <h4 className="font-bold text-yellow-400 mb-2">⚠️ Important Notice</h4>
        <p className="text-sm text-yellow-200">
          This simulation mode is strictly for testing and demonstration purposes only.
          Audio outputs during simulation will play a test tone instead of actual alarms
          to prevent unnecessary panic. Always ensure you're in a controlled environment
          before triggering scenarios.
        </p>
      </div>
    </div>
  );
}

export default SimulationControl;