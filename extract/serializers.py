from rest_framework import serializers

from .models import PDFDocument


class PDFDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFDocument
        fields = ['id', 'file', 'uploaded_at', 'csv_output', 'file_hash']
        read_only_fields = ['id', 'uploaded_at', 'csv_output', 'file_hash']
