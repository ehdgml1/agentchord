/**
 * Secrets management panel
 *
 * Provides UI for managing secrets (environment variables, API keys, etc.)
 * Values are masked for security and stored securely on the backend.
 */

import { useState, useEffect, useCallback, memo } from 'react';
import { api } from '../../services/api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Trash2, Edit2, Plus, Eye, EyeOff } from 'lucide-react';

export const SecretsPanel = memo(function SecretsPanel() {
  const [secrets, setSecrets] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add/Edit dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<'add' | 'edit'>('add');
  const [dialogName, setDialogName] = useState('');
  const [dialogValue, setDialogValue] = useState('');
  const [dialogShowValue, setDialogShowValue] = useState(false);
  const [dialogSubmitting, setDialogSubmitting] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteSecretName, setDeleteSecretName] = useState('');
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const SECRET_NAME_PATTERN = /^[A-Z][A-Z0-9_]*$/;

  const validateName = (name: string): string | null => {
    if (!name) return 'Name is required';
    if (!SECRET_NAME_PATTERN.test(name)) return 'Use UPPER_SNAKE_CASE (e.g., MY_API_KEY)';
    if (dialogMode === 'add' && secrets.includes(name)) return 'Secret already exists';
    return null;
  };

  const fetchSecrets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const secretList = await api.secrets.list();
      setSecrets(secretList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch secrets');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch secrets list on mount
  useEffect(() => {
    fetchSecrets();
  }, [fetchSecrets]);

  const handleAddClick = useCallback(() => {
    setDialogMode('add');
    setDialogName('');
    setDialogValue('');
    setDialogShowValue(false);
    setNameError(null);
    setDialogOpen(true);
  }, []);

  const handleEditClick = useCallback((name: string) => {
    setDialogMode('edit');
    setDialogName(name);
    setDialogValue('');
    setDialogShowValue(false);
    setNameError(null);
    setDialogOpen(true);
  }, []);

  const handleDeleteClick = useCallback((name: string) => {
    setDeleteSecretName(name);
    setDeleteDialogOpen(true);
  }, []);

  const handleDialogSubmit = async () => {
    const error = validateName(dialogName);
    if (error) {
      setNameError(error);
      return;
    }

    if (!dialogValue) {
      return;
    }

    setDialogSubmitting(true);
    setError(null);

    try {
      if (dialogMode === 'add') {
        await api.secrets.create(dialogName, dialogValue);
      } else {
        await api.secrets.update(dialogName, dialogValue);
      }

      await fetchSecrets();
      setDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save secret');
    } finally {
      setDialogSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteSecretName) {
      return;
    }

    setDeleteSubmitting(true);
    setError(null);

    try {
      await api.secrets.delete(deleteSecretName);
      await fetchSecrets();
      setDeleteDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete secret');
    } finally {
      setDeleteSubmitting(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Secrets</h2>
          <p className="text-sm text-muted-foreground">
            Manage environment variables and API keys
          </p>
        </div>
        <Button onClick={handleAddClick} size="sm" aria-label="Add new secret">
          <Plus className="h-4 w-4 mr-2" />
          Add Secret
        </Button>
      </div>

      {error && (
        <div className="p-3 rounded-md bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">
          Loading secrets...
        </div>
      ) : secrets.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p>No secrets configured</p>
          <p className="text-xs mt-2">Add your first secret to get started</p>
        </div>
      ) : (
        <div className="space-y-2">
          {secrets.map((name) => (
            <div
              key={name}
              className="flex items-center justify-between p-3 rounded-md border bg-card hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div>
                  <p className="font-medium">{name}</p>
                  <p className="text-xs text-muted-foreground">
                    Value: <span className="font-mono">{'*'.repeat(16)}</span>
                  </p>
                </div>
                <Badge variant="secondary">Masked</Badge>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleEditClick(name)}
                  title="Update secret value"
                  aria-label={`Edit ${name} secret`}
                >
                  <Edit2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDeleteClick(name)}
                  title="Delete secret"
                  aria-label={`Delete ${name} secret`}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === 'add' ? 'Add Secret' : 'Update Secret'}
            </DialogTitle>
            <DialogDescription>
              {dialogMode === 'add'
                ? 'Create a new secret for use in your workflows'
                : 'Update the value of an existing secret'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="secret-name">Name</Label>
              <Input
                id="secret-name"
                value={dialogName}
                onChange={(e) => {
                  const val = e.target.value.toUpperCase();
                  setDialogName(val);
                  setNameError(validateName(val));
                }}
                placeholder="API_KEY"
                disabled={dialogMode === 'edit'}
                aria-label="Secret name"
                aria-invalid={!!nameError}
                aria-describedby={nameError ? "name-error" : "name-hint"}
              />
              {nameError && <p id="name-error" className="text-xs text-destructive">{nameError}</p>}
              {!nameError && (
                <p id="name-hint" className="text-xs text-muted-foreground">
                  Use uppercase with underscores (e.g., MY_API_KEY)
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="secret-value">Value</Label>
              <div className="relative">
                <Input
                  id="secret-value"
                  type={dialogShowValue ? 'text' : 'password'}
                  value={dialogValue}
                  onChange={(e) => setDialogValue(e.target.value)}
                  placeholder="Enter secret value"
                  className="pr-10"
                  aria-label="Secret value"
                />
                <button
                  type="button"
                  onClick={() => setDialogShowValue(!dialogShowValue)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-accent rounded"
                  title={dialogShowValue ? 'Hide value' : 'Show value'}
                >
                  {dialogShowValue ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={dialogSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDialogSubmit}
              disabled={!dialogName || !dialogValue || !!nameError || dialogSubmitting}
            >
              {dialogSubmitting ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Secret</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the secret "{deleteSecretName}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleteSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteSubmitting}
            >
              {deleteSubmitting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
});
