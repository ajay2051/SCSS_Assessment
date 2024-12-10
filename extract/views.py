import os
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PDFDocument
from .serializers import PDFDocumentSerializer
from .utils import extract_tables_from_pdf, save_tables_to_csv


class PDFUploadView(APIView):
    """
    API View for uploading PDF files, extracting tables, and generating CSV
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        """
        Handle PDF file upload and processing
        """
        # Validate file presence
        pdf_file = request.data.get('file')
        if not pdf_file:
            return Response(
                {'error': 'No PDF file uploaded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create a unique filename
            original_filename = pdf_file.name
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # Prepare file paths
            pdf_save_path = os.path.join(settings.MEDIA_ROOT, 'pdfs', unique_filename)
            csv_filename = f"{os.path.splitext(unique_filename)[0]}_tables.csv"
            csv_save_path = os.path.join(settings.MEDIA_ROOT, 'csv_outputs', csv_filename)

            # Ensure directories exist
            os.makedirs(os.path.dirname(pdf_save_path), exist_ok=True)
            os.makedirs(os.path.dirname(csv_save_path), exist_ok=True)

            # Save PDF file
            with open(pdf_save_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)

            # Create PDFDocument instance
            pdf_document = PDFDocument()
            pdf_document.file.name = os.path.join('pdfs', unique_filename)

            # Calculate file hash
            pdf_document.file_hash = pdf_document.calculate_file_hash()

            # Extract tables
            tables = extract_tables_from_pdf(pdf_save_path)

            if not tables:
                # Remove the uploaded file if no tables found
                os.remove(pdf_save_path)
                return Response(
                    {'error': 'No tables found in PDF'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save tables to CSV
            if save_tables_to_csv(tables, csv_save_path):
                # Update PDFDocument with CSV path
                pdf_document.csv_output.name = os.path.join('csv_outputs', csv_filename)
                pdf_document.save()

                # Serialize and return response
                serializer = PDFDocumentSerializer(pdf_document)
                return Response({"message": "PDF Table Extracted Success...", "data": serializer.data}, status=status.HTTP_201_CREATED)
            else:
                # Remove files if CSV saving fails
                os.remove(pdf_save_path)
                return Response(
                    {'error': 'Failed to save tables to CSV'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            # Log the error and return a generic error response
            print(f"PDF Processing Error: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred during PDF processing'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PDFListView(APIView):
    """
    API View for listing PDF documents with optional filtering
    """

    def get(self, request, format=None):
        """
        List PDF documents with optional hash filtering
        """
        # Get query parameters
        file_hash = request.query_params.get('hash')

        # Base queryset
        queryset = PDFDocument.objects.all()

        # Optional hash filtering
        if file_hash:
            queryset = queryset.filter(file_hash=file_hash)

        # Serialize and return
        serializer = PDFDocumentSerializer(queryset, many=True)
        return Response(serializer.data)


class PDFDetailView(APIView):
    """
    API View for retrieving details of a specific PDF document
    """

    def get(self, request, pk, format=None):
        """
        Retrieve details of a specific PDF document
        """
        try:
            pdf_document = PDFDocument.objects.get(pk=pk)
            serializer = PDFDocumentSerializer(pdf_document)
            return Response(serializer.data)
        except PDFDocument.DoesNotExist:
            return Response(
                {'error': 'PDF document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, pk, format=None):
        """
        Delete a specific PDF document
        """
        try:
            pdf_document = PDFDocument.objects.get(pk=pk)

            # Remove associated files
            if pdf_document.file:
                try:
                    os.remove(pdf_document.file.path)
                except FileNotFoundError:
                    pass

            if pdf_document.csv_output:
                try:
                    os.remove(pdf_document.csv_output.path)
                except FileNotFoundError:
                    pass

            # Delete database record
            pdf_document.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except PDFDocument.DoesNotExist:
            return Response(
                {'error': 'PDF document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
