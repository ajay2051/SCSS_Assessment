import os
from unittest.mock import patch

import django
import psycopg2
import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import CsvFile, Pdf


@pytest.mark.django_db
class TestPdfTableExtractorView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('pdf-table-extractor')
        self.test_pdf_path = os.path.join(os.path.dirname(__file__), 'test_data', 'sample.pdf')

    def test_no_file_provided(self):
        """
        Test API response when no file is uploaded
        """
        response = self.client.post(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'No file provided'

    @patch('your_app.views.validate_file')
    def test_invalid_file(self, mock_validate_file):
        """
        Test API response for invalid file upload
        """
        mock_validate_file.return_value = False
        with open(self.test_pdf_path, 'rb') as file:
            uploaded_file = SimpleUploadedFile('sample.pdf', file.read(), content_type='application/pdf')

        response = self.client.post(self.url, {'file': uploaded_file}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'Invalid file'

    @patch('your_app.views.save_temp_pdf')
    @patch('your_app.views.extract_tables')
    @patch('your_app.views.save_table_as_csv')
    def test_successful_pdf_table_extraction(self, mock_save_table_as_csv, mock_extract_tables, mock_save_temp_pdf):
        """
        Test successful PDF table extraction
        """
        # Mock dependencies
        mock_save_temp_pdf.return_value = '/tmp/sample.pdf'
        mock_extract_tables.return_value = [['Table', 'Data'], ['Row1', 'Value']]
        mock_save_table_as_csv.return_value = 'sample_tables.csv'

        with open(self.test_pdf_path, 'rb') as file:
            uploaded_file = SimpleUploadedFile('sample.pdf', file.read(), content_type='application/pdf')

        response = self.client.post(self.url, {'file': uploaded_file}, format='multipart')
        assert response.status_code == status.HTTP_200_OK
        assert 'Successfully Extracted Tables' in response.data['message']
        assert 'hash' in response.data['data']
        assert 'pdf_url' in response.data['data']
        assert 'csv_url' in response.data['data']

    def test_duplicate_file_upload(self):
        """
        Test uploading a file with an existing hash
        """
        # Create an existing PDF instance
        existing_pdf = Pdf.objects.create(
            file=SimpleUploadedFile('existing.pdf', b'content'),
            hash='existing_hash'
        )

        with patch('your_app.views.generate_file_hash', return_value='existing_hash'):
            with open(self.test_pdf_path, 'rb') as file:
                uploaded_file = SimpleUploadedFile('sample.pdf', file.read(), content_type='application/pdf')

            response = self.client.post(self.url, {'file': uploaded_file}, format='multipart')
            assert response.status_code == status.HTTP_200_OK
            assert response.data['message'] == 'File Already Exists'


@pytest.mark.django_db
class TestPdfProcessingStatusView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.test_hash = 'test_hash_123'

    def test_completed_processing(self):
        """
        Test status for a PDF with completed processing
        """
        pdf = Pdf.objects.create(
            file=SimpleUploadedFile('sample.pdf', b'content'),
            hash=self.test_hash
        )
        csv_file = CsvFile.objects.create(
            pdf=pdf,
            file=SimpleUploadedFile('tables.csv', b'csv content')
        )

        url = reverse('pdf-processing-status', kwargs={'hash': self.test_hash})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'complete'
        assert 'pdf_url' in response.data
        assert 'csv_url' in response.data

    def test_in_progress_processing(self):
        """
        Test status for a PDF still being processed
        """
        Pdf.objects.create(
            file=SimpleUploadedFile('sample.pdf', b'content'),
            hash=self.test_hash
        )

        url = reverse('pdf-processing-status', kwargs={'hash': self.test_hash})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'in-progress'

    def test_failed_processing(self):
        """
        Test status for a PDF with failed processing
        """
        pdf = Pdf.objects.create(
            file=SimpleUploadedFile('sample.pdf', b'content'),
            hash=self.test_hash
        )

        # Simulate error file creation
        os.makedirs('media/errors', exist_ok=True)
        with open(f'media/errors/{self.test_hash}.txt', 'w') as f:
            f.write('Processing error details')

        url = reverse('pdf-processing-status', kwargs={'hash': self.test_hash})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'failed'
        assert 'error_file_url' in response.data


@pytest.mark.django_db
class TestPdfListView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('pdf-list')

    def test_list_pdfs(self):
        """
        Test listing PDFs with their corresponding CSVs
        """
        # Create test PDFs with CSVs
        pdf1 = Pdf.objects.create(
            file=SimpleUploadedFile('sample1.pdf', b'content1'),
            hash='hash1'
        )
        csv1 = CsvFile.objects.create(
            pdf=pdf1,
            file=SimpleUploadedFile('tables1.csv', b'csv content1')
        )

        pdf2 = Pdf.objects.create(
            file=SimpleUploadedFile('sample2.pdf', b'content2'),
            hash='hash2'
        )
        # Note: No CSV for pdf2 to test scenario with missing CSV

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['pdfs']) == 2

        # Verify first PDF details
        pdf_data = response.data['pdfs'][0]
        assert pdf_data['hash'] == 'hash1'
        assert 'uploaded_at' in pdf_data
        assert 'pdf_url' in pdf_data
        assert 'csv_url' in pdf_data

        # Verify second PDF details
        pdf_data = response.data['pdfs'][1]
        assert pdf_data['hash'] == 'hash2'
        assert pdf_data['csv_url'] is None


def create_test_database():
    """
    Dynamically create a test database for PostgreSQL
    """
    # Default connection parameters
    db_params = {
        'dbname': 'postgres',
        'user': os.environ.get('TEST_DB_USER', 'postgres'),
        'password': os.environ.get('TEST_DB_PASSWORD', ''),
        'host': os.environ.get('TEST_DB_HOST', 'localhost'),
        'port': os.environ.get('TEST_DB_PORT', '5432')
    }

    # Test database name
    test_db_name = os.environ.get('TEST_DB_NAME', 'test_pdf_extractor')

    # Connect to default database to create test database
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        # Drop existing test database if it exists
        cur.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')

        # Create new test database
        cur.execute(f'CREATE DATABASE "{test_db_name}"')
    except Exception as e:
        print(f"Error creating test database: {e}")
    finally:
        cur.close()
        conn.close()


def pytest_configure():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Create test database
    create_test_database()

    # Ensure the test database is used
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')

    # Configure Django settings manually
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            USE_TZ=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': os.environ.get('TEST_DB_NAME', 'test_pdf_extractor'),
                    'USER': os.environ.get('TEST_DB_USER', 'postgres'),
                    'PASSWORD': os.environ.get('TEST_DB_PASSWORD', ''),
                    'HOST': os.environ.get('TEST_DB_HOST', 'localhost'),
                    'PORT': os.environ.get('TEST_DB_PORT', '5432'),
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'rest_framework',
                'extract',  # replace with your actual app name
            ],
            REST_FRAMEWORK={
                'DEFAULT_PERMISSION_CLASSES': [
                    'rest_framework.permissions.AllowAny',
                ],
            },
            MEDIA_ROOT=os.path.join(base_dir, 'media'),
            SECRET_KEY='test_secret_key',
        )


# Fixture to ensure Django is set up for each test
@pytest.fixture(scope='session')
def django_setup():
    django.setup()
