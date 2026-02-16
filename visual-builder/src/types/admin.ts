/**
 * Admin-related type definitions for user management, audit logs, and A/B testing
 */

/**
 * User role hierarchy
 */
export type Role = 'viewer' | 'editor' | 'operator' | 'admin';

/**
 * User account information
 */
export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  createdAt: string;
  lastLoginAt: string | null;
}

/**
 * Audit log entry for tracking system actions
 */
export interface AuditLog {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  userId: string;
  userName: string;
  details: Record<string, unknown>;
  ipAddress: string | null;
  createdAt: string;
}

/**
 * A/B test configuration
 */
export interface ABTest {
  id: string;
  name: string;
  workflowAId: string;
  workflowBId: string;
  trafficSplit: number;
  status: 'draft' | 'running' | 'completed';
  createdAt: string;
}

/**
 * A/B test variant statistics
 */
export interface ABTestStats {
  variant: string;
  count: number;
  successRate: number;
  avgDurationMs: number;
}

/**
 * Filters for audit log queries
 */
export interface AuditFilters {
  startDate?: string;
  endDate?: string;
  action?: string;
  userId?: string;
}

/**
 * Data for creating a new A/B test
 */
export interface ABTestCreate {
  name: string;
  workflowAId: string;
  workflowBId: string;
  trafficSplit: number;
}
