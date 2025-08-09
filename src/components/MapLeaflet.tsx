import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { SensorReading } from '@/types/sensor';
import { useMemo } from 'react';

// Fix default icon paths in Vite
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const AnyMapContainer: any = MapContainer as any;
const AnyTileLayer: any = TileLayer as any;

interface Props {
  sensors: SensorReading[];
  center: { lat: number; lon: number };
  zoom?: number;
  onSelect?: (sensor: SensorReading) => void;
}

export default function MapLeaflet({ sensors, center, zoom = 12, onSelect }: Props) {
  const position: [number, number] = useMemo(() => [center.lat, center.lon], [center.lat, center.lon]);

  return (
    <div className="w-full h-[70vh] rounded-lg overflow-hidden border bg-card">
      {/* @ts-ignore - react-leaflet props typing mismatch in this environment */}
      <AnyMapContainer center={position} zoom={zoom} scrollWheelZoom={true} className="w-full h-full">
        {/* @ts-ignore */}
        <AnyTileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {sensors.map((s) => (
          <Marker
            key={s.device_id}
            position={[s.location.lat, s.location.lon]}
            eventHandlers={{ click: () => onSelect?.(s) }}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-semibold">{s.device_id}</div>
                <div>Temp: {s.microclimate.temperature_c}°C</div>
                <div>IAQ: {s.air_quality.iaq_index}</div>
                <div>Battery: {s.battery.percent}%</div>
              </div>
            </Popup>
          </Marker>
        ))}
      </AnyMapContainer>
    </div>
  );
}
