'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { outreachApi, resumeApi, jobsApi } from '@/lib/api';
import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Copy } from 'lucide-react';

export default function OutreachPage() {
  const [jobId, setJobId] = useState('');
  const [resumeId, setResumeId] = useState('');
  const [messageType, setMessageType] = useState('linkedin_message');
  const [recipientName, setRecipientName] = useState('');

  const { data: messages, refetch } = useQuery({
    queryKey: ['outreach'],
    queryFn: () => outreachApi.list().then((r) => r.data),
  });

  const { data: resumes } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumeApi.list().then((r) => r.data),
  });

  const { data: jobData } = useQuery({
    queryKey: ['jobs-all'],
    queryFn: () => jobsApi.list({ page_size: 100 }).then((r) => r.data),
  });

  const generateMutation = useMutation({
    mutationFn: () => outreachApi.generate({
      job_id: jobId, resume_id: resumeId, message_type: messageType, recipient_name: recipientName || undefined,
    }),
    onSuccess: () => {
      toast.success('Message generated!');
      refetch();
    },
    onError: () => toast.error('Generation failed'),
  });

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">Outreach Messages</h1>

      {/* Generate Form */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-700">Generate New Message</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Resume</label>
            <select value={resumeId} onChange={(e) => setResumeId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">Select resume...</option>
              {resumes?.map((r: any) => <option key={r.id} value={r.id}>{r.filename}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Job</label>
            <select value={jobId} onChange={(e) => setJobId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">Select job...</option>
              {jobData?.jobs?.map((j: any) => <option key={j.id} value={j.id}>{j.title} @ {j.company}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Message Type</label>
            <select value={messageType} onChange={(e) => setMessageType(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="linkedin_message">LinkedIn Message</option>
              <option value="email_draft">Email Draft</option>
              <option value="follow_up">Follow-up</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Recipient Name (optional)</label>
            <input value={recipientName} onChange={(e) => setRecipientName(e.target.value)}
              placeholder="e.g. John Smith"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={!jobId || !resumeId || generateMutation.isPending}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2 rounded-lg disabled:opacity-60"
        >
          {generateMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          Generate Message
        </button>
      </div>

      {/* Messages list */}
      <div className="space-y-3">
        {(messages ?? []).map((m: any) => (
          <div key={m.id} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium bg-purple-50 text-purple-700 px-2 py-0.5 rounded capitalize">
                {m.message_type.replace('_', ' ')}
              </span>
              <button onClick={() => copy(m.content ?? '')}
                className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1">
                <Copy size={12} /> Copy
              </button>
            </div>
            {m.subject && <p className="text-xs text-gray-500 mb-1">Subject: {m.subject}</p>}
            <p className="text-sm text-gray-700 whitespace-pre-line line-clamp-5">{m.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
