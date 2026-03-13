import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

export interface PartInteractionCallbacks {
  onPartHover?: (partName: string | null) => void;
  onPartClick?: (partName: string, screenPos: { x: number; y: number }) => void;
}

/**
 * Raycaster-based part interaction. Only parts in partMap respond.
 * Must be used inside Canvas (useThree).
 */
export function usePartInteraction(
  partMap: Map<string, THREE.Object3D>,
  callbacks: PartInteractionCallbacks = {}
) {
  const { camera, gl } = useThree();
  const [hoveredPart, setHoveredPart] = useState<string | null>(null);
  const hoveredRef = useRef<string | null>(null);
  const lastHitRef = useRef<string | null>(null);
  const sameHitCountRef = useRef(0);
  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  const pointer = useMemo(() => new THREE.Vector2(), []);

  const STABLE_FRAMES = 2;

  const handlePointerMove = useCallback(
    (e: PointerEvent) => {
      const canvas = gl.domElement;
      const rect = canvas.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(pointer, camera);
      const meshes: THREE.Mesh[] = [];
      partMap.forEach((obj) => {
        obj.traverse((c) => {
          if (c instanceof THREE.Mesh) meshes.push(c);
        });
      });
      const hits = raycaster.intersectObjects(meshes, false);

      let hitPartName: string | null = null;
      if (hits.length > 0) {
        const hitObj = hits[0].object;
        for (const [name, obj] of partMap) {
          let found = false;
          obj.traverse((c) => {
            if (c === hitObj) found = true;
          });
          if (found) {
            hitPartName = name;
            break;
          }
        }
      }

      if (hitPartName === lastHitRef.current) {
        sameHitCountRef.current += 1;
      } else {
        lastHitRef.current = hitPartName;
        sameHitCountRef.current = 1;
      }

      if (sameHitCountRef.current >= STABLE_FRAMES && hitPartName !== hoveredRef.current) {
        hoveredRef.current = hitPartName;
        setHoveredPart(hitPartName);
        canvas.style.cursor = hitPartName ? "pointer" : "auto";
        callbacks.onPartHover?.(hitPartName);
      }
    },
    [camera, gl, partMap, raycaster, pointer, callbacks.onPartHover]
  );

  const handleClick = useCallback(
    (e: MouseEvent) => {
      if (!hoveredPart) return;
      const canvas = gl.domElement;
      const rect = canvas.getBoundingClientRect();
      callbacks.onPartClick?.(hoveredPart, {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    },
    [hoveredPart, gl, callbacks.onPartClick]
  );

  useEffect(() => {
    const canvas = gl.domElement;
    canvas.addEventListener("pointermove", handlePointerMove);
    canvas.addEventListener("click", handleClick);
    return () => {
      canvas.removeEventListener("pointermove", handlePointerMove);
      canvas.removeEventListener("click", handleClick);
    };
  }, [gl, handlePointerMove, handleClick]);

  return { hoveredPart, handlePointerMove, handleClick };
}
