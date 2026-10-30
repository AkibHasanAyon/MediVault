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

