import type { SphericalAngle } from "@/types/equipment";
import { getDirectionLabel } from "@/utils/spherical";
import { Compass } from "lucide-react";

interface ViewAngleIndicatorProps {
  angle: SphericalAngle;
}

export default function ViewAngleIndicator({
  angle,
}: ViewAngleIndicatorProps) {
  return (
    <div className="absolute bottom-4 left-4 flex items-center gap-2 rounded-lg bg-gray-900/80 px-3 py-1.5 text-xs text-gray-300 backdrop-blur-sm">
      <Compass className="h-3.5 w-3.5 text-blue-400" />
      <span>{getDirectionLabel(angle)}</span>
    </div>
  );
}
