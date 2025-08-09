import { useMemo, useState } from 'react';
import MapLeaflet from '@/components/MapLeaflet';
import { generateSensors } from '@/lib/simulator';
import { generatePersona } from '@/lib/persona';
import { SensorReading, PersonaOutput } from '@/types/sensor';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Link } from 'react-router-dom';
import { toast } from '@/hooks/use-toast';

const Index = () => {
  // San Francisco area center
  const center = { lat: 37.7749, lon: -122.4194 };
  const sensors = useMemo(() => generateSensors(18, center), []);
  const [selected, setSelected] = useState<SensorReading | null>(null);
  const [persona, setPersona] = useState<PersonaOutput | null>(null);

  const onInsights = () => {
    if (!selected) return;
    const p = generatePersona(selected);
    setPersona(p);
    toast({ title: 'Insights ready', description: `${p.persona_name}: ${p.summary_short}` });
  };

  return (
    <main className="container mx-auto py-10 space-y-10">
      <header className="space-y-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Arbor Vista — Tree Sensor Map & 3D NeRF Viewer
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Explore simulated Dryad-like sensors on a live map. Click a sensor to see telemetry, open a 3D view,
          and translate readings into a friendly tree persona.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="hero">Launch Demo</Button>
          <Button variant="soft" onClick={() => setSelected(null)}>Reset Selection</Button>
        </div>
      </header>

      <section>
        <MapLeaflet sensors={sensors} center={center} onSelect={(s) => { setSelected(s); setPersona(null); }} />
      </section>

      <Drawer open={!!selected} onOpenChange={(open) => !open && (setSelected(null), setPersona(null))}>
        <DrawerContent>
          {selected && (
            <div className="max-w-3xl mx-auto w-full">
              <DrawerHeader>
                <DrawerTitle>{selected.device_id}</DrawerTitle>
              </DrawerHeader>
              <div className="grid md:grid-cols-2 gap-4 p-4 pt-0">
                <Card>
                  <CardHeader>
                    <CardTitle>Latest Telemetry</CardTitle>
                    <CardDescription>{new Date(selected.timestamp_utc).toLocaleString()}</CardDescription>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-sm text-muted-foreground">Temperature</div>
                      <div className="text-lg font-medium">{selected.microclimate.temperature_c}°C</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Humidity</div>
                      <div className="text-lg font-medium">{selected.microclimate.relative_humidity_pct}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">IAQ Index</div>
                      <div className="text-lg font-medium">{selected.air_quality.iaq_index}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Battery</div>
                      <div className="text-lg font-medium">{selected.battery.percent}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">VOC</div>
                      <div className="text-lg font-medium">{selected.air_quality.voc_ppb} ppb</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">CO</div>
                      <div className="text-lg font-medium">{selected.air_quality.co_ppm} ppm</div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>AI Persona</CardTitle>
                    <CardDescription>Translate metrics into a friendly tree voice</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {persona ? (
                      <div className="space-y-2">
                        <div className="text-sm uppercase tracking-wide text-muted-foreground">{persona.persona_name}</div>
                        <div className="text-lg font-semibold">Health Score: {persona.health_score}</div>
                        <p className="text-sm">{persona.summary_short}</p>
                        <ul className="list-disc pl-5 text-sm space-y-1">
                          {persona.recommended_actions.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">Click "Get Insights" to generate persona.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
              <DrawerFooter>
                <div className="flex items-center gap-3">
                  <Button variant="hero" asChild>
                    <Link to={`/viewer/${selected.device_id}?lat=${selected.location.lat}&lon=${selected.location.lon}`}>
                      Open 3D View
                    </Link>
                  </Button>
                  <Button variant="soft" onClick={onInsights}>Get Insights</Button>
                </div>
              </DrawerFooter>
            </div>
          )}
        </DrawerContent>
      </Drawer>
    </main>
  );
};

export default Index;
