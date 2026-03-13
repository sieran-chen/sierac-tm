import type { SphericalAngle, ViewAngleImage } from "@/types/equipment";
import { Vector3 } from "three";

const DEG_TO_RAD = Math.PI / 180;

/** theta/phi in degrees -> unit direction (theta=0 front = +Z, Y up) */
export function directionFromDegrees(thetaDeg: number, phiDeg: number): Vector3 {
  const theta = thetaDeg * DEG_TO_RAD;
  const phi = phiDeg * DEG_TO_RAD;
  const cosPhi = Math.cos(phi);
  return new Vector3(
    Math.sin(theta) * cosPhi,
    Math.sin(phi),
    Math.cos(theta) * cosPhi
  );
}

export function angularDistance(a: SphericalAngle, b: SphericalAngle): number {
  const phiA = a.phi * DEG_TO_RAD;
  const phiB = b.phi * DEG_TO_RAD;
  const dTheta = (a.theta - b.theta) * DEG_TO_RAD;

  const cosAngle =
    Math.sin(phiA) * Math.sin(phiB) +
    Math.cos(phiA) * Math.cos(phiB) * Math.cos(dTheta);

  return Math.acos(Math.min(1, Math.max(-1, cosAngle)));
}

export function findClosestViews(
  cameraAngle: SphericalAngle,
  views: ViewAngleImage[],
  count: number = 2
): { view: ViewAngleImage; distance: number }[] {
  return views
    .map((view) => ({
      view,
      distance: angularDistance(cameraAngle, {
        theta: view.theta,
        phi: view.phi,
      }),
    }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, count);
}

/**
 * Convert Three.js camera spherical coordinates to our convention.
 * Three.js: phi = polar angle from Y axis (0=top), theta = azimuthal in XZ plane
 * Our convention: theta = horizontal 0-360 (0=front/+Z, CW), phi = vertical -90 to +90 (0=horizon)
 */
export function fromThreeSpherical(
  threePhi: number,
  threeTheta: number
): SphericalAngle {
  const phi = 90 - threePhi / DEG_TO_RAD;
  let theta = 90 - threeTheta / DEG_TO_RAD;
  theta = ((theta % 360) + 360) % 360;
  return { theta, phi };
}

export function getDirectionLabel(angle: SphericalAngle): string {
  const { theta, phi } = angle;

  if (phi > 60) return "俯视";
  if (phi < -60) return "仰视";

  const directions = [
    { min: 337.5, max: 360, label: "前方" },
    { min: 0, max: 22.5, label: "前方" },
    { min: 22.5, max: 67.5, label: "右前方" },
    { min: 67.5, max: 112.5, label: "右侧" },
    { min: 112.5, max: 157.5, label: "右后方" },
    { min: 157.5, max: 202.5, label: "后方" },
    { min: 202.5, max: 247.5, label: "左后方" },
    { min: 247.5, max: 292.5, label: "左侧" },
    { min: 292.5, max: 337.5, label: "左前方" },
  ];

  const horizontal =
    directions.find((d) => theta >= d.min && theta < d.max)?.label ?? "前方";

  if (phi > 30) return `${horizontal} (俯视)`;
  if (phi < -30) return `${horizontal} (仰视)`;
  return horizontal;
}
