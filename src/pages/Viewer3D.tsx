import { useParams, useSearchParams, Link } from 'react-router-dom';
import ThreeViewer from '@/components/ThreeViewer';
import { Button } from '@/components/ui/button';

const Viewer3D = () => {
  const { deviceId } = useParams();
  const [params] = useSearchParams();
  const lat = Number(params.get('lat') ?? '37.7749');
  const lon = Number(params.get('lon') ?? '-122.4194');

  return (
    <main className="container mx-auto py-8 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">3D View — {deviceId}</h1>
        <Button asChild variant="soft">
          <Link to="/">Back to Map</Link>
        </Button>
      </header>

      <section aria-label="3D NeRF viewer" className="space-y-4">
        <p className="text-muted-foreground">
          Viewing region near lat {lat.toFixed(4)}, lon {lon.toFixed(4)}. This demo renders a stylized tree placeholder.
        </p>
        <ThreeViewer />
      </section>
    </main>
  );
};

export default Viewer3D;
