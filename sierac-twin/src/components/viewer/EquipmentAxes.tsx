import { Html } from "@react-three/drei";
import { sceneToWorld } from "@/config/coordinateSystem";
import * as THREE from "three";

const AXIS_LENGTH = 15;
const LABEL_OFFSET = 16;

const axes = [
  { name: "+前 FRONT", color: "#ef4444", front: 1, up: 0, right: 0 },
  { name: "+右 RIGHT", color: "#3b82f6", front: 0, up: 0, right: 1 },
  { name: "+上 UP",    color: "#22c55e", front: 0, up: 1, right: 0 },
] as const;

export default function EquipmentAxes() {
  return (
    <group>
      {axes.map(({ name, color, front, up, right }) => {
        const end = sceneToWorld(
          front * AXIS_LENGTH,
          up * AXIS_LENGTH,
          right * AXIS_LENGTH,
        );
        const labelPos = sceneToWorld(
          front * LABEL_OFFSET,
          up * LABEL_OFFSET,
          right * LABEL_OFFSET,
        );
        const points = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(...end)];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);

        return (
          <group key={name}>
            <line geometry={geometry}>
              <lineBasicMaterial color={color} linewidth={2} />
            </line>
            <mesh position={end}>
              <coneGeometry args={[0.3, 1, 8]} />
              <meshBasicMaterial color={color} />
            </mesh>
            <Html
              position={labelPos}
              center
              style={{
                color,
                fontSize: 11,
                fontWeight: 600,
                whiteSpace: "nowrap",
                textShadow: "0 0 4px rgba(0,0,0,0.8)",
                pointerEvents: "none",
                userSelect: "none",
              }}
            >
              {name}
            </Html>
          </group>
        );
      })}
    </group>
  );
}
