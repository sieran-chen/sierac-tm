import { Html } from "@react-three/drei";
import { sceneToWorld } from "@/config/coordinateSystem";
import * as THREE from "three";

const AXIS_LENGTH = 18;
const LABEL_OFFSET = 20;
const TICK_INTERVAL = 2;
const MAJOR_TICK_INTERVAL = 4;
const TICK_SIZE = 0.45;
const MAJOR_TICK_SIZE = 0.8;

type AxisConfig = {
  key: string;
  color: string;
  positiveLabel: string;
  negativeLabel: string;
  vector: { front: number; up: number; right: number };
  tickAxis: "up" | "right";
};

const axes: AxisConfig[] = [
  {
    key: "front",
    color: "#ef4444",
    positiveLabel: "+前 FRONT",
    negativeLabel: "-前 / +后 BACK",
    vector: { front: 1, up: 0, right: 0 },
    tickAxis: "up",
  },
  {
    key: "right",
    color: "#3b82f6",
    positiveLabel: "+右 RIGHT",
    negativeLabel: "-右 / +左 LEFT",
    vector: { front: 0, up: 0, right: 1 },
    tickAxis: "up",
  },
  {
    key: "up",
    color: "#22c55e",
    positiveLabel: "+上 UP",
    negativeLabel: "-上 / +下 DOWN",
    vector: { front: 0, up: 1, right: 0 },
    tickAxis: "right",
  },
];

function makeLine(points: THREE.Vector3[], color: string) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color });
  return new THREE.Line(geometry, material);
}

function axisPoint(
  vector: AxisConfig["vector"],
  scalar: number,
): [number, number, number] {
  return sceneToWorld(
    vector.front * scalar,
    vector.up * scalar,
    vector.right * scalar,
  );
}

function tickPoint(
  vector: AxisConfig["vector"],
  tickAxis: AxisConfig["tickAxis"],
  scalar: number,
  tickScalar: number,
): [number, number, number] {
  const front = vector.front * scalar;
  const up = vector.up * scalar + (tickAxis === "up" ? tickScalar : 0);
  const right = vector.right * scalar + (tickAxis === "right" ? tickScalar : 0);
  return sceneToWorld(front, up, right);
}

export default function EquipmentAxes() {
  return (
    <group>
      {axes.map((axis) => {
        const positiveEnd = axisPoint(axis.vector, AXIS_LENGTH);
        const negativeEnd = axisPoint(axis.vector, -AXIS_LENGTH);
        const positiveLabelPos = axisPoint(axis.vector, LABEL_OFFSET);
        const negativeLabelPos = axisPoint(axis.vector, -LABEL_OFFSET);
        const axisLine = makeLine(
          [
            new THREE.Vector3(...negativeEnd),
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(...positiveEnd),
          ],
          axis.color,
        );

        const ticks = [];
        for (let value = -AXIS_LENGTH; value <= AXIS_LENGTH; value += TICK_INTERVAL) {
          if (value === 0) continue;
          const isMajor = Math.abs(value) % MAJOR_TICK_INTERVAL === 0;
          const tickSize = isMajor ? MAJOR_TICK_SIZE : TICK_SIZE;
          const tickStart = tickPoint(axis.vector, axis.tickAxis, value, -tickSize);
          const tickEnd = tickPoint(axis.vector, axis.tickAxis, value, tickSize);

          ticks.push(
            <primitive
              key={`${axis.key}-tick-${value}`}
              object={makeLine(
                [new THREE.Vector3(...tickStart), new THREE.Vector3(...tickEnd)],
                axis.color,
              )}
            />,
          );

          if (isMajor) {
            const labelPos = tickPoint(axis.vector, axis.tickAxis, value, tickSize + 0.6);
            ticks.push(
              <Html
                key={`${axis.key}-label-${value}`}
                position={labelPos}
                center
                style={{
                  color: axis.color,
                  fontSize: 10,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  textShadow: "0 0 4px rgba(0,0,0,0.8)",
                  pointerEvents: "none",
                  userSelect: "none",
                }}
              >
                {value}
              </Html>,
            );
          }
        }

        return (
          <group key={axis.key}>
            <primitive object={axisLine} />
            {ticks}
            <mesh position={positiveEnd}>
              <coneGeometry args={[0.35, 1.1, 8]} />
              <meshBasicMaterial color={axis.color} />
            </mesh>
            <mesh position={negativeEnd}>
              <coneGeometry args={[0.35, 1.1, 8]} />
              <meshBasicMaterial color={axis.color} />
            </mesh>
            <Html
              position={positiveLabelPos}
              center
              style={{
                color: axis.color,
                fontSize: 11,
                fontWeight: 700,
                whiteSpace: "nowrap",
                textShadow: "0 0 4px rgba(0,0,0,0.8)",
                pointerEvents: "none",
                userSelect: "none",
              }}
            >
              {axis.positiveLabel}
            </Html>
            <Html
              position={negativeLabelPos}
              center
              style={{
                color: axis.color,
                fontSize: 11,
                fontWeight: 700,
                whiteSpace: "nowrap",
                textShadow: "0 0 4px rgba(0,0,0,0.8)",
                pointerEvents: "none",
                userSelect: "none",
              }}
            >
              {axis.negativeLabel}
            </Html>
          </group>
        );
      })}
      <Html
        position={[0, 0.8, 0]}
        center
        style={{
          color: "#e5e7eb",
          fontSize: 11,
          fontWeight: 700,
          whiteSpace: "nowrap",
          textShadow: "0 0 4px rgba(0,0,0,0.8)",
          pointerEvents: "none",
          userSelect: "none",
        }}
      >
        原点 0
      </Html>
    </group>
  );
}
