import { cn } from '@/lib/utils';
import type { PipelineStage, PipelineStageStatus } from '@/types/content';

interface PipelineProps {
  stages: PipelineStage[];
  compact?: boolean;
}

const statusColors: Record<PipelineStageStatus, string> = {
  pending: 'bg-gray-100 border-gray-300 text-gray-500',
  in_progress: 'bg-blue-100 border-blue-400 text-blue-700',
  completed: 'bg-green-100 border-green-400 text-green-700',
  blocked: 'bg-red-100 border-red-400 text-red-700',
};

const statusIcons: Record<PipelineStageStatus, string> = {
  pending: '○',
  in_progress: '◐',
  completed: '●',
  blocked: '✕',
};

export function Pipeline({ stages, compact = false }: PipelineProps) {
  return (
    <div className={cn(
      'w-full',
      compact ? 'py-2' : 'py-6'
    )}>
      <div className="flex items-center justify-between gap-2">
        {stages.map((stage, index) => (
          <div key={stage.id} className="flex items-center flex-1">
            {/* Stage Node */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-10 h-10 rounded-full border-2 flex items-center justify-center font-bold text-sm transition-all',
                  statusColors[stage.status],
                  compact ? 'w-8 h-8 text-xs' : 'w-10 h-10'
                )}
                title={stage.name}
              >
                {statusIcons[stage.status]}
              </div>
              {!compact && (
                <span className={cn(
                  'mt-2 text-xs font-medium text-center max-w-[80px]',
                  stage.status === 'pending' ? 'text-gray-500' : 'text-gray-900'
                )}>
                  {stage.name}
                </span>
              )}
              {!compact && stage.completedAt && (
                <span className="text-[10px] text-gray-400 mt-1">
                  {new Date(stage.completedAt).toLocaleDateString()}
                </span>
              )}
            </div>

            {/* Connector Line */}
            {index < stages.length - 1 && (
              <div className="flex-1 h-0.5 mx-2 relative">
                <div
                  className={cn(
                    'absolute inset-y-0 left-0 right-0 transition-all',
                    stages[index].status === 'completed'
                      ? 'bg-green-400'
                      : 'bg-gray-200'
                  )}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface PipelineStageCardProps {
  stage: PipelineStage;
  onClick?: () => void;
}

export function PipelineStageCard({ stage, onClick }: PipelineStageCardProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'p-4 rounded-lg border-2 transition-all text-left w-full',
        statusColors[stage.status],
        'hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
      )}
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold">{stage.name}</h4>
          <p className="text-sm opacity-75 capitalize">{stage.status.replace('_', ' ')}</p>
        </div>
        <span className="text-xl">{statusIcons[stage.status]}</span>
      </div>
      {stage.completedAt && (
        <p className="text-xs mt-2 opacity-60">
          Completed: {new Date(stage.completedAt).toLocaleString()}
        </p>
      )}
    </button>
  );
}
