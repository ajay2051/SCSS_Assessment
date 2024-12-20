import hashlib
import os
import traceback

import pandas as pd
import pdfplumber
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def validate_file(file):
    """Additional file validation"""
    # Check file size (e.g., max 10MB)
    if file.size > 10 * 1024 * 1024:
        return False

    # Check file extension
    allowed_extensions = ['pdf']
    file_extension = file.name.split('.')[-1].lower()
    return file_extension in allowed_extensions


def generate_file_hash(file):
    """Generates a hash for the PDF file."""
    file.seek(0)  # Make sure the file pointer is at the start
    file_hash = hashlib.sha256()
    for chunk in file.chunks():
        file_hash.update(chunk)
    return file_hash.hexdigest()


def save_temp_pdf(file):
    """Saves the PDF file temporarily."""
    temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', file.name)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, 'wb') as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
    return temp_path


def extract_tables(pdf_path):
    """Extracts tables from the PDF using pdfplumber."""
    tables = []
    error_details = None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    # Clean and standardize the table data
                    cleaned_table = clean_table_data(table)
                    tables.append(pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0]))

    except Exception as e:
        # Capture detailed error information
        error_details = traceback.format_exc()

    return tables, error_details


def save_error_details(file_hash, error_details):
    """
    Save error details to a text file

    Args:
    - file_hash: Unique identifier for the file
    - error_details: Error traceback or details

    Returns:
    - Path to the saved error file
    """
    # Generate error file path
    error_file_path = f'errors/{file_hash}_error.txt'

    # Save error details using Django's default storage
    default_storage.save(
        error_file_path,
        ContentFile(str(error_details).encode('utf-8'))
    )

    return error_file_path


def clean_table_data(table):
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


def save_table_as_csv(tables, file_hash):
    """Saves the extracted tables as CSV files."""
    global table
    if not tables or not isinstance(tables[0], (pd.DataFrame, list, dict)):
        raise ValueError("The first element of 'tables' must be tabular data.")

    # Preprocess tables[0] into a DataFrame
    if isinstance(tables[0], pd.DataFrame):
        table = tables[0]
    elif isinstance(tables[0], list):
        try:
            table = pd.DataFrame(tables[0])
        except ValueError as e:
            print(f"Error converting to DataFrame: {e}")
            # Attempt to normalize irregular data
            normalized_data = [row if isinstance(row, list) else [row] for row in tables[0]]
            table = pd.DataFrame(normalized_data)
    elif isinstance(tables[0], dict):
        table = pd.DataFrame([tables[0]])

    # Use a relative path within MEDIA_ROOT
    relative_path = os.path.join('csv', f'{file_hash}.csv')
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Save the CSV
    table.to_csv(full_path, index=False)

    return relative_path
