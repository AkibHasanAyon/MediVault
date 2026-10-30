import React, { useState } from 'react';
import { FileText, Upload, CheckCircle2, AlertTriangle, Eye, Calendar, Sparkles } from 'lucide-react';
import { MedicalDocument, documentsApi } from '../../api/documents';
import { Modal } from '../common/Modal';

interface DocumentVaultProps {
  documents: MedicalDocument[];
  onRefresh: () => void;
}

export const DocumentVault: React.FC<DocumentVaultProps> = ({ documents, onRefresh }) => {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<MedicalDocument | null>(null);

  // Upload Form State
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('PRESCRIPTION');
  const [docDate, setDocDate] = useState(new Date().toISOString().split('T')[0]);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', docType);
    formData.append('document_date', docDate);

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
      setSelectedDoc({ ...selectedDoc, is_patient_confirmed: true });
    }
    onRefresh();
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-medivault-navy flex items-center space-x-2">
            <FileText className="w-5 h-5 text-medivault-primary" />
            <span>Medical Vault & Records</span>
          </h2>
          <p className="text-xs text-slate-500">Chronological timeline of digital prescriptions and lab tests</p>
        </div>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="flex items-center space-x-1.5 px-4 py-2 bg-medivault-primary text-white rounded-xl text-xs font-semibold hover:bg-teal-700 transition shadow-sm"
        >
          <Upload className="w-4 h-4" />
          <span>Upload Record</span>
        </button>
      </div>

      {/* Document List */}
      <div className="space-y-3">
        {documents.length === 0 ? (
          <div className="text-center py-10 text-slate-400">
            <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-sm font-medium">No documents uploaded yet</p>
            <p className="text-xs text-slate-400 mt-1">Upload prescriptions or lab reports for AI extraction</p>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-3.5 rounded-xl border border-slate-100 hover:border-teal-200 hover:bg-slate-50/50 transition cursor-pointer"
              onClick={() => setSelectedDoc(doc)}
            >
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-teal-50 border border-teal-100 flex items-center justify-center text-medivault-primary">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h4 className="text-sm font-semibold text-slate-900">{doc.title || doc.document_type}</h4>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                      {doc.document_type}
                    </span>
                    {doc.is_patient_confirmed && (
                      <span className="flex items-center space-x-0.5 text-[10px] text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Verified</span>
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1">
                    <span className="flex items-center space-x-1">
                      <Calendar className="w-3 h-3" />
                      <span>{doc.document_date}</span>
                    </span>
                    <span>•</span>
                    <span className="text-teal-600 font-medium">
                      {doc.extracted_entities?.length || 0} entities extracted
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={(e) => { e.stopPropagation(); setSelectedDoc(doc); }}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-white flex items-center space-x-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Review</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Upload Modal */}
      <Modal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} title="Upload Medical Document">
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select File (PDF or Image)</label>
            <input
              type="file"
              required
              accept="image/*,application/pdf"
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
              className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-medivault-primary hover:file:bg-teal-100"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Document Category</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="PRESCRIPTION">Prescription (প্রেসক্রিপশন)</option>
              <option value="LAB_REPORT">Lab Test Report (ল্যাব রিপোর্ট)</option>
              <option value="DISCHARGE_SUMMARY">Discharge Summary (হাসপাতাল ছাড়পত্র)</option>
              <option value="OTHER">Other Health Record</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Record Date</label>
            <input
              type="date"
              required
              value={docDate}
              onChange={(e) => setDocDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <button
              type="button"
              onClick={() => setIsUploadOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || !file}
              className="px-4 py-2 bg-medivault-primary text-white rounded-lg text-xs font-semibold hover:bg-teal-700 disabled:opacity-50 flex items-center space-x-1"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isUploading ? 'Running OCR...' : 'Upload & Extract'}</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Review Modal */}
      <Modal
        isOpen={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        title={selectedDoc?.title || 'Extracted Medical Entities'}
        maxWidth="xl"
      >
        {selectedDoc && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-100">
              <span>Date: {selectedDoc.document_date}</span>
              <span>Status: <strong className="text-teal-700">{selectedDoc.processing_status}</strong></span>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                AI Extracted Entities ({selectedDoc.extracted_entities?.length || 0})
              </h4>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {selectedDoc.extracted_entities?.map((ent) => (
                  <div key={ent.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-800">{ent.normalized_name || ent.raw_text}</span>
                      <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-slate-200 text-slate-600">
                        {ent.category}
                      </span>
                    </div>
                    {ent.numerical_value !== null && (
                      <span className="font-mono font-bold text-teal-700">
                        {ent.numerical_value} {ent.unit}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-400">
                {selectedDoc.is_patient_confirmed ? 'Already confirmed by patient' : 'Please verify before adding to timeline'}
              </span>
              {!selectedDoc.is_patient_confirmed && (
                <button
                  onClick={() => handleConfirm(selectedDoc.id)}
                  className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition"
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

