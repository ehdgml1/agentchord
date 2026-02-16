import { memo } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react';

interface LabeledEdgeData {
  label?: string;
  edgeColor?: string;
}

export const LabeledEdge = memo(function LabeledEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
  style,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeData = data as LabeledEdgeData | undefined;
  const label = edgeData?.label;
  const edgeColor = edgeData?.edgeColor;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{ ...style, stroke: edgeColor || style?.stroke }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
              backgroundColor: edgeColor === '#22c55e' ? '#dcfce7' : edgeColor === '#ef4444' ? '#fee2e2' : '#f3f4f6',
              color: edgeColor || '#6b7280',
              border: `1px solid ${edgeColor || '#d1d5db'}`,
              borderRadius: '4px',
              padding: '1px 6px',
              fontSize: '10px',
              fontWeight: 500,
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});
