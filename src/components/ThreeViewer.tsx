import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { Suspense, useRef } from 'react';
import * as THREE from 'three';

function Tree() {
  const crown = useRef<THREE.Mesh>(null!);
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (crown.current) crown.current.position.y = 1.6 + Math.sin(t) * 0.05;
  });
  return (
    <group position={[0, 0, 0]}>
      {/* trunk */}
      <mesh position={[0, 0.75, 0]}>
        <cylinderGeometry args={[0.1, 0.15, 1.5, 12]} />
        <meshStandardMaterial color="#8b5a2b" />
      </mesh>
      {/* crown */}
      <mesh ref={crown} position={[0, 1.6, 0]}>
        <coneGeometry args={[0.8, 1.2, 16]} />
        <meshStandardMaterial color="#2e7d32" />
      </mesh>
    </group>
  );
}

export default function ThreeViewer() {
  return (
    <div className="relative w-full h-[80vh] rounded-lg overflow-hidden border bg-card">
      <Canvas camera={{ position: [3, 2, 3], fov: 55 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <Suspense fallback={null}>
          <Tree />
          <Stars radius={30} depth={10} count={1000} factor={2} fade />
        </Suspense>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
          <planeGeometry args={[50, 50]} />
          <meshStandardMaterial color="#e8e8e8" />
        </mesh>
        <OrbitControls enableDamping />
      </Canvas>
    </div>
  );
}
