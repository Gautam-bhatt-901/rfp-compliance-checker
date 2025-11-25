"""
Utility functions for the RFP Compliance Checker
"""

import os
from typing import List
from app import config

def save_uploaded_file(uploaded_file, directory: str) -> str:
    """
    Save uploaded file to specified directory
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        directory: Target directory path
        
    Returns:
        Full path to saved file
    """
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, uploaded_file.filename)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.file.read())
    
    return file_path

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate file has allowed extension
    
    Args:
        filename: Name of file to validate
        allowed_extensions: List of allowed extensions (without dots)
        
    Returns:
        True if valid, False otherwise
    """
    extension = filename.rsplit('.', 1)[-1].lower()
    return extension in allowed_extensions

def clear_directory(directory: str):
    """
    Clear all files from a directory
    
    Args:
        directory: Directory path to clear
    """
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

def format_results_for_display(results: List[dict]) -> List[dict]:
    """
    Format matching results for better display
    
    Args:
        results: List of matching result dictionaries
        
    Returns:
        Formatted results
    """
    # Sort by status (Present first, then Review, then Missing)
    criticality_order = {'Mandatory': 1, 'Important': 2, 'Optional': 3}
    status_order = {
        config.STATUS_PRESENT: 1,
        config.STATUS_REVIEW: 2,
        config.STATUS_MISSING: 3
    }
    
    return sorted(results, key=lambda x: (
        criticality_order.get(x.get('Criticality', 'Optional'), 3),
        status_order.get(x['Status'], 3)
    ))

def get_summary_stats(results: List[dict]) -> dict:
    """
    Calculate summary statistics from results
    
    Args:
        results: List of matching result dictionaries
        
    Returns:
        Dictionary with summary statistics
    """
    total = len(results)
    present = sum(1 for r in results if r['Status'] == config.STATUS_PRESENT)
    review = sum(1 for r in results if r['Status'] == config.STATUS_REVIEW)
    missing = sum(1 for r in results if r['Status'] == config.STATUS_MISSING)
    
    return {
        'total': total,
        'present': present,
        'review': review,
        'missing': missing,
        'completion_rate': (present / total * 100) if total > 0 else 0
    }
