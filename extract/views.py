import hashlib
import os

import pandas as pd
import pdfplumber
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import CsvFile, Pdf


class PdfTableExtractorView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            file = request.FILES.get('file')
            if not file:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Validate file type and size
            if not self.validate_file(file):
                return Response({'error': 'Invalid file'}, status=status.HTTP_400_BAD_REQUEST)

            file_hash = self.generate_file_hash(file)

            # Check for existing file
            if Pdf.objects.filter(hash=file_hash).exists():
                return Response({"message": "File Already Exists"})

            pdf_path = None
            try:
                pdf_path = self.save_temp_pdf(file)

                pdf_instance = Pdf.objects.create(file=file, hash=file_hash)

                tables = self.extract_tables(pdf_path)

                if not tables:
                    return Response({'error': 'No tables found in PDF'}, status=status.HTTP_400_BAD_REQUEST)

                csv_file = self.save_table_as_csv(tables, file_hash)

                csv_instance = CsvFile.objects.create(
                    pdf=pdf_instance,
                    file=csv_file
                )

                response_data = {
                    'hash': pdf_instance.hash,
                    'pdf_url': request.build_absolute_uri(f'/media/{pdf_instance.file.name}'),
                    'csv_url': request.build_absolute_uri(f'/media/{csv_instance.file.name}'),
                }
                return Response({"message": "Successfully Extracted Tables", "data": response_data}, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({'error': f'Processing error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'error': f'Processing error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def validate_file(self, file):
        """Additional file validation"""
        # Check file size (e.g., max 10MB)
        if file.size > 10 * 1024 * 1024:
            return False

        # Check file extension
        allowed_extensions = ['pdf']
        file_extension = file.name.split('.')[-1].lower()
        return file_extension in allowed_extensions


    def generate_file_hash(self, file):
        """Generates a hash for the PDF file."""
        file.seek(0) # Make sure the file pointer is at the start
        file_hash = hashlib.sha256()
        for chunk in file.chunks():
            file_hash.update(chunk)
        return file_hash.hexdigest()

    def save_temp_pdf(self, file):
        """Saves the PDF file temporarily."""
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, 'wb') as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)
        return temp_path

    def extract_tables(self, pdf_path):
        """Extracts tables from the PDF using pdfplumber."""
        tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    # Clean and standardize the table data
                    cleaned_table = self.clean_table_data(table)
                    tables.append(pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0]))
        return tables

    def clean_table_data(self, table):
        """
        Clean and standardize the table data
        - Remove empty rows and columns
        - Ensure proper header alignment
        - Remove unnecessary whitespace
        """
        # Remove completely empty rows
        cleaned_table = [row for row in table if any(cell and str(cell).strip() for cell in row)]

        # Find the first row with meaningful headers
        header_row = next((row for row in cleaned_table if any(cell and str(cell).strip() for cell in row)), None)

        if header_row is None:
            return table

        # Get the index of the header row
        header_index = cleaned_table.index(header_row)

        # Extract headers, removing None or empty values
        headers = [str(cell).strip() if cell else f'Column_{i}' for i, cell in enumerate(header_row)]

        # Get data rows, skipping header and empty rows
        data_rows = cleaned_table[header_index + 1:]

        # Clean and align data rows
        cleaned_data_rows = []
        for row in data_rows:
            # Ensure row has same length as headers, filling with empty string if needed
            cleaned_row = [str(cell).strip() if cell is not None else '' for cell in row[:len(headers)]]
            while len(cleaned_row) < len(headers):
                cleaned_row.append('')
            cleaned_data_rows.append(cleaned_row)

        # Combine headers and data
        return [headers] + cleaned_data_rows

    def save_table_as_csv(self, tables, file_hash):
        """Saves the extracted tables as CSV files."""
        table = tables[0]  # Save only the first table

        # Clean column names
        table.columns = [col.strip() for col in table.columns]

        # Remove any completely empty columns
        table = table.dropna(axis=1, how='all')

        # Remove any completely empty rows
        table = table.dropna(how='all')

        # Reset index to ensure clean output
        table = table.reset_index(drop=True)
        # Generate CSV content
        csv_content = table.to_csv(index=False)

        # Save file using Django's storage
        csv_path = f'csv/{file_hash}.csv'
        default_storage.save(csv_path, ContentFile(csv_content.encode('utf-8')))

        return csv_path
