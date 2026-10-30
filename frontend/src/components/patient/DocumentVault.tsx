import React, { useState } from 'react';
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Eye,
  Calendar,
  Sparkles,
  ExternalLink,
  Bot,
  Pill,
  Activity,
  Stethoscope,
  Building,
  Check,
  FileUp,
} from 'lucide-react';
import { MedicalDocument, documentsApi } from '../../api/documents';
import { Modal } from '../common/Modal';

interface DocumentVaultProps {
  documents: MedicalDocument[];
  onRefresh: () => void;
}

export const DocumentVault: React.FC<DocumentVaultProps> = ({ documents, onRefresh }) => {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<MedicalDocument | null>(null);

  // Upload Form State (Zero manual classification)
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await documentsApi.uploadDocument(formData);
      setIsUploadOpen(false);
      setFile(null);
      onRefresh();
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfirm = async (docId: string) => {
    await documentsApi.confirmDocument(docId);
    if (selectedDoc) {
      setSelectedDoc({ ...selectedDoc, is_patient_confirmed: true, user_confirmed: true });
    }
    onRefresh();
  };

  const getDocTypeBadge = (type: string) => {
    switch (type) {
      case 'PRESCRIPTION':
        return { label: 'Prescription (প্রেসক্রিপশন)', color: 'bg-teal-50 text-teal-800 border-teal-200' };
      case 'LAB_REPORT':
        return { label: 'Lab Test Report (ল্যাব রিপোর্ট)', color: 'bg-indigo-50 text-indigo-800 border-indigo-200' };
      case 'DISCHARGE':
      case 'DISCHARGE_SUMMARY':
        return { label: 'Discharge Summary (ছাড়পত্র)', color: 'bg-amber-50 text-amber-800 border-amber-200' };
      case 'RADIOLOGY':
        return { label: 'Radiology / X-Ray', color: 'bg-purple-50 text-purple-800 border-purple-200' };
      default:
        return { label: 'Medical Record', color: 'bg-slate-100 text-slate-700 border-slate-200' };
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-lg font-bold text-medivault-navy flex items-center space-x-2">
            <FileText className="w-5 h-5 text-medivault-primary" />
            <span>Medical Vault & Records</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            AI automatically classifies document type, extracts consultation dates, and structures medications & lab biomarkers.
          </p>
        </div>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="flex items-center space-x-2 px-4 py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 transition shadow-sm"
        >
          <Upload className="w-4 h-4" />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Document List */}
      <div className="space-y-3">
        {documents.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
            <FileUp className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p className="text-sm font-bold text-slate-700">No medical documents uploaded yet</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Upload any prescription, lab report, or hospital summary. AI will automatically categorize it and extract the data.
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-4 inline-flex items-center space-x-1.5 px-4 py-2 bg-teal-50 text-medivault-primary border border-teal-200 rounded-xl text-xs font-bold hover:bg-teal-100 transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Upload Your First Document</span>
            </button>
          </div>
        ) : (
          documents.map((doc) => {
            const badge = getDocTypeBadge(doc.document_type);
            const isConfirmed = doc.is_patient_confirmed || doc.user_confirmed;

            return (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:border-teal-200 hover:bg-slate-50/50 transition cursor-pointer"
                onClick={() => setSelectedDoc(doc)}
              >
                <div className="flex items-center space-x-3.5">
                  <div className="w-11 h-11 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center text-medivault-primary shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-sm font-bold text-slate-900">{doc.title || badge.label}</h4>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${badge.color}`}>
                        {badge.label}
                      </span>
                      {isConfirmed && (
                        <span className="flex items-center space-x-0.5 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-bold">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Verified</span>
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
                      <span className="flex items-center space-x-1 font-medium text-slate-600">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{doc.document_date || 'Date pending AI extraction'}</span>
                      </span>
                      {doc.issuing_doctor_name && (
                        <>
                          <span>•</span>
                          <span className="flex items-center space-x-1 text-slate-600">
                            <Stethoscope className="w-3.5 h-3.5 text-slate-400" />
                            <span>{doc.issuing_doctor_name}</span>
                          </span>
                        </>
                      )}
                      {doc.issuing_clinic_name && (
                        <>
                          <span>•</span>
                          <span className="flex items-center space-x-1 text-slate-500">
                            <Building className="w-3.5 h-3.5 text-slate-400" />
                            <span>{doc.issuing_clinic_name}</span>
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedDoc(doc);
                    }}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-bold text-slate-700 hover:bg-white hover:border-slate-300 transition flex items-center space-x-1"
                  >
                    <Eye className="w-3.5 h-3.5 text-slate-500" />
                    <span>Review</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Zero-Config AI Upload Modal */}
      <Modal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} title="Upload Medical Document" maxWidth="md">
        <form onSubmit={handleUpload} className="space-y-4">
          {/* AI Automated Intelligence Note */}
          <div className="p-3.5 bg-gradient-to-r from-teal-50 to-blue-50 border border-teal-100 rounded-xl flex items-start space-x-3 text-xs text-slate-700">
            <Sparkles className="w-5 h-5 text-medivault-primary shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-medivault-navy">Automated AI Optical Analysis</p>
              <p className="text-slate-500 mt-0.5">
                No need to specify document type or date. MediVault AI automatically reads the scan, classifies whether it is a
                Prescription, Diagnostic Lab, or Discharge Summary, extracts the consultation date, and indexes all medications &
                biomarkers.
              </p>
            </div>
          </div>

          {/* Drag & Drop File Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                setFile(e.dataTransfer.files[0]);
              }
            }}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition ${
              isDragging
                ? 'border-medivault-primary bg-teal-50/50'
                : file
                ? 'border-emerald-400 bg-emerald-50/30'
                : 'border-slate-300 hover:border-teal-400 bg-slate-50/50'
            }`}
            onClick={() => document.getElementById('file-upload-input')?.click()}
          >
            <input
              id="file-upload-input"
              type="file"
              accept="image/*,application/pdf,.heic,.heif"
              className="hidden"
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
            />

            <div className="w-12 h-12 mx-auto rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-medivault-primary shadow-sm mb-3">
              {file ? <Check className="w-6 h-6 text-emerald-600" /> : <FileUp className="w-6 h-6" />}
            </div>

            {file ? (
              <div>
                <p className="text-sm font-bold text-slate-900">{file.name}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for AI extraction
                </p>
                <span className="text-[11px] text-teal-700 font-semibold mt-2 inline-block">
                  Click to choose a different file
                </span>
              </div>
            ) : (
              <div>
                <p className="text-sm font-bold text-slate-800">
                  Click to browse or drag & drop document
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Supports iPhone / Camera Photos (HEIC, JPEG, PNG, WebP) or Multi-page PDF (up to 10MB)
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setIsUploadOpen(false);
                setFile(null);
              }}
              className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || !file}
              className="px-5 py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 disabled:opacity-50 flex items-center space-x-2 shadow-sm transition"
            >
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span>{isUploading ? 'Extracting with AI...' : 'Upload & Auto-Classify'}</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Review Modal with AI-Extracted Entities */}
      <Modal
        isOpen={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        title={selectedDoc?.title || 'Extracted Document Insights'}
        maxWidth="2xl"
      >
        {selectedDoc && (
          <div className="space-y-5">
            {/* Classification & Metadata Banner */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200">
                <div className="flex items-center space-x-2">
                  <span className={`text-xs px-3 py-1 rounded-full border font-bold ${getDocTypeBadge(selectedDoc.document_type).color}`}>
                    {getDocTypeBadge(selectedDoc.document_type).label}
                  </span>
                  <span className="text-[11px] text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full font-semibold border border-teal-200 flex items-center space-x-1">
                    <Bot className="w-3 h-3" />
                    <span>AI Detected</span>
                  </span>
                </div>

                {selectedDoc.file_url && (
                  <a
                    href={selectedDoc.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1 text-xs text-medivault-primary font-bold hover:underline"
                  >
                    <span>View Original File</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                    Consultation Date
                  </span>
                  <span className="font-bold text-slate-800">{selectedDoc.document_date || 'Not stated'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                    Doctor / Clinician
                  </span>
                  <span className="font-bold text-slate-800">{selectedDoc.issuing_doctor_name || 'Not stated'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                    Clinic / Diagnostic Center
                  </span>
                  <span className="font-bold text-slate-800">{selectedDoc.issuing_clinic_name || 'Not stated'}</span>
                </div>
              </div>
            </div>

            {/* Extracted Structured Entities */}
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-medivault-primary" />
                <span>Extracted Clinical Entities ({selectedDoc.extracted_entities?.length || 0})</span>
              </h4>

              {(!selectedDoc.extracted_entities || selectedDoc.extracted_entities.length === 0) ? (
                <div className="p-6 text-center border border-dashed border-slate-200 rounded-xl text-slate-400 text-xs">
                  {selectedDoc.processing_status === 'COMPLETED'
                    ? 'No specific medications or lab tests were recognized in this document.'
                    : 'AI OCR analysis is currently processing this document. Please check back in a few seconds.'}
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {selectedDoc.extracted_entities.map((ent, idx) => {
                    const type = ent.entity_type || ent.category || 'RECORD';
                    const name = ent.entity_name || ent.normalized_name || ent.raw_text || 'Clinical Observation';
                    const value = ent.entity_value || (ent.numerical_value !== null && ent.numerical_value !== undefined ? `${ent.numerical_value} ${ent.unit || ''}` : null);

                    return (
                      <div
                        key={ent.id || idx}
                        className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 flex items-center justify-between text-xs hover:bg-white transition"
                      >
                        <div className="flex items-center space-x-2.5">
                          {type === 'MEDICATION' ? (
                            <Pill className="w-4 h-4 text-teal-600 shrink-0" />
                          ) : type === 'LAB_TEST' ? (
                            <Activity className="w-4 h-4 text-indigo-600 shrink-0" />
                          ) : (
                            <Stethoscope className="w-4 h-4 text-slate-500 shrink-0" />
                          )}
                          <div>
                            <span className="font-bold text-slate-900">{name}</span>
                            <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-semibold">
                              {type}
                            </span>
                            {ent.raw_snippet && (
                              <p className="text-[11px] text-slate-400 mt-0.5 italic">{ent.raw_snippet}</p>
                            )}
                          </div>
                        </div>

                        {value && (
                          <div className="text-right">
                            <span className={`font-mono font-bold ${ent.is_abnormal ? 'text-rose-600 bg-rose-50 px-2 py-0.5 rounded' : 'text-teal-700'}`}>
                              {value}
                            </span>
                            {ent.reference_range && (
                              <span className="block text-[10px] text-slate-400">Ref: {ent.reference_range}</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer Confirmation */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-400">
                {selectedDoc.is_patient_confirmed || selectedDoc.user_confirmed
                  ? 'Verified by patient and added to chronological timeline.'
                  : 'Review the AI-extracted details above and click confirm.'}
              </span>

              {!(selectedDoc.is_patient_confirmed || selectedDoc.user_confirmed) && (
                <button
                  onClick={() => handleConfirm(selectedDoc.id)}
                  className="flex items-center space-x-1.5 px-5 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold hover:bg-emerald-700 transition shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm Accuracy</span>
                </button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
