import uuid
from django.db import models

class TimeStampedUUIDModel(models.Model):
    """
    Abstract base model providing:
    - Primary key UUID instead of sequential integer (prevents ID enumeration attacks).
    - Indexed created_at timestamp.
    - updated_at timestamp.
    - Soft-deletion flag and helper methods.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])

