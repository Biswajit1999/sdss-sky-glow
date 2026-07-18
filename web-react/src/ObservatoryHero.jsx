import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState } from 'react';

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  return reduced;
}

function FrameTicker({ reducedMotion }) {
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    if (reducedMotion) {
      invalidate();
      return undefined;
    }
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') invalidate();
    }, 1000 / 20);
    return () => window.clearInterval(timer);
  }, [invalidate, reducedMotion]);

  return null;
}

function StarPoints() {
  const positions = useMemo(
    () => Array.from({ length: 34 }, (_, index) => ({
      x: Math.sin(index * 2.17) * 4.8,
      y: 1.2 + ((index * 1.73) % 4.1),
      z: -2.5 - ((index * 0.91) % 2.8),
      size: index % 6 === 0 ? 0.035 : 0.018,
    })),
    [],
  );

  return positions.map((star, index) => (
    <mesh key={index} position={[star.x, star.y, star.z]}>
      <sphereGeometry args={[star.size, 5, 5]} />
      <meshBasicMaterial color={index % 5 === 0 ? '#b8ffe0' : '#dff7ed'} />
    </mesh>
  ));
}

function DomeModel({ reducedMotion }) {
  const dome = useRef();
  const telescope = useRef();

  useFrame((state) => {
    if (reducedMotion) return;
    const elapsed = state.clock.elapsedTime;
    if (dome.current) dome.current.rotation.y = -0.16 + Math.sin(elapsed * 0.22) * 0.09;
    if (telescope.current) telescope.current.rotation.z = -0.92 + Math.sin(elapsed * 0.28) * 0.025;
  });

  return (
    <group position={[0, -1.1, 0]} rotation={[0, -0.15, 0]}>
      <mesh position={[0, -0.18, 0]}>
        <cylinderGeometry args={[1.78, 1.9, 0.68, 28]} />
        <meshStandardMaterial color="#aebbb2" metalness={0.28} roughness={0.7} />
      </mesh>
      <group ref={dome}>
        <mesh position={[0, 0.15, 0]}>
          <sphereGeometry args={[1.72, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial color="#d5ddd7" metalness={0.38} roughness={0.56} />
        </mesh>
        <mesh position={[0, 1.0, 1.48]}>
          <boxGeometry args={[0.42, 1.58, 0.1]} />
          <meshStandardMaterial color="#06110d" roughness={0.82} />
        </mesh>
        <mesh position={[0, 1.95, 0.8]} rotation={[-0.48, 0, 0]}>
          <boxGeometry args={[0.42, 0.85, 0.1]} />
          <meshStandardMaterial color="#06110d" roughness={0.82} />
        </mesh>
      </group>
      <group ref={telescope} position={[0, 0.72, 0.14]} rotation={[0, 0, -0.92]}>
        <mesh position={[0, 0.78, 0]}>
          <cylinderGeometry args={[0.22, 0.28, 1.7, 14]} />
          <meshStandardMaterial color="#2b4137" metalness={0.45} roughness={0.46} />
        </mesh>
        <mesh position={[0, 1.66, 0]}>
          <cylinderGeometry args={[0.31, 0.31, 0.12, 16]} />
          <meshStandardMaterial color="#8fcbae" metalness={0.3} roughness={0.5} />
        </mesh>
        <mesh position={[0, -0.15, 0]}>
          <cylinderGeometry args={[0.12, 0.16, 0.28, 12]} />
          <meshStandardMaterial color="#1b2c24" metalness={0.5} roughness={0.42} />
        </mesh>
      </group>
      <mesh position={[0, -0.55, 0]}>
        <cylinderGeometry args={[2.25, 2.4, 0.22, 30]} />
        <meshStandardMaterial color="#12261d" roughness={0.9} />
      </mesh>
    </group>
  );
}

export default function ObservatoryHero() {
  const reducedMotion = useReducedMotion();

  return (
    <figure className="observatory-visual w-full overflow-hidden border border-emerald-300/15 bg-[#020806]/70 shadow-2xl shadow-black/30">
      <div className="h-[23rem] md:h-[27rem]" aria-label="Animated stylized ground-telescope observatory illustration">
        <Canvas
          camera={{ position: [4.2, 2.5, 6.8], fov: 43 }}
          dpr={[1, 1.5]}
          frameloop="demand"
          gl={{ antialias: true, powerPreference: 'low-power' }}
        >
          <color attach="background" args={['#020806']} />
          <fog attach="fog" args={['#020806', 7, 13]} />
          <ambientLight intensity={0.75} />
          <directionalLight position={[3, 5, 4]} intensity={2.7} color="#dfffee" />
          <directionalLight position={[-4, 1, 2]} intensity={1.8} color="#31c883" />
          <FrameTicker reducedMotion={reducedMotion} />
          <StarPoints />
          <DomeModel reducedMotion={reducedMotion} />
        </Canvas>
      </div>
      <figcaption className="flex items-center gap-2 border-t border-emerald-300/10 px-4 py-3 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-[#78988a]">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_8px_#6ee7b7]" aria-hidden="true" />
        Stylized illustration, not flight data
      </figcaption>
    </figure>
  );
}
