import logging

import pandas as pd
import tabula

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_tables_from_pdf(pdf_path, pages='all', multiple_tables=True, guess=True):
    """
    Enhanced PDF table extraction with multiple strategies

    Args:
        pdf_path (str): Path to the PDF file
        pages (str/list): Pages to extract tables from. 'all' or list of page numbers
        multiple_tables (bool): Allow multiple tables
        guess (bool): Use Tabula's guessing algorithm

    Returns:
        list: List of pandas DataFrames containing extracted tables
    """
    try:
        # Strategy 1: Default extraction with guessing
        tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=multiple_tables, guess=guess)

        if tables and len(tables) > 0:
            logger.info(f"Found {len(tables)} tables using default extraction")
            return tables

        # Strategy 2: No guessing, default settings
        tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=multiple_tables, guess=False)

        if tables and len(tables) > 0:
            logger.info(f"Found {len(tables)} tables without guessing")
            return tables

        # Strategy 3: Extraction with alternative parameters
        alternative_strategies = [
            {'stream': True},  # Streaming mode
            {'lattice': True},  # Grid-based detection
            {'stream': True, 'guess': False},
            {'lattice': True, 'guess': False}
        ]

        for strategy in alternative_strategies:
            tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=multiple_tables, **strategy)

            if tables and len(tables) > 0:
                logger.info(f"Found {len(tables)} tables using strategy: {strategy}")
                return tables

        # Manual parsing if automated methods fail
        tables = manual_table_extraction(pdf_path)

        if tables and len(tables) > 0:
            logger.info(f"Found {len(tables)} tables using manual extraction")
            return tables

        logger.warning("No tables found in PDF using any extraction method")
        return []

    except Exception as e:
        logger.error(f"Error in table extraction: {e}")
        return []


def manual_table_extraction(pdf_path):
    """
    Manual table extraction for complex PDFs

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        list: List of manually parsed tables
    """
    try:
        import camelot

        # Use camelot for alternative table extraction
        tables = camelot.read_pdf(pdf_path, pages='all')

        if tables:
            # Convert camelot tables to pandas DataFrames
            pandas_tables = [table.df for table in tables]
            return pandas_tables

        return []

    except ImportError:
        logger.warning("Camelot library not installed. Skipping manual extraction.")
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
        # Clean and process tables
        cleaned_tables = []
        for df in tables:
            # Remove empty rows and columns
            df = df.dropna(how='all')
            df = df.dropna(axis=1, how='all')

            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]

            cleaned_tables.append(df)

        # Combine or save tables
        if len(cleaned_tables) > 1:
            combined_df = pd.concat(cleaned_tables, ignore_index=True)
        elif len(cleaned_tables) == 1:
            combined_df = cleaned_tables[0]
        else:
            return False

        # Save to CSV
        combined_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(cleaned_tables)} tables to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving tables to CSV: {e}")
        return False
