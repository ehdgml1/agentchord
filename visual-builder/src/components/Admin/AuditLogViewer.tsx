/**
 * Audit Log Viewer component
 * Displays system audit logs with filtering and export capabilities
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAdminStore } from '../../stores/adminStore';
import type { AuditLog, AuditFilters } from '../../types/admin';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Dialog, DialogContent } from '../ui/dialog';

export function AuditLogViewer() {
  const { auditLogs, auditLogsLoading, auditLogsError, fetchAuditLogs } = useAdminStore();
  const [filters, setFilters] = useState<AuditFilters>({});
  const [filterInputs, setFilterInputs] = useState<AuditFilters>({});
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    fetchAuditLogs(filters);
  }, [fetchAuditLogs, filters]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, []);

  const sanitizeCsvValue = (value: string | undefined | null): string => {
    if (!value) return '""';

    const str = String(value);
    // Escape double quotes by doubling them
    let sanitized = str.replace(/"/g, '""');

    // Prefix formula-triggering characters with a single quote
    // This prevents Excel/Sheets from interpreting them as formulas
    if (/^[=+\-@\t\r]/.test(sanitized)) {
      sanitized = "'" + sanitized;
    }

    // Always wrap in double quotes for safety
    return `"${sanitized}"`;
  };

  const handleExportCsv = () => {
    const headers = ['Time', 'User', 'Action', 'Resource Type', 'Resource ID', 'IP Address'];
    const sanitizedHeaders = headers.map(h => sanitizeCsvValue(h));

    const rows = auditLogs.map((log) => [
      sanitizeCsvValue(new Date(log.createdAt).toISOString()),
      sanitizeCsvValue(log.userName),
      sanitizeCsvValue(log.action),
      sanitizeCsvValue(log.resourceType),
      sanitizeCsvValue(log.resourceId),
      sanitizeCsvValue(log.ipAddress || 'N/A'),
    ]);

    const csv = [sanitizedHeaders, ...rows].map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const handleFilterChange = useCallback((key: keyof AuditFilters, value: string) => {
    // Update display immediately for responsive UX
    setFilterInputs((prev) => ({ ...prev, [key]: value || undefined }));

    // Debounce the actual API fetch
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    debounceTimer.current = setTimeout(() => {
      setFilters((prev) => ({
        ...prev,
        [key]: value || undefined,
      }));
    }, 300);
  }, []);

  if (auditLogsLoading && auditLogs.length === 0) {
    return <div className="p-8 text-center">Loading audit logs...</div>;
  }

  if (auditLogsError) {
    return (
      <div className="p-8 text-center text-red-600">
        Error: {auditLogsError}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Audit Logs</h2>
        <Button onClick={handleExportCsv} disabled={auditLogs.length === 0}>
          Export CSV
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Input
          type="date"
          placeholder="Start Date"
          value={filterInputs.startDate || ''}
          onChange={(e) => handleFilterChange('startDate', e.target.value)}
        />
        <Input
          type="date"
          placeholder="End Date"
          value={filterInputs.endDate || ''}
          onChange={(e) => handleFilterChange('endDate', e.target.value)}
        />
        <Input
          type="text"
          placeholder="Filter by action"
          value={filterInputs.action || ''}
          onChange={(e) => handleFilterChange('action', e.target.value)}
        />
        <Input
          type="text"
          placeholder="Filter by user ID"
          value={filterInputs.userId || ''}
          onChange={(e) => handleFilterChange('userId', e.target.value)}
        />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Resource</TableHead>
            <TableHead>IP Address</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {auditLogs.map((log) => (
            <TableRow key={log.id}>
              <TableCell>{formatDate(log.createdAt)}</TableCell>
              <TableCell>{log.userName}</TableCell>
              <TableCell>{log.action}</TableCell>
              <TableCell>
                {log.resourceType}/{log.resourceId}
              </TableCell>
              <TableCell>{log.ipAddress || 'N/A'}</TableCell>
              <TableCell>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSelectedLog(log);
                    setShowDetail(true);
                  }}
                >
                  View
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {auditLogs.length === 0 && (
        <div className="p-8 text-center text-muted-foreground">
          No audit logs found
        </div>
      )}

      {showDetail && selectedLog && (
        <Dialog open={showDetail} onOpenChange={setShowDetail}>
          <DialogContent>
            <h3 className="text-lg font-semibold mb-4">Audit Log Details</h3>
            <div className="space-y-2">
              <div>
                <strong>ID:</strong> {selectedLog.id}
              </div>
              <div>
                <strong>Time:</strong> {formatDate(selectedLog.createdAt)}
              </div>
              <div>
                <strong>User:</strong> {selectedLog.userName} ({selectedLog.userId})
              </div>
              <div>
                <strong>Action:</strong> {selectedLog.action}
              </div>
              <div>
                <strong>Resource:</strong> {selectedLog.resourceType}/{selectedLog.resourceId}
              </div>
              <div>
                <strong>IP Address:</strong> {selectedLog.ipAddress || 'N/A'}
              </div>
              <div>
                <strong>Details:</strong>
                <pre className="mt-2 p-2 bg-muted rounded text-sm overflow-auto">
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
