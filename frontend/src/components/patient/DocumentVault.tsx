import React, { useState, useMemo } from 'react';
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
  Edit3,
  Save,
  Plus,
  Trash2,
  X,
  ChevronDown,
  ChevronUp,
  Layers,
  Files,
  FileImage,
  RefreshCw,
} from 'lucide-react';
import { MedicalDocument, DocumentEntity, documentsApi } from '../../api/documents';
import { Modal } from '../common/Modal';

interface DocumentVaultProps {
  documents: MedicalDocument[];
  onRefresh: () => void;
}

export const DocumentVault: React.FC<DocumentVaultProps> = ({ documents, onRefresh }) => {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<MedicalDocument | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Upload Form State (Multiple files support)
  const [files, setFiles] = useState<File[]>([]);
  const [combineFiles, setCombineFiles] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgressMsg, setUploadProgressMsg] = useState('');

  // Editing state for selected document
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editType, setEditType] = useState<MedicalDocument['document_type']>('OTHER');
  const [editDate, setEditDate] = useState('');
  const [editDoctor, setEditDoctor] = useState('');
  const [editClinic, setEditClinic] = useState('');
  const [editEntities, setEditEntities] = useState<DocumentEntity[]>([]);
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [showRawOcr, setShowRawOcr] = useState(false);
  const [selectedCategoryTab, setSelectedCategoryTab] = useState('ALL');

  // When a document is selected, load fresh full detail from API
  const handleOpenDoc = async (doc: MedicalDocument) => {
    setSelectedDoc(doc);
    setIsEditing(false);
    setShowRawOcr(false);
    setSelectedCategoryTab('ALL');
    setIsLoadingDetail(true);

    // Initial sync from passed doc
    setEditTitle(doc.title || '');
    setEditType(doc.document_type || 'OTHER');
    setEditDate(doc.document_date || '');
    setEditDoctor(doc.issuing_doctor_name || '');
    setEditClinic(doc.issuing_clinic_name || '');
    setEditEntities(doc.extracted_entities ? [...doc.extracted_entities] : []);

    try {
      const fullDoc = await documentsApi.getDocument(doc.id);
      setSelectedDoc(fullDoc);
      setEditTitle(fullDoc.title || '');
      setEditType(fullDoc.document_type || 'OTHER');
      setEditDate(fullDoc.document_date || '');
      setEditDoctor(fullDoc.issuing_doctor_name || '');
      setEditClinic(fullDoc.issuing_clinic_name || '');
      setEditEntities(fullDoc.extracted_entities ? [...fullDoc.extracted_entities] : []);
    } catch {
      // Keep doc from timeline if detail fetch fails
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleFilesChosen = (incoming: FileList | File[] | null) => {
    if (!incoming) return;
    const array = Array.from(incoming);
    // Append new files without duplicates
    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => `${f.name}_${f.size}`));
      const newFiles = array.filter((f) => !existingNames.has(`${f.name}_${f.size}`));
      return [...prev, ...newFiles];
    });
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadProgressMsg(
      files.length > 1
        ? combineFiles
          ? `Merging ${files.length} images into unified document...`
          : `Uploading ${files.length} documents...`
        : 'Uploading and processing document...'
    );

    const formData = new FormData();
    if (files.length === 1) {
      formData.append('file', files[0]);
    } else {
      files.forEach((f) => {
        formData.append('files', f);
      });
      formData.append('combine', combineFiles ? 'true' : 'false');
    }

    try {
      await documentsApi.uploadDocument(formData);
      setIsUploadOpen(false);
      setFiles([]);
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.message || 'Upload failed. Please check file format and try again.');
    } finally {
      setIsUploading(false);
      setUploadProgressMsg('');
    }
  };

  const handleQuickConfirm = async (docId: string) => {
    try {
      await documentsApi.confirmDocument(docId);
      if (selectedDoc) {
        setSelectedDoc({ ...selectedDoc, is_patient_confirmed: true, user_confirmed: true });
      }
      onRefresh();
    } catch (err: any) {
      alert('Confirmation failed. Please try again.');
    }
  };

  const handleSaveReview = async () => {
    if (!selectedDoc) return;
    setIsSavingReview(true);

    try {
      const payload = {
        title: editTitle,
        document_type: editType,
        document_date: editDate || null,
        issuing_doctor_name: editDoctor,
        issuing_clinic_name: editClinic,
        entities: editEntities.map((ent) => ({
          id: ent.id,
          entity_type: ent.entity_type || ent.category || 'MEDICATION',
          entity_name: ent.entity_name || ent.normalized_name || 'Clinical Item',
          entity_value: ent.entity_value || '',
          unit: ent.unit || '',
          reference_range: ent.reference_range || '',
          is_abnormal: Boolean(ent.is_abnormal),
          raw_snippet: ent.raw_snippet || '',
        })),
      };

      const updated = await documentsApi.reviewDocument(selectedDoc.id, payload);
      setSelectedDoc(updated);
      setIsEditing(false);
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to save changes. Please try again.');
    } finally {
      setIsSavingReview(false);
    }
  };

  const handleAddEntity = (type: 'MEDICATION' | 'LAB_TEST' | 'DIAGNOSIS' | 'ADVICE') => {
    const newEnt: DocumentEntity = {
      id: '',
      entity_type: type,
      entity_name: '',
      entity_value: '',
      unit: '',
      reference_range: '',
      is_abnormal: false,
    };
    setEditEntities([...editEntities, newEnt]);
    if (!isEditing) setIsEditing(true);
  };

  const handleUpdateEntityField = (index: number, field: keyof DocumentEntity, val: any) => {
    setEditEntities((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: val };
      return updated;
    });
  };

  const handleRemoveEntity = (index: number) => {
    setEditEntities((prev) => prev.filter((_, i) => i !== index));
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

  const getEntityCategory = (ent: DocumentEntity): string => {
    const type = ent.entity_type || ent.category || 'MEDICATION';
    if (type === 'MEDICATION') return 'Medications';
    if (type === 'DIAGNOSIS') return 'Diagnoses';
    if (type === 'ADVICE') return 'Advice';

    const name = (ent.entity_name || '').toLowerCase();
    if (
      name.includes('cbc') || name.includes('rbc') || name.includes('wbc') ||
      name.includes('hemoglobin') || name.includes('platelet') || name.includes('mcv') ||
      name.includes('mch') || name.includes('polymorph') || name.includes('lymphocyte') ||
      name.includes('eosinophil') || name.includes('monocyte') || name.includes('basophil') ||
      name.includes('hct') || name.includes('rdw') || name.includes('mpv') || name.includes('pct') ||
      name.includes('pdw') || name.includes('esr')
    ) {
      return 'Hematology & CBC';
    }
    if (
      name.includes('ultrasound') || name.includes('usg') || name.includes('liver') ||
      name.includes('gall') || name.includes('spleen') || name.includes('pancreas') ||
      name.includes('kidney') || name.includes('bladder') || name.includes('prostate') ||
      name.includes('biliary')
    ) {
      return 'Ultrasound & Imaging';
    }
    if (
      name.includes('urine') || name.includes('urinalysis') || name.includes('pus') ||
      name.includes('epithelial') || name.includes('cast') || name.includes('sediment') ||
      name.includes('specific gravity')
    ) {
      return 'Urinalysis';
    }
    if (
      name.includes('tsh') || name.includes('t4') || name.includes('t3') ||
      name.includes('thyroxine') || name.includes('vitamin')
    ) {
      return 'Endocrinology & Thyroid';
    }
    if (
      name.includes('glucose') || name.includes('alt') || name.includes('gpt') ||
      name.includes('creatinine') || name.includes('cholesterol') || name.includes('hdl') ||
      name.includes('ldl') || name.includes('triglyceride') || name.includes('uric')
    ) {
      return 'Biochemistry';
    }
    return 'Other Findings';
  };

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    editEntities.forEach((ent) => {
      const cat = getEntityCategory(ent);
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [editEntities]);

  const filteredEntities = useMemo(() => {
    if (selectedCategoryTab === 'ALL') return editEntities.map((ent, originalIdx) => ({ ent, originalIdx }));
    return editEntities
      .map((ent, originalIdx) => ({ ent, originalIdx }))
      .filter(({ ent }) => getEntityCategory(ent) === selectedCategoryTab);
  }, [editEntities, selectedCategoryTab]);

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
          onClick={() => {
            setFiles([]);
            setCombineFiles(true);
            setIsUploadOpen(true);
          }}
          className="flex items-center space-x-2 px-4 py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 transition shadow-sm"
        >
          <Upload className="w-4 h-4" />
          <span>Upload Documents / Photos</span>
        </button>
      </div>

      {/* Document List */}
      <div className="space-y-3">
        {documents.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
            <FileUp className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p className="text-sm font-bold text-slate-700">No medical documents uploaded yet</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Upload any prescription, lab report, or hospital summary (single or multi-page photos). AI will automatically categorize it and extract the data.
            </p>
            <button
              onClick={() => {
                setFiles([]);
                setCombineFiles(true);
                setIsUploadOpen(true);
              }}
              className="mt-4 inline-flex items-center space-x-1.5 px-4 py-2 bg-teal-50 text-medivault-primary border border-teal-200 rounded-xl text-xs font-bold hover:bg-teal-100 transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Upload Documents</span>
            </button>
          </div>
        ) : (
          documents.map((doc) => {
            const badge = getDocTypeBadge(doc.document_type);
            const isConfirmed = doc.is_patient_confirmed || doc.user_confirmed;
            const totalEntities =
              (doc.extracted_entities?.length || 0) ||
              ((doc.medication_count || 0) + (doc.lab_test_count || 0) + (doc.diagnosis_count || 0));

            return (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:border-teal-200 hover:bg-slate-50/50 transition cursor-pointer"
                onClick={() => handleOpenDoc(doc)}
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
                      {totalEntities > 0 && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold border border-slate-200">
                          {totalEntities} clinical {totalEntities === 1 ? 'item' : 'items'}
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
                          <span className="flex items-center space-x-1 text-slate-600 font-medium">
                            <Stethoscope className="w-3.5 h-3.5 text-teal-600" />
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
                      handleOpenDoc(doc);
                    }}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-bold text-slate-700 hover:bg-white hover:border-slate-300 transition flex items-center space-x-1"
                  >
                    <Eye className="w-3.5 h-3.5 text-slate-500" />
                    <span>Review & Edit</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Multi-File AI Upload Modal */}
      <Modal isOpen={isUploadOpen} onClose={() => !isUploading && setIsUploadOpen(false)} title="Upload Medical Documents / Camera Photos" maxWidth="lg">
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="p-3.5 bg-gradient-to-r from-teal-50 to-blue-50 border border-teal-100 rounded-xl flex items-start space-x-3 text-xs text-slate-700">
            <Sparkles className="w-5 h-5 text-medivault-primary shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-medivault-navy">Automated Multi-File AI Optical Analysis</p>
              <p className="text-slate-500 mt-0.5">
                Upload single photos or select multiple image files at once (e.g. multi-page prescriptions or lab reports). MediVault AI automatically cleans, OCRs, classifies, and structures all pages.
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
              handleFilesChosen(e.dataTransfer.files);
            }}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition ${
              isDragging
                ? 'border-medivault-primary bg-teal-50/50'
                : files.length > 0
                ? 'border-teal-400 bg-teal-50/20'
                : 'border-slate-300 hover:border-teal-400 bg-slate-50/50'
            }`}
            onClick={() => document.getElementById('multi-file-upload-input')?.click()}
          >
            <input
              id="multi-file-upload-input"
              type="file"
              multiple
              accept="image/*,application/pdf,.heic,.heif"
              className="hidden"
              onChange={(e) => handleFilesChosen(e.target.files)}
            />

            <div className="w-12 h-12 mx-auto rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-medivault-primary shadow-sm mb-3">
              {files.length > 0 ? <Files className="w-6 h-6 text-teal-600" /> : <FileUp className="w-6 h-6" />}
            </div>

            <div>
              <p className="text-sm font-bold text-slate-800">
                Click to browse or drag & drop files here
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Select one or multiple images (HEIC, JPEG, PNG, WebP) or PDFs (up to 10MB each)
              </p>
            </div>
          </div>

          {/* Selected Files List */}
          {files.length > 0 && (
            <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span>Selected Files ({files.length})</span>
                <button
                  type="button"
                  onClick={() => document.getElementById('multi-file-upload-input')?.click()}
                  className="text-medivault-primary hover:underline flex items-center space-x-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add more files</span>
                </button>
              </div>

              <div className="max-h-40 overflow-y-auto space-y-2 pr-1">
                {files.map((f, idx) => (
                  <div
                    key={`${f.name}-${idx}`}
                    className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-slate-200 text-xs"
                  >
                    <div className="flex items-center space-x-2.5 truncate">
                      <FileImage className="w-4 h-4 text-teal-600 shrink-0" />
                      <span className="font-semibold text-slate-800 truncate">{f.name}</span>
                      <span className="text-[10px] text-slate-400 shrink-0">
                        ({(f.size / (1024 * 1024)).toFixed(2)} MB)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(idx);
                      }}
                      className="p-1 text-slate-400 hover:text-rose-500 rounded transition shrink-0 ml-2"
                      title="Remove file"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Multi-page Merge vs Separate Option */}
              {files.length > 1 && (
                <div className="pt-3 border-t border-slate-200 text-xs space-y-2">
                  <span className="font-bold text-slate-700 block">Upload Mode:</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <label
                      className={`p-3 rounded-xl border cursor-pointer flex items-start space-x-2.5 transition ${
                        combineFiles
                          ? 'border-medivault-primary bg-teal-50/50 text-slate-900 font-semibold'
                          : 'border-slate-200 bg-white text-slate-600'
                      }`}
                    >
                      <input
                        type="radio"
                        name="combine_mode"
                        checked={combineFiles}
                        onChange={() => setCombineFiles(true)}
                        className="mt-0.5 text-medivault-primary"
                      />
                      <div>
                        <div className="flex items-center space-x-1">
                          <Layers className="w-3.5 h-3.5 text-teal-600" />
                          <span>Merge into 1 Document</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5 font-normal">
                          For multi-page prescriptions or multi-page lab reports. OCR will extract everything together.
                        </p>
                      </div>
                    </label>

                    <label
                      className={`p-3 rounded-xl border cursor-pointer flex items-start space-x-2.5 transition ${
                        !combineFiles
                          ? 'border-medivault-primary bg-teal-50/50 text-slate-900 font-semibold'
                          : 'border-slate-200 bg-white text-slate-600'
                      }`}
                    >
                      <input
                        type="radio"
                        name="combine_mode"
                        checked={!combineFiles}
                        onChange={() => setCombineFiles(false)}
                        className="mt-0.5 text-medivault-primary"
                      />
                      <div>
                        <div className="flex items-center space-x-1">
                          <Files className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Upload as Separate Records</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5 font-normal">
                          Upload each file as an individual document (e.g. different visits or dates).
                        </p>
                      </div>
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              disabled={isUploading}
              onClick={() => {
                setIsUploadOpen(false);
                setFiles([]);
              }}
              className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || files.length === 0}
              className="px-5 py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 disabled:opacity-50 flex items-center space-x-2 shadow-sm transition"
            >
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span>
                {isUploading
                  ? uploadProgressMsg || 'Uploading...'
                  : files.length > 1
                  ? combineFiles
                    ? `Merge & Upload (${files.length} Pages)`
                    : `Upload ${files.length} Documents`
                  : 'Upload & Auto-Classify'}
              </span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Comprehensive Review & Inline Editing Modal */}
      <Modal
        isOpen={!!selectedDoc}
        onClose={() => {
          if (!isSavingReview) {
            setSelectedDoc(null);
            setIsEditing(false);
          }
        }}
        title={selectedDoc?.title || 'Extracted Document Insights'}
        maxWidth="2xl"
      >
        {selectedDoc && (
          <div className="space-y-5">
            {/* Top Toolbar */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200">
                <div className="flex items-center space-x-2">
                  <span className={`text-xs px-3 py-1 rounded-full border font-bold ${getDocTypeBadge(editType).color}`}>
                    {getDocTypeBadge(editType).label}
                  </span>
                  <span className="text-[11px] text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full font-semibold border border-teal-200 flex items-center space-x-1">
                    <Bot className="w-3 h-3" />
                    <span>AI Extracted</span>
                  </span>
                  {(selectedDoc.is_patient_confirmed || selectedDoc.user_confirmed) && (
                    <span className="text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-bold border border-emerald-200 flex items-center space-x-1">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Verified by Patient</span>
                    </span>
                  )}
                  {isLoadingDetail && (
                    <span className="text-[11px] text-slate-400 flex items-center space-x-1">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      <span>Loading complete records...</span>
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-3 text-xs">
                  {selectedDoc.file_url && (
                    <a
                      href={selectedDoc.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center space-x-1 text-medivault-primary font-bold hover:underline"
                    >
                      <span>View Original File</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                  {!isEditing ? (
                    <button
                      type="button"
                      onClick={() => setIsEditing(true)}
                      className="px-3 py-1 bg-white border border-slate-300 rounded-lg font-bold text-slate-700 hover:border-teal-400 hover:text-medivault-primary transition flex items-center space-x-1 shadow-sm"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Edit Information</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1 bg-white border border-slate-300 rounded-lg font-bold text-slate-600 hover:bg-slate-100 transition"
                    >
                      Cancel Editing
                    </button>
                  )}
                </div>
              </div>

              {/* Document Metadata (View vs Edit Mode) */}
              {!isEditing ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                      Title
                    </span>
                    <span className="font-bold text-slate-800">{editTitle || selectedDoc.title || 'Untitled Document'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                      Consultation Date
                    </span>
                    <span className="font-bold text-slate-800">{editDate || 'Not stated'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                      Ordering Doctor
                    </span>
                    <span className="font-bold text-slate-800">{editDoctor || 'Not stated'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] font-bold uppercase tracking-wider">
                      Clinic / Center
                    </span>
                    <span className="font-bold text-slate-800">{editClinic || 'Not stated'}</span>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
                  <div>
                    <label className="text-slate-500 block text-[10px] font-bold uppercase mb-1">
                      Document Title
                    </label>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      placeholder="e.g. Diagnostic Lab Report - Padma Diagnostic Centre"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-500 block text-[10px] font-bold uppercase mb-1">
                      Document Type
                    </label>
                    <select
                      value={editType}
                      onChange={(e) => setEditType(e.target.value as any)}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500 bg-white"
                    >
                      <option value="PRESCRIPTION">Prescription (প্রেসক্রিপশন)</option>
                      <option value="LAB_REPORT">Diagnostic Lab Report (ল্যাব রিপোর্ট)</option>
                      <option value="RADIOLOGY">Radiology / Imaging / X-Ray</option>
                      <option value="DISCHARGE">Discharge Summary (ছাড়পত্র)</option>
                      <option value="OTHER">Other Health Document</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-500 block text-[10px] font-bold uppercase mb-1">
                      Consultation / Test Date
                    </label>
                    <input
                      type="date"
                      value={editDate}
                      onChange={(e) => setEditDate(e.target.value)}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-500 block text-[10px] font-bold uppercase mb-1">
                      Doctor / Ordering Clinician (Referred By)
                    </label>
                    <input
                      type="text"
                      value={editDoctor}
                      onChange={(e) => setEditDoctor(e.target.value)}
                      placeholder="e.g. Khaleda Khatun MSC MPH or Dr. ..."
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-slate-500 block text-[10px] font-bold uppercase mb-1">
                      Clinic / Hospital / Diagnostic Centre
                    </label>
                    <input
                      type="text"
                      value={editClinic}
                      onChange={(e) => setEditClinic(e.target.value)}
                      placeholder="e.g. Padma Diagnostic Centre Limited"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Structured Entities Section */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-medivault-primary" />
                  <span>
                    Extracted Clinical Entities ({editEntities.length})
                  </span>
                </h4>

                {isEditing && (
                  <div className="flex items-center space-x-1.5 text-xs">
                    <span className="text-slate-400 text-[11px]">Add:</span>
                    <button
                      type="button"
                      onClick={() => handleAddEntity('MEDICATION')}
                      className="px-2 py-1 bg-teal-50 text-teal-700 border border-teal-200 rounded-lg font-bold hover:bg-teal-100 flex items-center space-x-1 text-[11px]"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Medicine</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAddEntity('LAB_TEST')}
                      className="px-2 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg font-bold hover:bg-indigo-100 flex items-center space-x-1 text-[11px]"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Lab Test</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAddEntity('DIAGNOSIS')}
                      className="px-2 py-1 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg font-bold hover:bg-purple-100 flex items-center space-x-1 text-[11px]"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Diagnosis</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Category Filter Tabs */}
              {editEntities.length > 5 && Object.keys(categoryCounts).length > 1 && (
                <div className="flex flex-wrap items-center gap-1.5 mb-3 pb-2 border-b border-slate-100">
                  <button
                    type="button"
                    onClick={() => setSelectedCategoryTab('ALL')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition flex items-center space-x-1 ${
                      selectedCategoryTab === 'ALL'
                        ? 'bg-medivault-primary text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <span>All</span>
                    <span className="text-[10px] opacity-80">({editEntities.length})</span>
                  </button>

                  {Object.entries(categoryCounts).map(([cat, count]) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setSelectedCategoryTab(cat)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-bold transition flex items-center space-x-1 ${
                        selectedCategoryTab === cat
                          ? 'bg-medivault-primary text-white shadow-xs'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      <span>{cat}</span>
                      <span className="text-[10px] opacity-80">({count})</span>
                    </button>
                  ))}
                </div>
              )}

              {editEntities.length === 0 ? (
                <div className="p-8 text-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50 text-slate-500 text-xs space-y-2">
                  <FileText className="w-8 h-8 mx-auto text-slate-300" />
                  <p className="font-semibold">
                    {selectedDoc.processing_status === 'COMPLETED'
                      ? 'No clinical entities were automatically detected in this document.'
                      : 'AI OCR analysis is currently processing this document. Please check back in a few seconds.'}
                  </p>
                  <p className="text-slate-400 text-[11px]">
                    You can click below to manually add medications or lab test results from your document.
                  </p>
                  {!isEditing && (
                    <button
                      type="button"
                      onClick={() => {
                        setIsEditing(true);
                        handleAddEntity('LAB_TEST');
                      }}
                      className="mt-2 inline-flex items-center space-x-1 px-3 py-1.5 bg-medivault-primary text-white rounded-lg font-bold text-xs hover:bg-teal-700 transition"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Extracted Data Manually</span>
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                  {filteredEntities.map(({ ent, originalIdx: idx }) => {
                    const type = ent.entity_type || ent.category || 'MEDICATION';
                    const name = ent.entity_name || ent.normalized_name || ent.raw_text || '';
                    const value = ent.entity_value || (ent.numerical_value !== null && ent.numerical_value !== undefined ? `${ent.numerical_value}` : '');
                    const isLongObservation = Boolean(value && (value.length > 40 || name.toLowerCase().includes('ultrasound')));

                    if (!isEditing) {
                      // View Mode: Long Observation / Ultrasound Card
                      if (isLongObservation) {
                        return (
                          <div
                            key={ent.id || idx}
                            className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs hover:bg-white transition space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2.5">
                                <div className="w-8 h-8 rounded-lg bg-indigo-100/60 flex items-center justify-center text-indigo-700 shrink-0">
                                  <Activity className="w-4 h-4" />
                                </div>
                                <div>
                                  <div className="flex items-center space-x-2">
                                    <span className="font-bold text-slate-900">{name || 'Unnamed Finding'}</span>
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-semibold uppercase">
                                      {type}
                                    </span>
                                  </div>
                                  {ent.raw_snippet && (
                                    <p className="text-[11px] text-slate-400 mt-0.5 italic">{ent.raw_snippet}</p>
                                  )}
                                </div>
                              </div>
                              {ent.is_abnormal && (
                                <span className="text-[10px] font-bold text-rose-600 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-md shrink-0">
                                  Abnormal Finding
                                </span>
                              )}
                            </div>

                            <div className="p-3 bg-white rounded-lg border border-slate-200 text-slate-800 font-normal leading-relaxed text-xs">
                              {value}
                            </div>

                            {ent.reference_range && (
                              <div className="text-[11px] text-slate-500 font-medium">
                                <span className="font-bold text-slate-600">Reference:</span> {ent.reference_range}
                              </div>
                            )}
                          </div>
                        );
                      }

                      // View Mode: Standard Lab / Medication / Diagnosis Row
                      return (
                        <div
                          key={ent.id || idx}
                          className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs hover:bg-white transition"
                        >
                          <div className="flex items-center space-x-3">
                            <div className="shrink-0">
                              {type === 'MEDICATION' ? (
                                <div className="w-8 h-8 rounded-lg bg-teal-100/60 flex items-center justify-center text-teal-700">
                                  <Pill className="w-4 h-4" />
                                </div>
                              ) : type === 'LAB_TEST' ? (
                                <div className="w-8 h-8 rounded-lg bg-indigo-100/60 flex items-center justify-center text-indigo-700">
                                  <Activity className="w-4 h-4" />
                                </div>
                              ) : (
                                <div className="w-8 h-8 rounded-lg bg-purple-100/60 flex items-center justify-center text-purple-700">
                                  <Stethoscope className="w-4 h-4" />
                                </div>
                              )}
                            </div>
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-bold text-slate-900">{name || 'Unnamed Item'}</span>
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-semibold uppercase">
                                  {type}
                                </span>
                              </div>
                              {ent.raw_snippet && (
                                <p className="text-[11px] text-slate-400 mt-0.5 italic">{ent.raw_snippet}</p>
                              )}
                            </div>
                          </div>

                          {(value || ent.unit || ent.reference_range) && (
                            <div className="text-right max-w-sm ml-4">
                              <span
                                className={`font-mono font-bold text-xs ${
                                  ent.is_abnormal
                                    ? 'text-rose-600 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-md'
                                    : 'text-teal-800'
                                }`}
                              >
                                {value} {ent.unit || ''}
                              </span>
                              {ent.reference_range && (
                                <span className="block text-[10px] text-slate-500 mt-0.5 leading-tight font-medium">
                                  Ref: {ent.reference_range}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    }

                    // Edit Mode Card
                    return (
                      <div
                        key={ent.id || idx}
                        className="p-3 bg-white rounded-xl border border-slate-200 text-xs space-y-2 hover:border-teal-300 transition"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center space-x-2 w-full">
                            <select
                              value={type}
                              onChange={(e) => handleUpdateEntityField(idx, 'entity_type', e.target.value)}
                              className="px-2 py-1 border border-slate-300 rounded-lg text-xs font-semibold bg-slate-50 focus:outline-none"
                            >
                              <option value="MEDICATION">Medication</option>
                              <option value="LAB_TEST">Lab Test</option>
                              <option value="DIAGNOSIS">Diagnosis</option>
                              <option value="ADVICE">Advice</option>
                            </select>

                            <input
                              type="text"
                              value={name}
                              onChange={(e) => handleUpdateEntityField(idx, 'entity_name', e.target.value)}
                              placeholder={type === 'MEDICATION' ? 'e.g. Nexum 20mg' : 'e.g. Fasting Blood Glucose'}
                              className="flex-1 px-3 py-1 border border-slate-300 rounded-lg text-xs font-bold text-slate-900 focus:outline-none focus:border-teal-500"
                            />
                          </div>

                          <button
                            type="button"
                            onClick={() => handleRemoveEntity(idx)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition"
                            title="Delete Item"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>

                        {type === 'LAB_TEST' ? (
                          isLongObservation ? (
                            <div className="space-y-2 pt-1">
                              <div>
                                <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">
                                  Observation Finding / Measurement
                                </label>
                                <textarea
                                  rows={2}
                                  value={value}
                                  onChange={(e) => handleUpdateEntityField(idx, 'entity_value', e.target.value)}
                                  placeholder="Observation details..."
                                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs leading-relaxed"
                                />
                              </div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                <div>
                                  <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Reference / Notes</label>
                                  <input
                                    type="text"
                                    value={ent.reference_range || ''}
                                    onChange={(e) => handleUpdateEntityField(idx, 'reference_range', e.target.value)}
                                    placeholder="e.g. Normal limits or empty"
                                    className="w-full px-2.5 py-1 border border-slate-300 rounded-lg text-xs"
                                  />
                                </div>
                                <div className="flex items-end pb-1">
                                  <label className="flex items-center space-x-1.5 text-xs font-bold text-rose-700 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(ent.is_abnormal)}
                                      onChange={(e) => handleUpdateEntityField(idx, 'is_abnormal', e.target.checked)}
                                      className="rounded text-rose-600 focus:ring-rose-500"
                                    />
                                    <span>Abnormal Finding</span>
                                  </label>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-1">
                              <div>
                                <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Value</label>
                                <input
                                  type="text"
                                  value={value}
                                  onChange={(e) => handleUpdateEntityField(idx, 'entity_value', e.target.value)}
                                  placeholder="e.g. 6.8"
                                  className="w-full px-2.5 py-1 border border-slate-300 rounded-lg text-xs font-mono font-bold"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Unit</label>
                                <input
                                  type="text"
                                  value={ent.unit || ''}
                                  onChange={(e) => handleUpdateEntityField(idx, 'unit', e.target.value)}
                                  placeholder="e.g. mmol/L"
                                  className="w-full px-2.5 py-1 border border-slate-300 rounded-lg text-xs"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Ref Range</label>
                                <input
                                  type="text"
                                  value={ent.reference_range || ''}
                                  onChange={(e) => handleUpdateEntityField(idx, 'reference_range', e.target.value)}
                                  placeholder="e.g. 4.0 - 6.0"
                                  className="w-full px-2.5 py-1 border border-slate-300 rounded-lg text-xs"
                                />
                              </div>
                              <div className="flex items-end pb-1">
                                <label className="flex items-center space-x-1.5 text-xs font-bold text-rose-700 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={Boolean(ent.is_abnormal)}
                                    onChange={(e) => handleUpdateEntityField(idx, 'is_abnormal', e.target.checked)}
                                    className="rounded text-rose-600 focus:ring-rose-500"
                                  />
                                  <span>Abnormal Value</span>
                                </label>
                              </div>
                            </div>
                          )
                        ) : type === 'MEDICATION' ? (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                            <div>
                              <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">
                                Dosage / Pattern
                              </label>
                              <input
                                type="text"
                                value={value}
                                onChange={(e) => handleUpdateEntityField(idx, 'entity_value', e.target.value)}
                                placeholder="e.g. 20mg 1+0+1 (After Food)"
                                className="w-full px-2.5 py-1 border border-slate-300 rounded-lg text-xs font-semibold"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">
                                Notes / Instructions
                              </label>
                              <input
                                type="text"
                                value={ent.raw_snippet || ''}
                                onChange={(e) => handleUpdateEntityField(idx, 'raw_snippet', e.target.value)}
                                placeholder="e.g. 14 days, before breakfast"
                                className="w-full px-2.5 py-1 border border-slate-300 rounded-lg text-xs"
                              />
                            </div>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Raw OCR Text Collapsible Box */}
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50">
              <button
                type="button"
                onClick={() => setShowRawOcr(!showRawOcr)}
                className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-bold text-slate-600 hover:bg-slate-100 transition"
              >
                <span className="flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  <span>View Raw Scanned OCR Transcript</span>
                </span>
                {showRawOcr ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showRawOcr && (
                <div className="p-4 bg-white border-t border-slate-200">
                  <pre className="text-[11px] font-mono text-slate-700 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                    {selectedDoc.raw_ocr_text || selectedDoc.ocr_raw_text || 'No raw OCR transcript text recorded for this document.'}
                  </pre>
                </div>
              )}
            </div>

            {/* Modal Actions Footer */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-400">
                {selectedDoc.is_patient_confirmed || selectedDoc.user_confirmed
                  ? 'All changes verified and synchronized with your health timeline.'
                  : 'Review or edit the AI-extracted details above and click save & confirm.'}
              </span>

              <div className="flex items-center space-x-2 shrink-0">
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      disabled={isSavingReview}
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={isSavingReview}
                      onClick={handleSaveReview}
                      className="flex items-center space-x-1.5 px-5 py-2.5 bg-emerald-600 text-white rounded-xl text-xs font-bold hover:bg-emerald-700 transition shadow-sm"
                    >
                      <Save className="w-4 h-4" />
                      <span>{isSavingReview ? 'Saving Changes...' : 'Save Changes & Confirm'}</span>
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => setIsEditing(true)}
                      className="flex items-center space-x-1.5 px-4 py-2 border border-slate-200 bg-white rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
                    >
                      <Edit3 className="w-3.5 h-3.5 text-slate-500" />
                      <span>Edit Information</span>
                    </button>
                    {!(selectedDoc.is_patient_confirmed || selectedDoc.user_confirmed) && (
                      <button
                        type="button"
                        onClick={() => handleQuickConfirm(selectedDoc.id)}
                        className="flex items-center space-x-1.5 px-5 py-2.5 bg-emerald-600 text-white rounded-xl text-xs font-bold hover:bg-emerald-700 transition shadow-sm"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Confirm Accuracy</span>
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
