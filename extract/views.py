import os
import traceback

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CsvFile, Pdf
from .utils import extract_tables, generate_file_hash, save_error_details, save_table_as_csv, save_temp_pdf, validate_file


class PdfTableExtractorView(APIView):
    def post(self, request, *args, **kwargs):
        global pdf_path, file_hash
        try:
            file = request.FILES.get('file')
            if not file:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Validate file type and size
            if not validate_file(file):
                return Response({'error': 'Invalid file'}, status=status.HTTP_400_BAD_REQUEST)

            file_hash = generate_file_hash(file)
            pdf_path = None
            # Check for existing file
            if Pdf.objects.filter(hash=file_hash).exists():
                return Response({"message": "File Already Exists"})

            pdf_path = None
            try:
                pdf_path = save_temp_pdf(file)

                pdf_instance = Pdf.objects.create(file=file, hash=file_hash)

                tables = extract_tables(pdf_path)

                if not tables:
                    return Response({'error': 'No tables found in PDF'}, status=status.HTTP_400_BAD_REQUEST)

                csv_file = save_table_as_csv(tables, file_hash)

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
            error_details = traceback.format_exc()
            error_file_path = save_error_details(file_hash, error_details)
            return Response({
                'error': f'Processing error: {str(e)}',
                'error_file_url': request.build_absolute_uri(f'/media/{error_file_path}')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            # Cleanup temporary PDF if it exists
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)


class PdfProcessingStatusView(APIView):
    """
    GET endpoint to check the status of a PDF processing task.
    """

    def get(self, request, hash, *args, **kwargs):
        try:
            pdf_instance = get_object_or_404(Pdf, hash=hash)

            # Check if a CSV file exists for the PDF
            csv_instance = CsvFile.objects.filter(pdf=pdf_instance).first()
            if csv_instance:
                return Response({
                    'status': 'complete',
                    'pdf_url': request.build_absolute_uri(f'/media/{pdf_instance.file.name}'),
                    'csv_url': request.build_absolute_uri(f'/media/{csv_instance.file.name}')
                }, status=status.HTTP_200_OK)

            # Check for error details
            error_file_path = f'errors/{hash}.txt'  # Assuming errors are stored in a dedicated folder
            error_file_full_path = os.path.join('media', error_file_path)
            if os.path.exists(error_file_full_path):
                return Response({
                    'status': 'failed',
                    'error_file_url': request.build_absolute_uri(f'/media/{error_file_path}')
                }, status=status.HTTP_200_OK)

            return Response({'status': 'in-progress'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PdfListView(APIView):
    """
    GET endpoint to list all PDFs and their corresponding CSVs.
    """

    def get(self, request, *args, **kwargs):
        try:
            pdfs = Pdf.objects.all()
            pdf_list = []

            for pdf in pdfs:
                csv_instance = CsvFile.objects.filter(pdf=pdf).first()
                pdf_list.append({
                    'hash': pdf.hash,
                    'uploaded_at': pdf.uploaded_at,
                    'pdf_url': request.build_absolute_uri(f'/media/{pdf.file.name}'),
                    'csv_url': request.build_absolute_uri(f'/media/{csv_instance.file.name}') if csv_instance else None
                })

            return Response({'pdfs': pdf_list}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
