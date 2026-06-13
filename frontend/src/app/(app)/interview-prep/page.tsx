'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { interviewPrepApi, resumeApi, jobsApi } from '@/lib/api';
import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, ChevronDown, ChevronUp } from 'lucide-react';

export default function InterviewPrepPage() {
  const [jobId, setJobId] = useState('');
  const [resumeId, setResumeId] = useState('');
  const [prep, setPrep] = useState<any>(null);

  const { data: resumes } = useQuery({ queryKey: ['resumes'], queryFn: () => resumeApi.list().then((r) => r.data) });
  const { data: jobData } = useQuery({ queryKey: ['jobs-all'], queryFn: () => jobsApi.list({ page_size: 100 }).then((r) => r.data) });

  const generateMutation = useMutation({
    mutationFn: () => interviewPrepApi.generate(jobId, resumeId),
    onSuccess: (data) => { setPrep(data.data); toast.success('Interview prep ready!'); },
    onError: () => toast.error('Generation failed'),
  });

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">Interview Prep</h1>

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
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
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={!jobId || !resumeId || generateMutation.isPending}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2 rounded-lg disabled:opacity-60"
        >
          {generateMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          Generate Prep Materials
        </button>
      </div>

      {prep && (
        <div className="space-y-4">
          <PrepSection title="Technical Questions" items={prep.technical_questions} />
          <PrepSection title="Behavioral Questions (STAR)" items={prep.behavioral_questions} />
          <PrepSection title="Company-specific Questions" items={prep.company_questions} />
          <PrepSection title="Questions to Ask Them" items={prep.questions_to_ask} />
          <PrepSection title="Key Talking Points" items={prep.key_talking_points} />
          {prep.red_flags_to_address?.length > 0 && (
            <PrepSection title="Red Flags to Address" items={prep.red_flags_to_address} variant="warning" />
          )}
        </div>
      )}
    </div>
  );
}

function PrepSection({ title, items, variant = 'default' }: { title: string; items: any[]; variant?: string }) {
  const [open, setOpen] = useState(true);
  if (!items?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-5 py-3 text-left">
        <h3 className="font-semibold text-gray-700">{title}</h3>
        {open ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>
      {open && (
        <div className={`px-5 pb-4 space-y-2 ${variant === 'warning' ? 'bg-orange-50' : ''}`}>
          {items.map((item: any, i: number) => (
            <div key={i} className="border-l-2 border-brand-300 pl-3 py-1">
              {typeof item === 'string' ? (
                <p className="text-sm text-gray-700">{item}</p>
              ) : (
                <>
                  <p className="text-sm font-medium text-gray-800">{item.question}</p>
                  {item.answer && <p className="text-xs text-gray-500 mt-1">{item.answer}</p>}
                  {item.example && <p className="text-xs text-blue-500 mt-1 italic">{item.example}</p>}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
