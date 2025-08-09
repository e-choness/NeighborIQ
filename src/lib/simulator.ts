import { SensorReading } from "@/types/sensor";

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export function generateSensors(count: number, center: { lat: number; lon: number }): SensorReading[] {
  const now = new Date();
  return Array.from({ length: count }).map((_, i) => {
    const lat = center.lat + rand(-0.2, 0.2);
    const lon = center.lon + rand(-0.2, 0.2);
    const batteryPct = Math.floor(rand(40, 100));
    const temperature_c = Number(rand(10, 30).toFixed(1));
    const rh = Number(rand(25, 85).toFixed(1));
    const pressure = Number(rand(990, 1025).toFixed(1));
    const soil = Math.random() > 0.2 ? Number(rand(5, 40).toFixed(1)) : null;
    const iaq = Math.max(0, Math.min(100, Math.round(100 - rand(0, 25) - (soil ? Math.max(0, 20 - soil) * 0.4 : 0))));

    return {
      device_id: `silva-${(i + 1).toString().padStart(6, "0")}`,
      timestamp_utc: new Date(now.getTime() - rand(0, 60) * 1000).toISOString(),
      firmware_version: "v1.4.2",
      location: { lat, lon, elevation_m: Math.round(rand(200, 1500)) },
      battery: { voltage_v: Number((3.5 + (batteryPct / 100) * 0.8).toFixed(2)), percent: batteryPct },
      radio: { rssi_dbm: Math.round(rand(-95, -60)), snr_db: Number(rand(5, 12).toFixed(1)) },
      microclimate: {
        temperature_c,
        relative_humidity_pct: rh,
        air_pressure_hpa: pressure,
        soil_moisture_pct: soil,
      },
      air_quality: {
        voc_ppb: Math.round(rand(80, 400)),
        co_ppm: Number(rand(0, 1.2).toFixed(2)),
        pm1_ugm3: Number(rand(1, 8).toFixed(1)),
        pm2_5_ugm3: Number(rand(2, 15).toFixed(1)),
        pm10_ugm3: Number(rand(3, 25).toFixed(1)),
        iaq_index: iaq,
      },
      smoke_index: { smoke_probability: Number(rand(0, 0.1).toFixed(3)), smoke_confidence: Number(rand(0, 0.2).toFixed(2)) },
      health: {
        last_calibrated_utc: new Date(now.getTime() - 1000 * 60 * 60 * 24 * rand(5, 30)).toISOString(),
        error_flags: [],
        uptime_seconds: Math.round(rand(100000, 3000000)),
      },
      meta: {
        sensor_type: "wildfire_v2",
        manufacturer: "Dryad-like Co",
        notes: "",
      },
    } satisfies SensorReading;
  });
}
