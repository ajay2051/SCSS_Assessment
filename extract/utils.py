import pandas as pd
import tabula


def extract_tables_from_pdf(pdf_path):
    """
    Extract tables from a PDF file using Tabula

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        list: List of pandas DataFrames containing extracted tables
    """
    try:
        # Extract tables from PDF
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        return tables
    except Exception as e:
        print(f"Error extracting tables: {e}")
        return []


def save_tables_to_csv(tables, output_path):
    """
    Save extracted tables to a CSV file

    Args:
        tables (list): List of pandas DataFrames
        output_path (str): Path to save the CSV file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Combine multiple tables if there are more than one
        if len(tables) > 1:
            combined_df = pd.concat(tables, ignore_index=True)
        elif len(tables) == 1:
            combined_df = tables[0]
        else:
            return False

        # Save to CSV
        combined_df.to_csv(output_path, index=False)
        return True
    except Exception as e:
        print(f"Error saving tables to CSV: {e}")
        return False
