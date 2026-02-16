import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ReactFlowProvider } from '@xyflow/react';
import { Canvas } from '../components/Canvas/Canvas';
import { Layout } from '../components/Layout';
import { useWorkflowStore } from '../stores/workflowStore';
import { useUnsavedChanges } from '../hooks/useUnsavedChanges';
import { useAutoSave } from '../hooks/useAutoSave';

export function WorkflowEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const loadFromBackend = useWorkflowStore(s => s.loadFromBackend);
  useUnsavedChanges();
  useAutoSave();

  useEffect(() => {
    if (id && id !== 'new') {
      loadFromBackend(id).catch(() => {
        navigate('/');
      });
    }
  }, [id, loadFromBackend, navigate]);

  return (
    <ReactFlowProvider>
      <Layout>
        <Canvas />
      </Layout>
    </ReactFlowProvider>
  );
}
