from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_MAGIC_SIGNATURES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'RIFF': 'image/webp',
    b'%PDF-': 'application/pdf',
}

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'pdf', 'heic', 'heif'}
HEIC_BRANDS = [b'heic', b'heix', b'hevc', b'heim', b'heis', b'mif1', b'msf1', b'miaf']

def validate_medical_document_file(uploaded_file):
    """
    Validates file size and inspects binary magic headers to prevent
    mime-type spoofing and malicious binary uploads.
    Supports JPEG, PNG, WebP, PDF, and HEIC/HEIF images.
    """
    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            _(f"File size exceeds maximum allowable limit of 10 MB. Your file is {uploaded_file.size / (1024 * 1024):.1f} MB.")
        )

    # Check file extension
    ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            _(f"Unsupported file extension '.{ext}'. Supported formats are: JPEG, PNG, WebP, PDF, HEIC.")
        )

    # Read the first 32 bytes for magic signature inspection
    initial_bytes = uploaded_file.read(32)
    uploaded_file.seek(0)  # Rewind file pointer for downstream storage

    is_valid_magic = False
    for signature in ALLOWED_MAGIC_SIGNATURES:
        if initial_bytes.startswith(signature):
            is_valid_magic = True
            break

    # Check for HEIC/HEIF (ISOBMFF structure: bytes 4-8 'ftyp' with compatible brand in bytes 8-32)
    if not is_valid_magic and len(initial_bytes) >= 12 and initial_bytes[4:8] == b'ftyp':
        brand_chunk = initial_bytes[8:32]
        if any(brand in brand_chunk for brand in HEIC_BRANDS):
            is_valid_magic = True

    if not is_valid_magic:
        raise ValidationError(
            _("Invalid or corrupted file content. File header does not match expected JPEG, PNG, WebP, PDF, or HEIC format.")
        )

