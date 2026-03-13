import { useState, useCallback } from "react";
import type { SphericalAngle } from "@/types/equipment";
import { fromThreeSpherical } from "@/utils/spherical";

export function useViewAngle() {
  const [angle, setAngle] = useState<SphericalAngle>({ theta: 0, phi: 15 });

  const handleCameraChange = useCallback(
    (threePhi: number, threeTheta: number) => {
      setAngle(fromThreeSpherical(threePhi, threeTheta));
    },
    []
  );

  return { angle, handleCameraChange };
}
