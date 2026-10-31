import io
import os
import logging
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger('medivault.documents')

def convert_heic_to_jpeg_if_needed(uploaded_file):
    """
    If the uploaded file is a HEIC/HEIF image, converts it to a standard high-quality JPEG
    so it can be rendered natively in web browsers and processed by Google Cloud Vision.
    """
    file_name = getattr(uploaded_file, 'name', '') or ''
    ext = os.path.splitext(file_name)[1].lower()

    # Read initial bytes to check if it's HEIC even without proper extension
    uploaded_file.seek(0)
    initial_bytes = uploaded_file.read(32)
    uploaded_file.seek(0)

    is_heic = ext in ['.heic', '.heif'] or (len(initial_bytes) >= 12 and initial_bytes[4:8] == b'ftyp')

    if not is_heic:
        return uploaded_file

    try:
        import pillow_heif
        from PIL import Image

        pillow_heif.register_heif_opener()
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)

        # Convert RGBA/Palette modes to RGB for JPEG
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        output_buffer = io.BytesIO()
        image.save(output_buffer, format='JPEG', quality=95, optimize=True)
        output_buffer.seek(0)

        base_name = os.path.splitext(file_name)[0] or 'document'
        new_filename = f"{base_name}.jpg"

        new_file = InMemoryUploadedFile(
            file=output_buffer,
            field_name=getattr(uploaded_file, 'field_name', 'file'),
            name=new_filename,
            content_type='image/jpeg',
            size=output_buffer.getbuffer().nbytes,
            charset=None
        )
        logger.info("Successfully converted HEIC image %s to JPEG %s (%d bytes)", file_name, new_filename, new_file.size)
        return new_file

    except Exception as exc:
        logger.error("Failed to convert HEIC image %s: %s", file_name, str(exc))
        uploaded_file.seek(0)
        return uploaded_file


def merge_files_to_pdf(uploaded_files, base_name="merged_medical_document"):
    """
    Merges multiple files (JPEG, PNG, WebP, HEIC, PDF) into a single multi-page PDF.
    Enables multi-page mobile photos of a single prescription or lab report to be
    processed together by OCR and viewed natively in any browser.
    """
    import pillow_heif
    from PIL import Image
    from pypdf import PdfWriter, PdfReader

    pillow_heif.register_heif_opener()
    writer = PdfWriter()

    for f in uploaded_files:
        f_name = getattr(f, 'name', '') or ''
        ext = os.path.splitext(f_name)[1].lower()
        f.seek(0)
        initial_bytes = f.read(16)
        f.seek(0)

        if ext == '.pdf' or initial_bytes.startswith(b'%PDF-'):
            reader = PdfReader(f)
            for page in reader.pages:
                writer.add_page(page)
        else:
            # It's an image (JPEG, PNG, WebP, HEIC)
            f_conv = convert_heic_to_jpeg_if_needed(f)
            f_conv.seek(0)
            img = Image.open(f_conv)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img_buf = io.BytesIO()
            img.save(img_buf, format='PDF')
            img_buf.seek(0)
            img_reader = PdfReader(img_buf)
            for page in img_reader.pages:
                writer.add_page(page)

    output_buf = io.BytesIO()
    writer.write(output_buf)
    output_buf.seek(0)

    clean_name = os.path.splitext(base_name)[0] or 'document'
    merged_filename = f"{clean_name}.pdf"

    merged_file = InMemoryUploadedFile(
        file=output_buf,
        field_name='file',
        name=merged_filename,
        content_type='application/pdf',
        size=output_buf.getbuffer().nbytes,
        charset=None
    )
    logger.info("Successfully merged %d files into PDF %s (%d bytes)", len(uploaded_files), merged_filename, merged_file.size)
    return merged_file

