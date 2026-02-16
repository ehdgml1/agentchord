/**
 * A/B Test Dashboard component
 * Manages A/B tests with creation, statistics, and control capabilities
 */

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useAdminStore } from '../../stores/adminStore';
import type { ABTest, ABTestCreate, ABTestStats } from '../../types/admin';
import { api } from '../../services/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Button } from '../ui/button';
import { Dialog, DialogContent } from '../ui/dialog';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Card } from '../ui/card';

export function ABTestDashboard() {
  const { abTests, abTestsLoading, abTestsError, fetchABTests } = useAdminStore();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedTest, setSelectedTest] = useState<ABTest | null>(null);
  const [stats, setStats] = useState<{ A: ABTestStats; B: ABTestStats } | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  const [createForm, setCreateForm] = useState<ABTestCreate>({
    name: '',
    workflowAId: '',
    workflowBId: '',
    trafficSplit: 50,
  });

  useEffect(() => {
    fetchABTests();
  }, [fetchABTests]);

  const handleCreate = async () => {
    try {
      await api.admin.abTests.create(createForm);
      await fetchABTests();
      setShowCreateDialog(false);
      setCreateForm({
        name: '',
        workflowAId: '',
        workflowBId: '',
        trafficSplit: 50,
      });
      toast.success('A/B test created successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create A/B test');
    }
  };

  const handleStart = async (testId: string) => {
    try {
      await api.admin.abTests.start(testId);
      await fetchABTests();
      toast.success('A/B test started');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to start test');
    }
  };

  const handleStop = async (testId: string) => {
    try {
      await api.admin.abTests.stop(testId);
      await fetchABTests();
      toast.success('A/B test stopped');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to stop test');
    }
  };

  const handleExport = async (testId: string) => {
    try {
      const csv = await api.admin.abTests.exportCsv(testId);
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ab-test-${testId}-${new Date().toISOString()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('A/B test data exported');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to export');
    }
  };

  const loadStats = async (test: ABTest) => {
    setSelectedTest(test);
    setLoadingStats(true);
    try {
      const testStats = await api.admin.abTests.getStats(test.id);
      setStats(testStats);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load stats');
    } finally {
      setLoadingStats(false);
    }
  };

  const getStatusBadge = (status: ABTest['status']) => {
    const variants = {
      draft: 'secondary',
      running: 'default',
      completed: 'outline',
    } as const;
    return <Badge variant={variants[status]}>{status}</Badge>;
  };

  if (abTestsLoading && abTests.length === 0) {
    return <div className="p-8 text-center">Loading A/B tests...</div>;
  }

  if (abTestsError) {
    return (
      <div className="p-8 text-center text-red-600">
        Error: {abTestsError}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">A/B Test Dashboard</h2>
        <Button onClick={() => setShowCreateDialog(true)}>
          Create New Test
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Traffic Split</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {abTests.map((test) => (
            <TableRow key={test.id}>
              <TableCell className="font-medium">{test.name}</TableCell>
              <TableCell>{getStatusBadge(test.status)}</TableCell>
              <TableCell>{test.trafficSplit}% / {100 - test.trafficSplit}%</TableCell>
              <TableCell>{new Date(test.createdAt).toLocaleString()}</TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => loadStats(test)}>
                    Stats
                  </Button>
                  {test.status === 'draft' && (
                    <Button size="sm" onClick={() => handleStart(test.id)}>
                      Start
                    </Button>
                  )}
                  {test.status === 'running' && (
                    <Button variant="destructive" size="sm" onClick={() => handleStop(test.id)}>
                      Stop
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={() => handleExport(test.id)}>
                    Export
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {showCreateDialog && (
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Create A/B Test</h3>
              <div className="space-y-3">
                <Input
                  placeholder="Test Name"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                />
                <Input
                  placeholder="Workflow A ID"
                  value={createForm.workflowAId}
                  onChange={(e) => setCreateForm({ ...createForm, workflowAId: e.target.value })}
                />
                <Input
                  placeholder="Workflow B ID"
                  value={createForm.workflowBId}
                  onChange={(e) => setCreateForm({ ...createForm, workflowBId: e.target.value })}
                />
                <div>
                  <label className="text-sm">Traffic Split (% to A): {createForm.trafficSplit}%</label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={createForm.trafficSplit}
                    onChange={(e) => setCreateForm({ ...createForm, trafficSplit: Number(e.target.value) })}
                    className="w-full"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreate}>Create</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {selectedTest && (
        <Dialog open={!!selectedTest} onOpenChange={() => setSelectedTest(null)}>
          <DialogContent>
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">{selectedTest.name} - Statistics</h3>
              {loadingStats ? (
                <div className="text-center">Loading stats...</div>
              ) : stats ? (
                <div className="grid grid-cols-2 gap-4">
                  <Card className="p-4">
                    <h4 className="font-semibold mb-2">Variant A</h4>
                    <div className="space-y-1 text-sm">
                      <div>Count: {stats.A.count}</div>
                      <div>Success Rate: {(stats.A.successRate * 100).toFixed(2)}%</div>
                      <div>Avg Duration: {stats.A.avgDurationMs.toFixed(0)}ms</div>
                    </div>
                  </Card>
                  <Card className="p-4">
                    <h4 className="font-semibold mb-2">Variant B</h4>
                    <div className="space-y-1 text-sm">
                      <div>Count: {stats.B.count}</div>
                      <div>Success Rate: {(stats.B.successRate * 100).toFixed(2)}%</div>
                      <div>Avg Duration: {stats.B.avgDurationMs.toFixed(0)}ms</div>
                    </div>
                  </Card>
                </div>
              ) : null}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
