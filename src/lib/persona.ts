import { PersonaOutput, SensorReading } from "@/types/sensor";

export function generatePersona(device: SensorReading): PersonaOutput {
  const soil = device.microclimate.soil_moisture_pct ?? 20;
  const iaq = device.air_quality.iaq_index; // 0-100 higher is better here
  const temp = device.microclimate.temperature_c;
  const battery = device.battery.percent;

  // Health score heuristic (0-100)
  let score = 100;
  // penalize dry soil
  if (soil < 20) score -= (20 - soil) * 1.5;
  // penalize poor IAQ (convert to penalty)
  score -= Math.max(0, 60 - iaq);
  // penalize temperature extremes
  if (temp < 5) score -= (5 - temp) * 2;
  if (temp > 32) score -= (temp - 32) * 1.5;
  // penalize low battery
  if (battery < 25) score -= (25 - battery) * 1.2;

  score = Math.max(0, Math.min(100, Math.round(score)));

  const actions: string[] = [];
  if (soil < 18) actions.push("Increase irrigation over next 48–72h");
  if (battery < 30) actions.push("Schedule battery/solar check");
  if (iaq < 75) actions.push("Inspect nearby air quality sources (traffic, dust)");
  actions.push("Log a visual inspection this week");

  const thirsty = soil < 20;
  const persona_name = thirsty ? "Thirsty Cedar" : "Steady Pine";
  const summary_short = thirsty
    ? "Feeling thirsty; a drink soon would help."
    : "Doing fine overall; keep an eye on trends.";

  const detailed_explanation = `Soil moisture ${device.microclimate.soil_moisture_pct ?? "n/a"}% with IAQ ${iaq}. Temperature is ${temp}°C; battery ${battery}%. These suggest ${thirsty ? "mild drought stress" : "stable conditions"} with ${iaq < 75 ? "moderate air quality impacts" : "no major air concerns"}.`;

  return {
    persona_name,
    health_score: score,
    summary_short,
    detailed_explanation,
    recommended_actions: actions.slice(0, 4),
    confidence: 0.72,
  };
}
