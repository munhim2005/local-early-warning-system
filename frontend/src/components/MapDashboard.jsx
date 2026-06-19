import React, { useEffect, useState } from 'react';
import MapGL, { Layer, GeolocateControl, Popup, Marker, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import axios from 'axios';
import { Building, MapPin, Navigation, Compass, AlertTriangle } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function MapDashboard({ alerts, nodes }) {
  const [viewState, setViewState] = useState({
    latitude: 33.6844,
    longitude: 73.0479,
    zoom: 12,
    bearing: 0,
    pitch: 45
  });
  
  const [bunkers, setBunkers] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [routingData, setRoutingData] = useState(null);
  const [userPosition, setUserPosition] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  
  useEffect(() => {
    fetchBunkers();
    getCurrentLocation();
  }, []);

  const fetchBunkers = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/bunkers`);
      setBunkers(res.data);
    } catch (error) {
      console.error('Error fetching bunkers:', error);
    }
  };

  const getCurrentLocation = () => {
    setIsLocating(true);
    if (!navigator.geolocation) {
      alert("Geolocation not supported");
      setIsLocating(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        const pos = { lat: latitude, lng: longitude };
        setUserPosition(pos);
        await calculateRouteToNearestBunker(latitude, longitude);
        setIsLocating(false);
      },
      (error) => {
        console.error("Geolocation error:", error);
        setIsLocating(false);
      }
    );
  };

  const calculateRouteToNearestBunker = async (lat, lon) => {
    // Only route if there is an active disaster
    if (!alerts || alerts.length === 0) {
      setSelectedLocation(null);
      setRoutingData(null);
      return;
    }

    try {
      const res = await axios.get(`${API_BASE_URL}/alerts/routing`, {
        params: { user_lat: lat, user_lon: lon }
      });
      
      setRoutingData(res.data);
      
      if (res.data.recommended_route) {
        setSelectedLocation({
          lat: lat,
          lng: lon,
          routing: res.data
        });
      }
    } catch (error) {
      console.error('Routing error:', error);
    }
  };

  const handleMapClick = async (evt) => {
    const { lat, lng } = evt.lngLat;
    setUserPosition({ lat, lng });
    await calculateRouteToNearestBunker(lat, lng);
  };

  const calculateThreatZone = (alert) => {
    const coordinates = [];
    const centerLat = alert.source_latitude;
    const centerLon = alert.source_longitude;
    const radius = alert.affected_radius_km || 10;
    const segments = 32;
    
    for (let i = 0; i < segments; i++) {
      const angle = (2 * Math.PI * i) / segments;
      const latOffset = (radius / 111.0) * Math.cos(angle);
      const lonOffset = (radius / (111.0 * Math.cos(centerLat * Math.PI / 180))) * Math.sin(angle);
      coordinates.push([centerLon + lonOffset, centerLat + latOffset]);
    }
    coordinates.push(coordinates[0]);
    return coordinates;
  };
  
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#ef4444'; // red-500
      case 'high': return '#f97316';     // orange-500
      case 'medium': return '#eab308';   // yellow-500
      case 'low': return '#10b981';      // emerald-500
      default: return '#64748b';         // slate-500
    }
  };

  return (
    <div className="space-y-4 relative h-[calc(100vh-160px)] min-h-[500px]">
      <div className="absolute inset-0 rounded-lg overflow-hidden border border-white/10 bg-[#111111]">
        <MapGL
          {...viewState}
          style={{ width: '100%', height: '100%' }}
          onMove={(e) => setViewState(e.viewState)}
          onClick={handleMapClick}
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
          attributionControl={false}
        >
          <GeolocateControl position="top-right" />

          {/* Threat Zones */}
          {alerts.map((alert) => {
            const severityColor = getSeverityColor(alert.severity_level);
            return (
              <Source
                key={`threat-${alert.id}`}
                type="geojson"
                data={{
                  type: 'FeatureCollection',
                  features: [{
                    type: 'Feature',
                    geometry: { type: 'Polygon', coordinates: [calculateThreatZone(alert)] }
                  }]
                }}
              >
                <Layer id={`fill-${alert.id}`} type="fill" paint={{ 'fill-color': severityColor, 'fill-opacity': 0.15 }} />
                <Layer id={`line-${alert.id}`} type="line" paint={{ 'line-color': severityColor, 'line-width': 2, 'line-dasharray': [2, 2] }} />
              </Source>
            );
          })}

          {/* Bunkers */}
          {bunkers.map((bunker) => (
            <Marker key={bunker.id} longitude={bunker.longitude} latitude={bunker.latitude} anchor="bottom">
              <div className="group cursor-pointer">
                <div className="w-8 h-8 bg-[#111111] rounded-md border border-white/20 flex items-center justify-center text-slate-300 group-hover:bg-indigo-600 group-hover:text-white group-hover:border-indigo-500 transition-colors shadow-sm">
                  <Building className="w-4 h-4" />
                </div>
              </div>
            </Marker>
          ))}

          {/* User Position */}
          {userPosition && (
            <Marker longitude={userPosition.lng} latitude={userPosition.lat} anchor="center">
              <div className="relative flex items-center justify-center w-6 h-6">
                <div className="absolute w-full h-full bg-blue-500 rounded-full animate-ping opacity-40"></div>
                <div className="relative w-3 h-3 bg-blue-500 rounded-full border-2 border-[#111111]"></div>
              </div>
            </Marker>
          )}

          {/* Route Line - From User to Recommended Bunker */}
          {userPosition && routingData?.recommended_route?.path_geometry && (
            <Source
              id="route-line"
              type="geojson"
              data={{
                type: 'Feature',
                geometry: routingData.recommended_route.path_geometry
              }}
            >
              <Layer
                id="route-line-layer"
                type="line"
                paint={{
                  'line-color': '#6366f1', // indigo-500
                  'line-width': 4,
                  'line-opacity': 0.8,
                }}
              />
            </Source>
          )}

          {/* Route Info Popup */}
          {selectedLocation && routingData?.recommended_route && (
            <Popup
              longitude={selectedLocation.lng}
              latitude={selectedLocation.lat}
              closeButton={true}
              onClose={() => setSelectedLocation(null)}
              className="bg-transparent"
              anchor="top"
              maxWidth="320px"
            >
              <div className="bg-[#111111] border border-white/10 p-4 rounded-lg w-72 text-slate-200 shadow-xl">
                <div className="flex items-center space-x-2 border-b border-white/5 pb-3 mb-3">
                  <Navigation className="w-4 h-4 text-indigo-400" />
                  <h3 className="font-semibold text-sm">Evacuation Route</h3>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase font-medium">Destination</p>
                    <p className="text-sm font-medium text-slate-200 mt-0.5">
                      {routingData.recommended_route.bunker.name}
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-[#1a1a1a] border border-white/5 p-2 rounded-md">
                      <p className="text-[10px] text-slate-500 uppercase font-medium">Distance</p>
                      <p className="font-medium text-sm text-slate-300 mt-0.5">{routingData.recommended_route.distance_km} km</p>
                    </div>
                    <div className="bg-[#1a1a1a] border border-white/5 p-2 rounded-md">
                      <p className="text-[10px] text-slate-500 uppercase font-medium">Est. Time</p>
                      <p className="font-medium text-sm text-slate-300 mt-0.5">{routingData.recommended_route.estimated_time_minutes} min</p>
                    </div>
                  </div>
                  
                  <div className="bg-emerald-500/10 border border-emerald-500/20 p-2 rounded-md flex justify-between items-center">
                    <p className="text-[10px] text-emerald-500 uppercase font-medium">Capacity</p>
                    <p className="font-semibold text-sm text-emerald-400">
                      {routingData.recommended_route.bunker.capacity - routingData.recommended_route.bunker.current_occupants} spots
                    </p>
                  </div>
                </div>
              </div>
            </Popup>
          )}
        </MapGL>

        {/* Floating Legend */}
        <div className="absolute bottom-6 left-6 bg-[#111111] border border-white/10 p-4 rounded-lg shadow-lg z-10 w-48">
          <h4 className="font-semibold text-xs mb-3 text-slate-400 uppercase tracking-wide border-b border-white/5 pb-2">Legend</h4>
          <div className="space-y-2.5 text-xs font-medium text-slate-300">
            <div className="flex items-center">
              <MapPin className="w-3.5 h-3.5 text-blue-500 mr-2.5" />
              <span>Your Location</span>
            </div>
            <div className="flex items-center">
              <Building className="w-3.5 h-3.5 text-slate-400 mr-2.5" />
              <span>Safe Bunker</span>
            </div>
            <div className="flex items-center">
              <AlertTriangle className="w-3.5 h-3.5 text-red-500 mr-2.5" />
              <span>Active Threat Zone</span>
            </div>
          </div>
        </div>
        
        {/* Status Overlay */}
        {isLocating && (
          <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-[#111111] border border-white/10 px-4 py-2 rounded-md text-slate-300 text-xs font-medium flex items-center shadow-lg z-10">
            <Compass className="w-3.5 h-3.5 animate-spin text-blue-400 mr-2" />
            Locating position...
          </div>
        )}
      </div>
    </div>
  );
}

export default MapDashboard;