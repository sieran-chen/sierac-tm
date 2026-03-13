import { Suspense, useState, useCallback, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Preload, Html } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import ImageSphere from "./ImageSphere";
import ModelViewer from "./ModelViewer";
import ModelPlaceholder from "./ModelPlaceholder";
import ViewAngleIndicator from "./ViewAngleIndicator";
import ViewerErrorBoundary from "./ViewerErrorBoundary";
import PresetViews from "./PresetViews";
import PresetCameraController from "./PresetCameraController";
import PartInfoPopup from "./PartInfoPopup";
import { PresetCameraProvider } from "./PresetCameraContext";
import { useViewAngle } from "@/hooks/useViewAngle";
import { PART_MAPPING } from "@/config/partMapping";
import type { Alarm, TelemetryValue } from "@/types/equipment";
import EquipmentAxes from "./EquipmentAxes";

const USE_MODEL = import.meta.env.VITE_USE_MODEL !== "false";

function ViewerLoadingFallback() {
  return (
    <>
      <mesh>
        <planeGeometry args={[10, 10]} />
        <meshBasicMaterial color="#374151" />
      </mesh>
      <Html center style={{ color: "#9ca3af", fontSize: 14, pointerEvents: "none" }}>
        正在加载 3D 模型，请稍候…
      </Html>
    </>
  );
}

interface EquipmentViewerProps {
  alarms?: Alarm[];
  telemetry?: TelemetryValue[];
}

const ZOOM_STEP = 1.2;

export default function EquipmentViewer({
  alarms = [],
  telemetry = [],
}: EquipmentViewerProps) {
  const { angle, handleCameraChange } = useViewAngle();
  const orbitRef = useRef<OrbitControlsImpl>(null);
  const [modelLoadFailed, setModelLoadFailed] = useState(false);
  const [hoveredPart, setHoveredPart] = useState<string | null>(null);
  const [selectedPart, setSelectedPart] = useState<{
    name: string;
    pos: { x: number; y: number };
  } | null>(null);

  const handlePartHover = useCallback((name: string | null) => {
    setHoveredPart(name);
  }, []);

  const handlePartClick = useCallback(
    (name: string, screenPos: { x: number; y: number }) => {
      setSelectedPart((prev) =>
        prev?.name === name ? null : { name, pos: screenPos }
      );
    },
    []
  );

  const showImageSphere = !USE_MODEL || modelLoadFailed;
  const partLabel = hoveredPart
    ? PART_MAPPING.find((p) => p.partName === hoveredPart)?.label
    : null;
  const selectedMapping = selectedPart
    ? PART_MAPPING.find((p) => p.partName === selectedPart.name)
    : null;

  return (
    <PresetCameraProvider>
      <div className="relative h-full w-full">
        <Canvas
          camera={{ position: [8, 12, 18], fov: 55 }}
          style={{
            background:
              "linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)",
          }}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 8, 5]} intensity={1} />
          {import.meta.env.DEV && <EquipmentAxes />}
          <Suspense fallback={<ViewerLoadingFallback />}>
            <ViewerErrorBoundary
              onError={() => setModelLoadFailed(true)}
              fallback={<ModelPlaceholder />}
            >
              {USE_MODEL && !modelLoadFailed ? (
                <ModelViewer
                  partMapping={PART_MAPPING}
                  alarms={alarms}
                  telemetry={telemetry}
                  onPartHover={handlePartHover}
                  onPartClick={handlePartClick}
                />
              ) : (
                <ImageSphere onAngleChange={handleCameraChange} />
              )}
            </ViewerErrorBoundary>
          </Suspense>
          {USE_MODEL && !modelLoadFailed && <PresetCameraController />}
          <OrbitControls
              ref={orbitRef}
              target={[0, 2, 0]}
              enablePan={USE_MODEL && !modelLoadFailed}
              minPolarAngle={Math.PI / 6}
              maxPolarAngle={(5 * Math.PI) / 6}
              minDistance={5}
              maxDistance={80}
              rotateSpeed={0.5}
            />
          <Preload all />
        </Canvas>

        {showImageSphere && <ViewAngleIndicator angle={angle} />}

        {USE_MODEL && modelLoadFailed && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="rounded-lg bg-black/70 px-4 py-3 text-center text-sm text-gray-300">
              <p>3D 模型未加载</p>
              <p className="mt-1 text-xs text-gray-500">
                请将 001.glb 放入 sierac-twin/public/models/ 以显示设备模型
              </p>
            </div>
          </div>
        )}

        {USE_MODEL && !modelLoadFailed && (
          <>
            <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-0.5 rounded-lg bg-gray-900/80 px-1.5 py-1 backdrop-blur-sm">
              <span className="px-1 text-[10px] text-gray-500">缩放</span>
              <div className="flex gap-0.5">
                <button
                  type="button"
                  onClick={() => orbitRef.current?.dollyOut(ZOOM_STEP)}
                  className="rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 hover:text-white"
                  title="缩小"
                >
                  −
                </button>
                <button
                  type="button"
                  onClick={() => orbitRef.current?.dollyIn(ZOOM_STEP)}
                  className="rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 hover:text-white"
                  title="放大"
                >
                  +
                </button>
              </div>
            </div>
            <PresetViews disabled={false} />
          </>
        )}

        {partLabel && (
          <div className="pointer-events-none absolute left-4 top-4 rounded bg-black/70 px-3 py-1.5 text-sm text-white">
            {partLabel}
          </div>
        )}

        {selectedPart && selectedMapping && (
          <PartInfoPopup
            selectedPart={selectedPart}
            mapping={selectedMapping}
            telemetry={telemetry}
            onClose={() => setSelectedPart(null)}
          />
        )}
      </div>
    </PresetCameraProvider>
  );
}
