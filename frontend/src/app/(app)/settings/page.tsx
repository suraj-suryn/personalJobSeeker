'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/lib/api';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { setUser } from '@/store/authSlice';
import { toast } from 'sonner';
import { useState } from 'react';
import { Loader2 } from 'lucide-react';

const LLM_OPTIONS = [
  { value: 'ollama', label: 'Ollama (Local — free, private)' },
  { value: 'openrouter', label: 'OpenRouter (free tier)' },
  { value: 'groq', label: 'Groq (free tier)' },
  { value: 'gemini', label: 'Gemini (free tier)' },
  { value: 'openai', label: 'OpenAI (paid)' },
];

export default function SettingsPage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const qc = useQueryClient();

  const [llmProvider, setLlmProvider] = useState(user?.llm_provider ?? 'ollama');
  const [emailNotif, setEmailNotif] = useState(user?.email_notifications ?? true);
  const [desktopNotif, setDesktopNotif] = useState(user?.desktop_notifications ?? true);
  const [matchThreshold, setMatchThreshold] = useState(user?.match_threshold ?? 65);

  const updateMutation = useMutation({
    mutationFn: () => authApi.updateMe({
      llm_provider: llmProvider,
      email_notifications: emailNotif,
      desktop_notifications: desktopNotif,
      match_threshold: matchThreshold,
    }),
    onSuccess: (data) => {
      dispatch(setUser(data.data));
      toast.success('Settings saved');
    },
    onError: () => toast.error('Save failed'),
  });

  // Admin section
  const isAdmin = user?.role === 'admin';
  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => authApi.listUsers().then((r) => r.data),
    enabled: isAdmin,
  });

  const toggleUser = useMutation({
    mutationFn: (userId: string) => authApi.toggleUserActive(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  return (
    <div className="p-6 space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* User preferences */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-5">
        <h2 className="font-semibold text-gray-700">Preferences</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">LLM Provider</label>
          <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
            {LLM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <p className="text-xs text-gray-400 mt-1">Ollama runs locally on your machine for maximum privacy.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Match Threshold: <span className="text-brand-600">{matchThreshold}%</span>
          </label>
          <input type="range" min={30} max={95} step={5} value={matchThreshold}
            onChange={(e) => setMatchThreshold(Number(e.target.value))}
            className="w-full accent-brand-600" />
          <p className="text-xs text-gray-400">Only show notifications for jobs above this score.</p>
        </div>

        <div className="space-y-3">
          <Toggle label="Email Notifications" checked={emailNotif} onChange={setEmailNotif}
            description="Receive emails when new matching jobs are found" />
          <Toggle label="Desktop Notifications" checked={desktopNotif} onChange={setDesktopNotif}
            description="Windows toast notifications when new jobs arrive" />
        </div>

        <button
          onClick={() => updateMutation.mutate()}
          disabled={updateMutation.isPending}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2 rounded-lg disabled:opacity-60"
        >
          {updateMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          Save Settings
        </button>
      </div>

      {/* Admin: User Management */}
      {isAdmin && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
          <h2 className="font-semibold text-gray-700">User Management</h2>
          <div className="space-y-2">
            {(users ?? []).map((u: any) => (
              <div key={u.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-medium">{u.name}</p>
                  <p className="text-xs text-gray-400">{u.email} · {u.role}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {u.is_active ? 'Active' : 'Disabled'}
                  </span>
                  {u.role !== 'admin' && (
                    <button onClick={() => toggleUser.mutate(u.id)}
                      className="text-xs text-gray-500 hover:text-gray-700 underline">
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400">
            To create new users, use the Admin API: POST /v1/auth/admin/users
          </p>
        </div>
      )}
    </div>
  );
}

function Toggle({ label, description, checked, onChange }: {
  label: string; description?: string; checked: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${checked ? 'bg-brand-600' : 'bg-gray-200'}`}
      >
        <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${checked ? 'translate-x-4' : 'translate-x-1'}`} />
      </button>
    </div>
  );
}
