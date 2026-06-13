'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi, scoringApi, resumeApi } from '@/lib/api';
import { toast } from 'sonner';
import { Search, Loader2, ExternalLink, Zap } from 'lucide-react';
import { formatScore, scoreBadgeClass } from '@/lib/utils';

export default function JobsPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['jobs', page, search],
    queryFn: () => jobsApi.list({ page, page_size: 20, query: search || undefined }).then((r) => r.data),
    placeholderData: (prev) => prev,
  });

  const { data: resumes } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumeApi.list().then((r) => r.data),
  });

  const primaryResume = resumes?.find((r: any) => r.is_primary) ?? resumes?.[0];

  const searchMutation = useMutation({
    mutationFn: () => jobsApi.search({ queries: ['python developer', 'software engineer'], sources: ['linkedin', 'indeed'] }),
    onSuccess: () => {
      toast.success('Job search started — results in ~2 minutes');
      setTimeout(() => qc.invalidateQueries({ queryKey: ['jobs'] }), 90_000);
    },
  });

  const scoreMutation = useMutation({
    mutationFn: (jobId: string) => scoringApi.scoreJob(jobId, primaryResume?.id),
    onSuccess: () => {
      toast.success('Job scored!');
      qc.invalidateQueries({ queryKey: ['matches'] });
    },
    onError: () => toast.error('Scoring failed — make sure you have a resume'),
  });

  const jobs = data?.jobs ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
        <button
          onClick={() => searchMutation.mutate()}
          disabled={searchMutation.isPending}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-60"
        >
          {searchMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          Search New Jobs
        </button>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Filter jobs..."
          className="w-full border border-gray-300 rounded-lg pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {/* Job List */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
      ) : jobs.length === 0 ? (
        <p className="text-center text-gray-400 py-12">No jobs found. Click "Search New Jobs" to start.</p>
      ) : (
        <div className="space-y-3">
          {jobs.map((job: any) => (
            <div key={job.id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-gray-900">{job.title}</p>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded capitalize">{job.source}</span>
                    {job.job_type && (
                      <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded capitalize">{job.job_type}</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5">{job.company} · {job.location ?? 'Remote'}</p>
                  {job.salary_min && (
                    <p className="text-xs text-green-600 mt-1">
                      ${job.salary_min.toLocaleString()}
                      {job.salary_max ? ` – $${job.salary_max.toLocaleString()}` : '+'} {job.salary_currency}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {primaryResume && (
                    <button
                      onClick={() => scoreMutation.mutate(job.id)}
                      disabled={scoreMutation.isPending}
                      className="text-xs text-brand-600 hover:bg-brand-50 border border-brand-200 px-3 py-1.5 rounded-lg flex items-center gap-1 disabled:opacity-50"
                    >
                      <Zap size={12} />Score
                    </button>
                  )}
                  <a href={job.url} target="_blank" rel="noopener noreferrer"
                    className="text-gray-400 hover:text-gray-600 p-1">
                    <ExternalLink size={16} />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{total} jobs total</span>
          <div className="flex gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1 border rounded disabled:opacity-40">Prev</button>
            <span className="px-3 py-1">Page {page}</span>
            <button onClick={() => setPage((p) => p + 1)} disabled={page * 20 >= total}
              className="px-3 py-1 border rounded disabled:opacity-40">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
