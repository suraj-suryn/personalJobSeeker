'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { resumeApi } from '@/lib/api';
import { toast } from 'sonner';
import { Upload, Trash2, Star, FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ResumesPage() {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);

  const { data: resumes, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumeApi.list().then((r) => r.data),
  });

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return;
    setUploading(true);
    try {
      await resumeApi.upload(files[0], resumes?.length === 0);
      toast.success('Resume uploaded and parsed!');
      qc.invalidateQueries({ queryKey: ['resumes'] });
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [resumes, qc]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
    maxFiles: 1,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resumeApi.delete(id),
    onSuccess: () => {
      toast.success('Resume deleted');
      qc.invalidateQueries({ queryKey: ['resumes'] });
    },
  });

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Resumes</h1>
      </div>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
          isDragActive ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex flex-col items-center gap-2 text-brand-600">
            <Loader2 size={32} className="animate-spin" />
            <p>Parsing resume...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <Upload size={32} className={isDragActive ? 'text-brand-500' : ''} />
            <p className="font-medium">Drop your resume here, or click to browse</p>
            <p className="text-sm">PDF or DOCX, max 10MB</p>
          </div>
        )}
      </div>

      {/* Resume List */}
      {isLoading ? (
        <div className="flex justify-center py-8"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
      ) : resumes?.length === 0 ? (
        <p className="text-center text-gray-400 py-8">No resumes uploaded yet</p>
      ) : (
        <div className="space-y-3">
          {resumes?.map((r: any) => (
            <div key={r.id} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4">
              <div className="bg-blue-50 text-blue-600 p-2.5 rounded-lg">
                <FileText size={20} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-800 truncate">{r.filename}</p>
                  {r.is_primary && (
                    <span className="inline-flex items-center gap-1 text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                      <Star size={10} />Primary
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 capitalize">{r.parse_status} · {r.file_type.toUpperCase()}</p>
              </div>
              <button
                onClick={() => deleteMutation.mutate(r.id)}
                className="text-red-400 hover:text-red-600 p-1 rounded"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
