import { useRef, useMemo, useEffect } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { PartMapping, Alarm, TelemetryValue } from "@/types/equipment";
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
  onPartClick?: (partName: string, screenPos: { x: number; y: number }) => void;
  onPartHover?: (partName: string | null) => void;
}

const ALARM_RED = new THREE.Color(1, 0.1, 0.1);
const ALARM_ORANGE = new THREE.Color(1, 0.5, 0);
const HOVER_EMISSIVE = new THREE.Color(0.2, 0.4, 0.8);

export default function ModelViewer({
  modelPath = MODEL_CONFIG.path,
  partMapping,
  alarms,
  telemetry = [],
  onPartClick,
  onPartHover,
}: ModelViewerProps) {
  const { scene } = useGLTF(modelPath);
  const groupRef = useRef<THREE.Group>(null);
  const conveyorProductRef = useRef<THREE.Mesh>(null);
  const nativePusherRef = useRef<THREE.Object3D | null>(null);
  const pusherRestPos = useRef<THREE.Vector3 | null>(null);
  const productOffsetRef = useRef(0);
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

    // FreeCAD flattens assemblies: parts appear both inside _ASM groups
    // AND as loose siblings at root level. Only keep _ASM assembly nodes
    // visible; hide everything else to eliminate overlap.
    const rootGroup = scene.children[0]; // "Unnamed1"
    if (rootGroup) {
      let hidden = 0;
      for (const child of rootGroup.children) {
        if (!child.name.endsWith("_ASM")) {
          child.visible = false;
          hidden++;
        }
      }
      if (import.meta.env.DEV) {
        console.log(`[ModelViewer] Hidden ${hidden}/${rootGroup.children.length} non-ASM root nodes`);
      }
    }

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

      // L-path: feed (+Z) → junction → reject (+X) → hold 2s → reset
      //
      // Coordinate mapping (confirmed by user):
      //   +X = reject section direction (original working motion, keep as-is)
      //   +Z = feed section direction (Y向 in xyrrr.png)
      //   Origin (0,_,0) = junction between feed and reject sections
      //
      // Leg A — feed: X=0 fixed, Z from Z_START (near end, -Y side) → 0 (junction)
      // Leg B — reject: Z=0 fixed, X from 0 → X_EXIT (+X, original motion)
      // Hold 2s at exit, then reset invisible
      const surface = conveyorSurfaceYRef.current;
      const productMesh = conveyorProductRef.current;
      if (productMesh && surface) {
        const beltSpeed = getTelemetryNumber(telemetry, "belt_speed");
        const speed = Math.max(0.3, beltSpeed * 0.03);

        const posY = surface.maxY + 0.05;

        // Coordinates in model-local space (meters, FreeCAD export)
        // Leg A — feed: Z~-0.3 fixed, X from -0.5 → 0 (center)
        // Leg B — reject: X~0 fixed, Z from -0.3 → +0.5
        const X_START    = -0.5;
        const X_MID      =  0.0;
        const Z_FEED     = -0.3;
        const Z_EXIT     =  0.5;

        const LEG_A      = X_MID - X_START;       // 0.5 units
        const LEG_B      = Z_EXIT - Z_FEED;        // 0.8 units
        const HOLD_DIST  = speed * 2.0;
        const RESET_DIST = speed * 0.5;
        const CYCLE      = LEG_A + LEG_B + HOLD_DIST + RESET_DIST;

        productOffsetRef.current += speed * delta;
        if (productOffsetRef.current >= CYCLE) {
          productOffsetRef.current -= CYCLE;
        }
        const off = productOffsetRef.current;

        const pusherObj = nativePusherRef.current;
        const restPos = pusherRestPos.current;
        // Native pusher fires along +Z in model-local coords (push stroke ~0.3m)
        const PUSH_STROKE      = 0.3;
        const PUSH_DURATION    = speed * 0.4;

        if (off < LEG_A) {
          const frac = off / LEG_A;
          productMesh.position.set(X_START + frac * LEG_A, posY, Z_FEED);
          productMesh.visible = true;
          if (pusherObj && restPos) pusherObj.position.copy(restPos);
        } else if (off < LEG_A + PUSH_DURATION) {
          const pushFrac = (off - LEG_A) / PUSH_DURATION;
          // Pusher fires fast (0→30%) then retracts (30→100%)
          let strokeFrac: number;
          if (pushFrac < 0.3) {
            strokeFrac = pushFrac / 0.3;
          } else {
            strokeFrac = 1 - (pushFrac - 0.3) / 0.7;
          }
          if (pusherObj && restPos) {
            pusherObj.position.copy(restPos);
            pusherObj.position.z += strokeFrac * PUSH_STROKE;
          }
          const boxZ = pushFrac < 0.3 ? Z_FEED : Z_FEED + (pushFrac - 0.3) / 0.7 * 0.1;
          productMesh.position.set(X_MID, posY, boxZ);
          productMesh.visible = true;
        } else if (off < LEG_A + LEG_B) {
          const slideStart = Z_FEED + 0.1;
          const frac = (off - LEG_A - PUSH_DURATION) / (LEG_B - PUSH_DURATION);
          const boxZ = slideStart + frac * (Z_EXIT - slideStart);
          productMesh.position.set(X_MID, posY, boxZ);
          productMesh.visible = true;
          if (pusherObj && restPos) pusherObj.position.copy(restPos);
        } else if (off < LEG_A + LEG_B + HOLD_DIST) {
          productMesh.position.set(X_MID, posY, Z_EXIT);
          productMesh.visible = true;
          if (pusherObj && restPos) pusherObj.position.copy(restPos);
        } else {
          productMesh.visible = false;
          if (pusherObj && restPos) pusherObj.position.copy(restPos);
        }
      }

    // Data-driven animation: rotate parts from telemetry.
    // MIN_SPEED ensures visible motion even when equipment is idle/stopped.
    const MIN_SPEED = 0.5; // rad/s
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
        {/* Product box on conveyor (cargo being transported) */}
        <mesh ref={conveyorProductRef} castShadow receiveShadow>
          <boxGeometry args={[0.15, 0.2, 0.12]} />
          <meshStandardMaterial color="#f59e0b" metalness={0.1} roughness={0.8} />
        </mesh>
      </group>
      <PartInteraction selection={hoveredMeshes} />
    </>
  );
}
