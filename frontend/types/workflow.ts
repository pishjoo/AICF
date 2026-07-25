export type WorkflowStatus = 'pending' | 'active' | 'completed';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'changes_requested';

export interface WorkflowStage {
  id: string;
  name: string;
  status: WorkflowStatus;
  completedAt?: string;
}

export interface Approval {
  id: string;
  reviewer: string;
  status: ApprovalStatus;
  comment?: string;
  createdAt: string;
}

export interface ActivityEvent {
  id: string;
  user: string;
  action: string;
  timestamp: string;
}
