import hashlib

from django.db import models


class PDFDocument(models.Model):
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    csv_output = models.FileField(upload_to='csv_outputs/', null=True, blank=True)
    file_hash = models.CharField(max_length=64, null=True, blank=True)  # SHA-256 hash

    def __str__(self):
        return f"PDF Document {self.file_hash}"

    def calculate_file_hash(self):
        """
        Calculate SHA-256 hash of the PDF file

        Returns:
            str: Hexadecimal hash of the file
        """
        hash_sha256 = hashlib.sha256()
        with self.file.open('rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
