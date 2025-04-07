import re
import os
from typing import List, Dict, Any, Optional, Tuple
import tempfile

def preprocess_data_file(input_filepath: str) -> str:
    """
    Preprocess a data file to normalize formats and fix common issues.
    
    Args:
        input_filepath: Path to the original data file
        
    Returns:
        Path to the preprocessed data file
    """
    # Create a temporary file for the preprocessed data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        output_filepath = temp_file.name
        
        # Process the input file line by line
        with open(input_filepath, 'r', encoding='utf-8', errors='replace') as input_file:
            for line in input_file:
                # Process the line
                processed_line = process_line(line)
                temp_file.write(processed_line)
    
    print(f"Preprocessed data saved to: {output_filepath}")
    return output_filepath


def process_line(line: str) -> str:
    """Process a single line of text, applying all necessary transformations."""
    # Remove BOM and other invisible characters
    line = line.strip('\ufeff\r\n')
    
    # Normalize number formats (e.g., remove commas in numbers)
    line = normalize_numbers(line)
    
    # Normalize date formats
    line = normalize_dates(line)
    
    # Handle special characters
    line = handle_special_chars(line)
    
    # Ensure line ends with newline
    if not line.endswith('\n'):
        line += '\n'
    
    return line


def normalize_numbers(text: str) -> str:
    """
    Normalize number formats by removing thousands separators and standardizing decimals.
    
    Examples:
    - "1,234.56" -> "1234.56"
    - "1.234,56" (European format) -> "1234.56"
    """
    # Pattern for numbers with commas as thousand separators (e.g. 1,234.56)
    us_pattern = r'(\d{1,3}(?:,\d{3})+(?:\.\d+)?)'
    
    # Function to replace commas in matched numbers
    def replace_us_commas(match):
        return match.group(0).replace(',', '')
    
    # Replace US-style numbers (commas as thousand separators)
    result = re.sub(us_pattern, replace_us_commas, text)
    
    # Handle European-style numbers (dots as thousand separators, commas as decimal)
    # This is more complex and would need specific patterns for your data
    
    return result


def normalize_dates(text: str) -> str:
    """
    Normalize date formats to a standard format.
    Example: Various date formats -> YYYY-MM-DD
    """
    # For this implementation, we'll just look for common date formats
    # In a real implementation, you'd want more sophisticated date parsing
    
    # Match dates like MM/DD/YYYY or DD/MM/YYYY
    date_pattern = r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
    
    # For simplicity, we'll just keep the dates as they are
    # In a real implementation, you'd convert to a standard format
    
    return text


def handle_special_chars(text: str) -> str:
    """
    Handle special characters that might cause issues.
    """
    # Replace problematic characters with safe alternatives
    # This is application-specific, so we'll just handle some basic cases
    
    # Replace null bytes
    text = text.replace('\x00', '')
    
    # Replace other problematic characters as needed
    
    return text


def get_data_stats(filepath: str) -> Dict[str, Any]:
    """
    Get basic statistics about the data file to help with preprocessing decisions.
    """
    stats = {
        'line_count': 0,
        'has_headers': False,
        'potential_delimiters': [],
        'sample_lines': []
    }
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        # Read the first 100 lines for analysis
        lines = [next(f, None) for _ in range(100) if f]
        valid_lines = [line for line in lines if line]
        
        stats['line_count'] = len(valid_lines)
        
        if stats['line_count'] > 0:
            # Get sample lines
            stats['sample_lines'] = valid_lines[:5]
            
            # Try to detect delimiters
            for delimiter in [',', '\t', '|', ';']:
                if any(delimiter in line for line in valid_lines):
                    stats['potential_delimiters'].append(delimiter)
            
            # Try to detect if first line is a header
            if stats['line_count'] > 1:
                first_line = valid_lines[0]
                second_line = valid_lines[1]
                
                # If first line contains more text and fewer numbers than second line,
                # it might be a header
                first_line_nums = sum(1 for c in first_line if c.isdigit())
                second_line_nums = sum(1 for c in second_line if c.isdigit())
                
                if first_line_nums < second_line_nums:
                    stats['has_headers'] = True
    
    return stats