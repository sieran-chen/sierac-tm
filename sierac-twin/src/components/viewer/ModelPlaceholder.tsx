/** Shown when GLB fails to load. Simple placeholder, no photo sphere. */
export default function ModelPlaceholder() {
  return (
    <group>
      <mesh>
        <boxGeometry args={[2, 1.5, 1]} />
        <meshStandardMaterial color="#374151" metalness={0.3} roughness={0.7} />
      </mesh>
    </group>
  );
}
