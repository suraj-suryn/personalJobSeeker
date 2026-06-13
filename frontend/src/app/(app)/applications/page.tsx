'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { applicationsApi } from '@/lib/api';
import { toast } from 'sonner';
import { statusLabel, statusColor, cn } from '@/lib/utils';
import { Loader2, ChevronDown } from 'lucide-react';

const STATUS_COLS = ['saved', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn'];

export default function ApplicationsPage() {
  const qc = useQueryClient();
  const [view, setView] = useState<'kanban' | 'list'>('kanban');

  const { data: apps, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => applicationsApi.list().then((r) => r.data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      applicationsApi.update(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications'] }),
    onError: () => toast.error('Update failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.delete(id),
    onSuccess: () => {
      toast.success('Application removed');
      qc.invalidateQueries({ queryKey: ['applications'] });
    },
  });

  if (isLoading) return <div className="p-6 flex justify-center"><Loader2 className="animate-spin text-gray-400" /></div>;

  const byStatus = (status: string) => (apps ?? []).filter((a: any) => a.status === status);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
        <div className="flex gap-2">
          {(['kanban', 'list'] as const).map((v) => (
            <button key={v} onClick={() => setView(v)}
              className={cn('text-sm px-3 py-1.5 rounded-lg capitalize', view === v ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200')}>
              {v}
            </button>
          ))}
        </div>
      </div>

      {(apps ?? []).length === 0 ? (
        <p className="text-center text-gray-400 py-12">No applications tracked yet. Go to Jobs to save or apply.</p>
      ) : view === 'kanban' ? (
        /* Kanban view — show only first 4 columns */
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 overflow-x-auto">
          {STATUS_COLS.slice(0, 4).map((status) => (
            <div key={status} className="bg-gray-100 rounded-xl p-3 min-h-[300px]">
              <div className="flex items-center gap-2 mb-3">
                <span className={cn('text-xs font-semibold px-2 py-0.5 rounded-full', statusColor(status))}>
                  {statusLabel(status)}
                </span>
                <span className="text-xs text-gray-400">({byStatus(status).length})</span>
              </div>
              <div className="space-y-2">
                {byStatus(status).map((app: any) => (
                  <KanbanCard key={app.id} app={app}
                    onStatusChange={(newStatus) => updateMutation.mutate({ id: app.id, status: newStatus })}
                    onDelete={() => deleteMutation.mutate(app.id)} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* List view */
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Job</th>
                <th className="px-4 py-3 text-left">Company</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(apps ?? []).map((app: any) => (
                <tr key={app.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{app.job_title ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{app.company ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', statusColor(app.status))}>
                      {statusLabel(app.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => deleteMutation.mutate(app.id)} className="text-red-400 hover:text-red-600 text-xs">
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function KanbanCard({ app, onStatusChange, onDelete }: { app: any; onStatusChange: (s: string) => void; onDelete: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
      <p className="font-medium text-gray-800 text-sm truncate">{app.job_title ?? 'Unknown Job'}</p>
      <p className="text-xs text-gray-400 truncate">{app.company ?? '—'}</p>
      <div className="flex items-center justify-between mt-2">
        <div className="relative">
          <button onClick={() => setOpen(!open)} className="text-xs text-gray-500 flex items-center gap-1">
            Move <ChevronDown size={10} />
          </button>
          {open && (
            <div className="absolute left-0 top-5 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1 min-w-[120px]">
              {STATUS_COLS.filter((s) => s !== app.status).map((s) => (
                <button key={s} onClick={() => { onStatusChange(s); setOpen(false); }}
                  className="block w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50 capitalize">
                  {statusLabel(s)}
                </button>
              ))}
            </div>
          )}
        </div>
        <button onClick={onDelete} className="text-xs text-red-400 hover:text-red-600">✕</button>
      </div>
    </div>
  );
}
