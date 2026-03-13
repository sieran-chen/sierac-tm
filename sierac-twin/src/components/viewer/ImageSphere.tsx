import { useRef, useLayoutEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { useTexture } from "@react-three/drei";
import * as THREE from "three";
import { VIEW_ANGLES } from "@/config/viewAngles";
import { directionFromDegrees } from "@/utils/spherical";

interface ImageSphereProps {
  onAngleChange?: (threePhi: number, threeTheta: number) => void;
}

const RADIUS = 2.5;
const PLANE_SIZE = 3.5;

export default function ImageSphere({ onAngleChange }: ImageSphereProps) {
  const texturePaths = VIEW_ANGLES.map((v) => v.src);
  const textures = useTexture(texturePaths);
  const { camera } = useThree();
  const meshRefs = useRef<(THREE.Mesh | null)[]>([]);
  const materialRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);

  useLayoutEffect(() => {
    textures.forEach((t) => {
      t.colorSpace = THREE.SRGBColorSpace;
      t.needsUpdate = true;
    });
  }, [textures]);

  useLayoutEffect(() => {
    meshRefs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const view = VIEW_ANGLES[i];
      const dir = directionFromDegrees(view.theta, view.phi);
      const pos = dir.clone().multiplyScalar(RADIUS);
      mesh.lookAt(pos.x + dir.x, pos.y + dir.y, pos.z + dir.z);
    });
  }, []);

  useFrame(() => {
    const spherical = new THREE.Spherical().setFromVector3(camera.position);
    onAngleChange?.(spherical.phi, spherical.theta);

    const cameraDir = camera.position.clone().normalize();
    const dots = VIEW_ANGLES.map((view, i) => ({
      i,
      dot: Math.max(0, cameraDir.dot(directionFromDegrees(view.theta, view.phi))),
    }));
    dots.sort((a, b) => b.dot - a.dot);
    const top2 = dots.slice(0, 2);
    const sum = top2.reduce((s, d) => s + d.dot, 0) || 1;

    for (let idx = 0; idx < VIEW_ANGLES.length; idx++) {
      const mat = materialRefs.current[idx];
      if (!mat) continue;
      const t = top2.find((d) => d.i === idx);
      if (t) {
        mat.opacity = t.dot / sum;
        mat.visible = true;
      } else {
        mat.opacity = 0;
        mat.visible = false;
      }
    }
  });

  const aspect =
    textures[0]?.image?.width && textures[0]?.image?.height
      ? textures[0].image.width / textures[0].image.height
      : 16 / 9;
  const planeHeight = PLANE_SIZE;
  const planeWidth = planeHeight * aspect;

  return (
    <group>
      {VIEW_ANGLES.map((view, i) => {
        const dir = directionFromDegrees(view.theta, view.phi);
        const pos = dir.clone().multiplyScalar(RADIUS);
        return (
          <mesh
            key={view.id}
            ref={(el) => {
              meshRefs.current[i] = el;
            }}
            position={[pos.x, pos.y, pos.z]}
          >
            <planeGeometry args={[planeWidth, planeHeight]} />
            <meshBasicMaterial
              ref={(el) => {
                materialRefs.current[i] = el;
              }}
              map={textures[i]}
              transparent
              opacity={1}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>
        );
      })}
    </group>
  );
}
