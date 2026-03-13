// import { EffectComposer, Outline } from "@react-three/postprocessing";
import type * as THREE from "three";

interface PartInteractionProps {
  /** Objects to outline on hover (e.g. meshes of the hovered part). */
  selection: THREE.Object3D[];
  /** When true, skip Outline to avoid extra cost. */
  disabled?: boolean;
}

/**
 * Renders post-processing outline for selected objects.
 * Cursor and tooltip are handled by the parent (EquipmentViewer + ModelViewer).
 */
export default function PartInteraction({
  selection,
  disabled = false,
}: PartInteractionProps) {
  // EffectComposer with useFrame(priority>0) disables R3F auto-render; scene then
  // only shows composer output. Outline pass can leave main scene invisible on some
  // setups, so we skip postprocessing and rely on emissive hover in ModelViewer.
  if (disabled || selection.length === 0) {
    return null;
  }
  return null;
  // Uncomment when composer is configured to not disable default render:
  // return (
  //   <EffectComposer>
  //     <Outline selection={selection} edgeStrength={2} visibleEdgeColor={0x3b82f6} hiddenEdgeColor={0x1e3a5f} blur />
  //   </EffectComposer>
  // );
}
