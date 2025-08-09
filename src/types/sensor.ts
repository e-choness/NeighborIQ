export interface Location {
  lat: number;
  lon: number;
  elevation_m?: number | null;
}

export interface Battery {
  voltage_v: number;
  percent: number;
}

export interface Radio {
  rssi_dbm: number;
  snr_db: number;
}

export interface Microclimate {
  temperature_c: number;
  relative_humidity_pct: number;
  air_pressure_hpa: number;
  soil_moisture_pct: number | null;
}

export interface AirQuality {
  voc_ppb: number;
  co_ppm: number;
  pm1_ugm3: number;
  pm2_5_ugm3: number;
  pm10_ugm3: number;
  iaq_index: number; // 0-100 (higher better)
}

export interface SmokeIndex {
  smoke_probability: number; // 0-1
  smoke_confidence: number; // 0-1
}

export interface Health {
  last_calibrated_utc: string;
  error_flags: string[];
  uptime_seconds: number;
}

export interface MetaInfo {
  sensor_type: string;
  manufacturer: string;
  notes: string;
}

export interface SensorReading {
  device_id: string;
  timestamp_utc: string;
  firmware_version: string;
  location: Location;
  battery: Battery;
  radio: Radio;
  microclimate: Microclimate;
  air_quality: AirQuality;
  smoke_index: SmokeIndex;
  health: Health;
  meta: MetaInfo;
}

export interface PersonaOutput {
  persona_name: string;
  health_score: number; // 0-100
  summary_short: string;
  detailed_explanation: string;
  recommended_actions: string[];
  confidence: number; // 0-1
}
