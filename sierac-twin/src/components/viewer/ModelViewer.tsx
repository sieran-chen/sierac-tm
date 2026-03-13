import { useRef, useMemo, useEffect } from "react";
import { Html, useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { SkeletonUtils } from "three-stdlib";
import type { PartMapping, Alarm, TelemetryValue } from "@/types/equipment";
import { sceneToWorld, worldToScene } from "@/config/coordinateSystem";
import { MODEL_CONFIG, KNOWN_PARTS } from "@/config/modelConfig";
import { usePartInteraction } from "@/hooks/usePartInteraction";
import PartInteraction from "./PartInteraction";

function getTelemetryNumber(telemetry: TelemetryValue[], pointId: string): number {
  const p = telemetry.find((t) => t.point_id === pointId);
  const v = p?.value;
  return typeof v === "number" ? v : 0;
}

interface ModelViewerProps {
  modelPath?: string;
  partMapping: PartMapping[];
  alarms: Alarm[];
  telemetry?: TelemetryValue[];
  pathPoints?: {
    start: CalibrationPoint;
    waypoint?: CalibrationPoint | null;
    end: CalibrationPoint;
  };
  calibrationTarget?: "start" | "waypoint" | "end";
  pendingCalibrationPoint?: CalibrationPoint | null;
  onCalibrationPick?: (point: CalibrationPoint) => void;
  onPartClick?: (partName: string, screenPos: { x: number; y: number }) => void;
  onPartHover?: (partName: string | null) => void;
}

type CalibrationPoint = {
  x: number;
  z: number;
  front: number;
  up: number;
  right: number;
};

const ALARM_RED = new THREE.Color(1, 0.1, 0.1);
const ALARM_ORANGE = new THREE.Color(1, 0.5, 0);
const HOVER_EMISSIVE = new THREE.Color(0.2, 0.4, 0.8);
const MODEL_EULER = new THREE.Euler(...MODEL_CONFIG.rotation);
const MODEL_POSITION = new THREE.Vector3(...MODEL_CONFIG.position);
const MODEL_QUATERNION = new THREE.Quaternion().setFromEuler(MODEL_EULER);
const MODEL_QUATERNION_INVERSE = MODEL_QUATERNION.clone().invert();
const DEFAULT_START_POINT = makeWorldPointFromScene(-8, 0, 8.5, false);
const DEFAULT_END_POINT = makeWorldPointFromScene(0, 0, -8.5, true);
const PUSHER_START_SCENE = { front: 0.8, up: 0, right: -18.1 } as const;
const TO_WAYPOINT_PORTION = 0.5;
const PUSH_PORTION = 0.25;

function sceneCoordToAlignedWorld(front: number, up: number, right: number) {
  const [x, y, z] = sceneToWorld(front, up, right);
  return new THREE.Vector3(x, y, z).applyQuaternion(MODEL_QUATERNION).add(MODEL_POSITION);
}

function sceneCoordToWorld(front: number, up: number, right: number) {
  const [x, y, z] = sceneToWorld(front, up, right);
  return new THREE.Vector3(x, y, z).add(MODEL_POSITION);
}

function makeWorldPointFromScene(front: number, up: number, right: number, alignWithModel: boolean) {
  const world = alignWithModel
    ? sceneCoordToAlignedWorld(front, up, right)
    : sceneCoordToWorld(front, up, right);

  return {
    x: world.x,
    z: world.z,
    front,
    up,
    right,
  };
}

function worldPointToScene(point: THREE.Vector3): CalibrationPoint {
  const local = point.clone().sub(MODEL_POSITION).applyQuaternion(MODEL_QUATERNION_INVERSE);
  const scenePoint = worldToScene(local.x, local.y, local.z);

  return {
    x: point.x,
    z: point.z,
    front: Number(scenePoint.front.toFixed(2)),
    up: Number(scenePoint.up.toFixed(2)),
    right: Number(scenePoint.right.toFixed(2)),
  };
}

function formatCoord(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export default function ModelViewer({
  modelPath = MODEL_CONFIG.path,
  partMapping,
  alarms,
  telemetry = [],
  pathPoints,
  calibrationTarget = "end",
  pendingCalibrationPoint = null,
  onCalibrationPick,
  onPartClick,
  onPartHover,
}: ModelViewerProps) {
  const { scene: rawScene } = useGLTF(modelPath);

  // Clone so each mount gets an independent scene graph (useGLTF caches the original).
  // The GLB (roller_reject_clean.glb) has already had duplicate nodes removed at
  // build time, so no runtime visibility patching is needed.
  const scene = useMemo(() => SkeletonUtils.clone(rawScene) as THREE.Group, [rawScene]);

  const groupRef = useRef<THREE.Group>(null);
  const conveyorProductRef = useRef<THREE.Mesh>(null);
  const virtualPusherRef = useRef<THREE.Mesh>(null);
  const startMarkerRef = useRef<THREE.Mesh>(null);
  const waypointMarkerRef = useRef<THREE.Mesh>(null);
  const endMarkerRef = useRef<THREE.Mesh>(null);
  const calibrationMarkerRef = useRef<THREE.Mesh>(null);
  const nativePusherRef = useRef<THREE.Object3D | null>(null);
  const pusherRestPos = useRef<THREE.Vector3 | null>(null);
  const productOffsetRef = useRef(0);
  const productSizeRef = useRef(new THREE.Vector3(120, 80, 120));
  const productWorldSizeRef = useRef(new THREE.Vector3(3.6, 2.4, 2.4));
  const pusherSizeRef = useRef(new THREE.Vector3(130, 150, 20));
  const pusherWorldSizeRef = useRef(new THREE.Vector3(3.9, 4.5, 0.6));
  const prevEmissiveStateRef = useRef<Map<string, string>>(new Map());
  const conveyorSurfaceYRef = useRef<{
    y: number;
    maxY: number;
    centerX: number;
    centerZ: number;
    sizeX: number;
    sizeY: number;
    sizeZ: number;
  } | null>(null);

  useEffect(() => {
    conveyorSurfaceYRef.current = null;
    productOffsetRef.current = 0;
    nativePusherRef.current = null;
    pusherRestPos.current = null;

    scene.updateWorldMatrix(true, true);
    const box = new THREE.Box3().setFromObject(scene);
    const size = new THREE.Vector3();
    box.getSize(size);
    if (size.x > 0.01 && size.y > 0.01) {
      const center = new THREE.Vector3();
      box.getCenter(center);
      conveyorSurfaceYRef.current = {
        y: center.y,
        maxY: box.max.y,
        centerX: center.x,
        centerZ: center.z,
        sizeX: size.x,
        sizeY: size.y,
        sizeZ: size.z,
      };
      productSizeRef.current.set(
        Math.max(size.x * 0.12, 80),
        Math.max(size.y * 0.10, 60),
        Math.max(size.z * 0.08, 80),
      );
      productWorldSizeRef.current.copy(productSizeRef.current).multiplyScalar(MODEL_CONFIG.scale);
      pusherSizeRef.current.set(
        Math.max(size.x * 0.18, 100),
        Math.max(size.y * 0.20, 120),
        Math.max(size.z * 0.025, 18),
      );
      pusherWorldSizeRef.current.copy(pusherSizeRef.current).multiplyScalar(MODEL_CONFIG.scale);
      if (import.meta.env.DEV) {
        console.log("[ModelViewer] scene bbox:", center, "size:", size);
      }
    }

    // Find the native pusher ("剔除") part by its STEP-encoded name
    scene.traverse((child) => {
      if (child.name === KNOWN_PARTS.pusher && !nativePusherRef.current) {
        nativePusherRef.current = child;
        pusherRestPos.current = child.position.clone();
        if (import.meta.env.DEV) {
          console.log("[ModelViewer] Found native pusher:", child.name, "pos:", child.position);
        }
      }
    });
  }, [scene]);

  const partMap = useMemo(() => {
    const map = new Map<string, THREE.Object3D>();
    const allNames: string[] = [];
    scene.traverse((child) => {
      if (child.name) allNames.push(child.name);
      const match = partMapping.find((p) => p.partName === child.name);
      if (match) {
        map.set(child.name, child);
      }
    });
    if (import.meta.env.DEV && allNames.length > 0) {
      console.log("[ModelViewer] scene nodes (for partMapping):", allNames);
    }
    if (map.size === 0) {
      console.warn(
        "[ModelViewer] No parts matched. Model nodes:",
        allNames,
        "Expected partName:",
        partMapping.map((p) => p.partName),
      );
    }
    return map;
  }, [scene, partMapping]);

  const { hoveredPart } = usePartInteraction(partMap, {
    onPartHover,
    onPartClick,
  });

  const hoveredMeshes = useMemo(() => {
    if (!hoveredPart) return [];
    const obj = partMap.get(hoveredPart);
    if (!obj) return [];
    const meshes: THREE.Object3D[] = [];
    obj.traverse((c) => {
      if (c instanceof THREE.Mesh) meshes.push(c);
    });
    return meshes;
  }, [hoveredPart, partMap]);

  const originalEmissives = useMemo(() => {
    const map = new Map<string, THREE.Color>();
    partMap.forEach((obj, name) => {
      obj.traverse((child) => {
        if (child instanceof THREE.Mesh && child.material) {
          const mat = child.material as THREE.MeshStandardMaterial;
          if (!mat.userData.__cloned) {
            child.material = mat.clone();
            (child.material as THREE.MeshStandardMaterial).userData.__cloned = true;
          }
          map.set(`${name}::${child.uuid}`, (child.material as THREE.MeshStandardMaterial).emissive.clone());
        }
      });
    });
    return map;
  }, [partMap]);

  const alarmPartMap = useMemo(() => {
    const map = new Map<string, "critical" | "warning">();
    for (const alarm of alarms) {
      if (!alarm.point_id || alarm.end_time) continue;
      const part = partMapping.find((p) => p.pointIds.includes(alarm.point_id!));
      if (part) {
        const existing = map.get(part.partName);
        if (!existing || (alarm.level === "critical" && existing === "warning")) {
          map.set(part.partName, alarm.level as "critical" | "warning");
        }
      }
    }
    return map;
  }, [alarms, partMapping]);

  const prevTimeRef = useRef<number | null>(null);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    const delta = prevTimeRef.current !== null ? t - prevTimeRef.current : 0.016;
    prevTimeRef.current = t;

      const surface = conveyorSurfaceYRef.current;
      const productMesh = conveyorProductRef.current;
      if (productMesh && surface) {
        const beltSpeed = getTelemetryNumber(telemetry, "belt_speed");
        const productHalfH = productSizeRef.current.y * 0.5;
        const offsetUp = 50;
        const startPathPoint = pathPoints?.start ?? DEFAULT_START_POINT;
        const waypointPathPoint = pathPoints?.waypoint ?? null;
        const endPathPoint = pathPoints?.end ?? DEFAULT_END_POINT;
        const phaseSpeed = Math.max(0.08, beltSpeed / 120);
        productOffsetRef.current = (productOffsetRef.current + phaseSpeed * delta) % 1;
        const cyclePhase = productOffsetRef.current;
        const pusherStartPoint = sceneCoordToAlignedWorld(
          PUSHER_START_SCENE.front,
          PUSHER_START_SCENE.up,
          PUSHER_START_SCENE.right,
        );
        let boxX = startPathPoint.x;
        let boxZ = startPathPoint.z;
        let pusherX = pusherStartPoint.x;
        let pusherZ = pusherStartPoint.z;
        const y = MODEL_CONFIG.position[1] + (surface.y + productHalfH + offsetUp) * MODEL_CONFIG.scale;
        const pusherBaseY =
          MODEL_CONFIG.position[1] + (surface.y + PUSHER_START_SCENE.up) * MODEL_CONFIG.scale;

        if (waypointPathPoint) {
          const pushDeltaX = endPathPoint.x - waypointPathPoint.x;
          const pushDeltaZ = endPathPoint.z - waypointPathPoint.z;
          const pusherEndX = pusherStartPoint.x + pushDeltaX;
          const pusherEndZ = pusherStartPoint.z + pushDeltaZ;

          if (cyclePhase < TO_WAYPOINT_PORTION) {
            const t1 = cyclePhase / TO_WAYPOINT_PORTION;
            boxX = THREE.MathUtils.lerp(startPathPoint.x, waypointPathPoint.x, t1);
            boxZ = THREE.MathUtils.lerp(startPathPoint.z, waypointPathPoint.z, t1);
          } else if (cyclePhase < TO_WAYPOINT_PORTION + PUSH_PORTION) {
            const t2 = (cyclePhase - TO_WAYPOINT_PORTION) / PUSH_PORTION;
            boxX = THREE.MathUtils.lerp(waypointPathPoint.x, endPathPoint.x, t2);
            boxZ = THREE.MathUtils.lerp(waypointPathPoint.z, endPathPoint.z, t2);
            pusherX = THREE.MathUtils.lerp(pusherStartPoint.x, pusherEndX, t2);
            pusherZ = THREE.MathUtils.lerp(pusherStartPoint.z, pusherEndZ, t2);
          } else {
            const retractPortion = 1 - TO_WAYPOINT_PORTION - PUSH_PORTION;
            const t3 = retractPortion > 0 ? (cyclePhase - TO_WAYPOINT_PORTION - PUSH_PORTION) / retractPortion : 1;
            boxX = endPathPoint.x;
            boxZ = endPathPoint.z;
            pusherX = THREE.MathUtils.lerp(pusherStartPoint.x + pushDeltaX, pusherStartPoint.x, t3);
            pusherZ = THREE.MathUtils.lerp(pusherStartPoint.z + pushDeltaZ, pusherStartPoint.z, t3);
          }
        } else {
          boxX = THREE.MathUtils.lerp(startPathPoint.x, endPathPoint.x, cyclePhase);
          boxZ = THREE.MathUtils.lerp(startPathPoint.z, endPathPoint.z, cyclePhase);
        }

        productMesh.scale.copy(productWorldSizeRef.current);
        productMesh.position.set(boxX, y, boxZ);
        productMesh.rotation.set(...MODEL_CONFIG.rotation);
        productMesh.visible = true;

        if (startMarkerRef.current) {
          startMarkerRef.current.position.set(startPathPoint.x, y, startPathPoint.z);
        }
        if (waypointMarkerRef.current) {
          waypointMarkerRef.current.visible = Boolean(waypointPathPoint);
          if (waypointPathPoint) {
            waypointMarkerRef.current.position.set(waypointPathPoint.x, y, waypointPathPoint.z);
          }
        }
        if (endMarkerRef.current) {
          endMarkerRef.current.position.set(endPathPoint.x, y, endPathPoint.z);
        }
        if (calibrationMarkerRef.current) {
          calibrationMarkerRef.current.visible = Boolean(pendingCalibrationPoint);
          if (pendingCalibrationPoint) {
            calibrationMarkerRef.current.position.set(
              pendingCalibrationPoint.x,
              y,
              pendingCalibrationPoint.z,
            );
          }
        }

        const pusherObj = nativePusherRef.current;
        if (pusherObj) {
          pusherObj.visible = false;
        }

        const virtualPusher = virtualPusherRef.current;
        if (virtualPusher) {
          const pushWidth = pusherWorldSizeRef.current.x;
          const pushHeight = pusherWorldSizeRef.current.y;
          virtualPusher.position.set(
            pusherX,
            pusherBaseY + pushHeight * 0.45,
            pusherZ,
          );
          virtualPusher.scale.set(pushWidth, pushHeight, pusherWorldSizeRef.current.z);
          virtualPusher.rotation.set(...MODEL_CONFIG.rotation);
          virtualPusher.visible = true;
        }
      }

    const MIN_SPEED = 0.5;
    partMapping.forEach((part) => {
      if (!part.animation) return;
      const obj = partMap.get(part.partName);
      if (!obj) return;
      const raw = getTelemetryNumber(telemetry, part.animation.pointId);
      const scale = part.animation.speedScale ?? 1;
      const speed = raw > 0 ? raw * scale : MIN_SPEED;
      const axis = part.animation.axis;
      if (part.animation.type === "rotate") {
        (obj.rotation as THREE.Euler)[axis] += speed * delta;
      } else {
        (obj.position as THREE.Vector3)[axis] += speed * delta;
      }
    });

    partMap.forEach((obj, name) => {
      const alarmLevel = alarmPartMap.get(name);
      const isHovered = hoveredPart === name;
      const stateKey = `${name}::${alarmLevel ?? "none"}::${isHovered}`;
      const prevKey = prevEmissiveStateRef.current.get(name);
      const stateChanged = prevKey !== stateKey;
      if (stateChanged) prevEmissiveStateRef.current.set(name, stateKey);

      obj.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) return;
        const mat = child.material as THREE.MeshStandardMaterial;
        const key = `${name}::${child.uuid}`;
        const orig = originalEmissives.get(key);
        if (!orig) return;

        if (!stateChanged && !alarmLevel) return;
        if (alarmLevel === "critical") {
          const intensity = Math.abs(Math.sin(t * 2));
          mat.emissive.copy(ALARM_RED).multiplyScalar(intensity);
        } else if (alarmLevel === "warning") {
          mat.emissive.copy(ALARM_ORANGE).multiplyScalar(0.5);
        } else if (isHovered) {
          mat.emissive.copy(HOVER_EMISSIVE).multiplyScalar(0.15);
        } else {
          mat.emissive.copy(orig);
        }
      });
    });
  });

  return (
    <>
      <group
        ref={groupRef}
        scale={MODEL_CONFIG.scale}
        position={MODEL_CONFIG.position}
        rotation={MODEL_CONFIG.rotation}
      >
        <primitive object={scene} />
      </group>
      {/* Box/pusher are in world coordinates so they match the visible axes exactly. */}
      <mesh ref={conveyorProductRef} castShadow receiveShadow>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#f59e0b" metalness={0.1} roughness={0.8} />
      </mesh>
      <mesh ref={virtualPusherRef} castShadow receiveShadow>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#64748b" metalness={0.45} roughness={0.45} />
      </mesh>
      {onCalibrationPick && (
        <group position={MODEL_CONFIG.position} rotation={MODEL_CONFIG.rotation}>
          <mesh
            rotation={[-Math.PI / 2, 0, 0]}
            position={[0, 0.02, 0]}
            onClick={(event) => {
              event.stopPropagation();
              onCalibrationPick(worldPointToScene(event.point.clone()));
            }}
          >
            <planeGeometry args={[42, 42]} />
            <meshBasicMaterial color="#fde047" transparent opacity={0.08} side={THREE.DoubleSide} />
          </mesh>
        </group>
      )}
      <mesh ref={startMarkerRef}>
        <sphereGeometry args={[0.35, 20, 20]} />
        <meshBasicMaterial color="#10b981" />
        <Html center position={[0, 0.9, 0]} style={{ color: "#10b981", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap", pointerEvents: "none", textShadow: "0 0 4px rgba(0,0,0,0.85)" }}>
          {`起点 (${formatCoord((pathPoints?.start ?? DEFAULT_START_POINT).front)}, ${formatCoord((pathPoints?.start ?? DEFAULT_START_POINT).right)})`}
        </Html>
      </mesh>
      <mesh ref={waypointMarkerRef} visible={Boolean(pathPoints?.waypoint)}>
        <sphereGeometry args={[0.35, 20, 20]} />
        <meshBasicMaterial color="#38bdf8" />
        {pathPoints?.waypoint && (
          <Html center position={[0, 0.9, 0]} style={{ color: "#38bdf8", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap", pointerEvents: "none", textShadow: "0 0 4px rgba(0,0,0,0.85)" }}>
            {`途径点 (${formatCoord(pathPoints.waypoint.front)}, ${formatCoord(pathPoints.waypoint.right)})`}
          </Html>
        )}
      </mesh>
      <mesh ref={endMarkerRef}>
        <sphereGeometry args={[0.35, 20, 20]} />
        <meshBasicMaterial color="#f43f5e" />
        <Html center position={[0, 0.9, 0]} style={{ color: "#f43f5e", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap", pointerEvents: "none", textShadow: "0 0 4px rgba(0,0,0,0.85)" }}>
          {`终点 (${formatCoord((pathPoints?.end ?? DEFAULT_END_POINT).front)}, ${formatCoord((pathPoints?.end ?? DEFAULT_END_POINT).right)})`}
        </Html>
      </mesh>
      <mesh ref={calibrationMarkerRef} visible={false}>
        <sphereGeometry args={[0.42, 20, 20]} />
        <meshBasicMaterial color="#eab308" />
        {pendingCalibrationPoint && (
          <Html center position={[0, 1.05, 0]} style={{ color: "#fde047", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap", pointerEvents: "none", textShadow: "0 0 4px rgba(0,0,0,0.85)" }}>
            {`${calibrationTarget === "start" ? "候选起点" : calibrationTarget === "waypoint" ? "候选途径点" : "候选终点"} (${formatCoord(pendingCalibrationPoint.front)}, ${formatCoord(pendingCalibrationPoint.right)}, ${formatCoord(pendingCalibrationPoint.up)})`}
          </Html>
        )}
      </mesh>
      <PartInteraction selection={hoveredMeshes} />
    </>
  );
}
