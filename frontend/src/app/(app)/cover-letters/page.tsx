'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { coverLetterApi, resumeApi, jobsApi } from '@/lib/api';
import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Download } from 'lucide-react';
import { downloadBlob } from '@/lib/utils';

export default function CoverLettersPage() {
  const [jobId, setJobId] = useState('');
  const [resumeId, setResumeId] = useState('');
  const [tone, setTone] = useState('professional');

  const { data: letters, refetch } = useQuery({
    queryKey: ['cover-letters'],
    queryFn: () => coverLetterApi.list().then((r) => r.data),
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
    mutationFn: () => coverLetterApi.generate({ job_id: jobId, resume_id: resumeId, tone }),
    onSuccess: () => {
      toast.success('Cover letter generated!');
      refetch();
    },
    onError: () => toast.error('Generation failed'),
  });

  const handleDownload = async (id: string, fmt: 'pdf' | 'docx') => {
    const resp = await coverLetterApi.download(id, fmt);
    downloadBlob(resp.data, `cover_letter.${fmt}`);
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">Cover Letters</h1>

      {/* Generate Form */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-700">Generate New</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Resume</label>
            <select value={resumeId} onChange={(e) => setResumeId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">Select resume...</option>
              {resumes?.map((r: any) => (
                <option key={r.id} value={r.id}>{r.filename}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Job</label>
            <select value={jobId} onChange={(e) => setJobId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">Select job...</option>
              {jobData?.jobs?.map((j: any) => (
                <option key={j.id} value={j.id}>{j.title} @ {j.company}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tone</label>
            <select value={tone} onChange={(e) => setTone(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="professional">Professional</option>
              <option value="enthusiastic">Enthusiastic</option>
              <option value="concise">Concise</option>
            </select>
          </div>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={!jobId || !resumeId || generateMutation.isPending}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2 rounded-lg disabled:opacity-60"
        >
          {generateMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          Generate Cover Letter
        </button>
      </div>

      {/* Letters List */}
      <div className="space-y-3">
        {(letters ?? []).map((l: any) => (
          <div key={l.id} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-800">Cover Letter</p>
                <p className="text-xs text-gray-400 capitalize">{l.tone} tone</p>
              </div>
              <div className="flex gap-2">
                {l.file_path_pdf && (
                  <button onClick={() => handleDownload(l.id, 'pdf')}
                    className="flex items-center gap-1 text-xs border border-gray-300 text-gray-600 hover:bg-gray-50 px-3 py-1.5 rounded-lg">
                    <Download size={12} /> PDF
                  </button>
                )}
                {l.file_path_docx && (
                  <button onClick={() => handleDownload(l.id, 'docx')}
                    className="flex items-center gap-1 text-xs border border-gray-300 text-gray-600 hover:bg-gray-50 px-3 py-1.5 rounded-lg">
                    <Download size={12} /> DOCX
                  </button>
                )}
              </div>
            </div>
            {l.content && (
              <p className="mt-3 text-sm text-gray-600 line-clamp-3 whitespace-pre-line">{l.content}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
