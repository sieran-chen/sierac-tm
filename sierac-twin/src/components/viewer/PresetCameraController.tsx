import { useFrame, useThree } from "@react-three/fiber";
import { useRef, useContext, useEffect } from "react";
import * as THREE from "three";
import { PresetContext } from "./PresetCameraContext";
import type { PresetId } from "./PresetViews";

const PRESET_POSITIONS: Record<PresetId, [number, number, number]> = {
  front: [0, 1, 6],
  back: [0, 1, -6],
  left: [-6, 1, 0],
  right: [6, 1, 0],
  top: [0, 6, 1],
};

export default function PresetCameraController() {
  const { camera } = useThree();
  const context = useContext(PresetContext);
  const targetPos = useRef<THREE.Vector3 | null>(null);

  useEffect(() => {
    if (!context?.preset) return;
    const pos = PRESET_POSITIONS[context.preset];
    if (pos) targetPos.current = new THREE.Vector3(pos[0], pos[1], pos[2]);
  }, [context?.preset]);

  useFrame(() => {
    if (!targetPos.current || !context?.setPreset) return;
    camera.position.lerp(targetPos.current, 0.08);
    if (camera.position.distanceTo(targetPos.current) < 0.1) {
      camera.position.copy(targetPos.current);
      targetPos.current = null;
      context.setPreset(null);
    }
  });

  return null;
}
