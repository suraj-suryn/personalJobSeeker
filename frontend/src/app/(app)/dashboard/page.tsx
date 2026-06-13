'use client';

import { useQuery } from '@tanstack/react-query';
import { scoringApi, jobsApi } from '@/lib/api';
import { formatScore, scoreBadgeClass } from '@/lib/utils';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { Briefcase, CheckCircle, TrendingUp, Bell } from 'lucide-react';

export default function DashboardPage() {
  const { data: matchData } = useQuery({
    queryKey: ['matches'],
    queryFn: () => scoringApi.matches().then((r) => r.data),
  });

  const { data: recentJobs } = useQuery({
    queryKey: ['recent-jobs'],
    queryFn: () => jobsApi.recent(6).then((r) => r.data),
    refetchInterval: 60_000,
  });

  const stats = matchData?.stats;
  const topMatches = matchData?.matches?.slice(0, 5) ?? [];
  const newJobs = recentJobs ?? [];

  const scoreDistribution = [
    { name: 'High (80+)', count: stats?.high_matches ?? 0 },
    { name: 'Medium (60-79)', count: stats?.medium_matches ?? 0 },
    { name: 'Low (<60)', count: stats?.low_matches ?? 0 },
  ];

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard icon={<Briefcase size={20} />} label="Total Matches" value={stats?.total_matches ?? 0} color="blue" />
        <StatCard icon={<TrendingUp size={20} />} label="Avg Match Score" value={stats ? formatScore(stats.avg_score) : '—'} color="green" />
        <StatCard icon={<Bell size={20} />} label="New Jobs (6h)" value={newJobs.length} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Distribution Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Match Score Distribution</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={scoreDistribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top Matches */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Top Matches</h2>
          {topMatches.length === 0 ? (
            <p className="text-sm text-gray-400">Score jobs to see matches here.</p>
          ) : (
            <div className="space-y-3">
              {topMatches.map((m: any) => (
                <div key={m.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{m.job?.title ?? 'Unknown'}</p>
                    <p className="text-xs text-gray-400">{m.job?.company}</p>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${scoreBadgeClass(m.match_score)}`}>
                    {formatScore(m.match_score)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Jobs */}
      {newJobs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-3">New Jobs in Last 6 Hours</h2>
          <div className="space-y-2">
            {newJobs.slice(0, 10).map((job: any) => (
              <div key={job.id} className="flex items-center justify-between py-1 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-800">{job.title}</p>
                  <p className="text-xs text-gray-400">{job.company} · {job.location}</p>
                </div>
                <span className="text-xs text-gray-400 capitalize">{job.source}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
      <div className={`p-2.5 rounded-lg ${colors[color]}`}>{icon}</div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
