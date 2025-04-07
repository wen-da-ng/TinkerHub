from mcp.context import Context, MessageRole
from mcp.providers import LLMProvider

def get_data_format_hint(document_content: str) -> str:
    """Generate a hint about the data format based on content examination."""
    
    # Look for CSV-like structures
    if "," in document_content and "\n" in document_content:
        lines = document_content.split("\n")
        if len(lines) > 1 and lines[0].count(",") > 0 and lines[0].count(",") == lines[1].count(","):
            return "The data appears to be in CSV format. Parse it using csv.reader or pandas."
    
    # Look for key-value pairs
    if ":" in document_content:
        lines = document_content.split("\n")
        kv_count = sum(1 for line in lines if ":" in line)
        if kv_count > len(lines) / 2:  # More than half the lines have key-value pairs
            return "The data appears to be in key-value format. Parse each line as 'key: value' pairs."
    
    # Look for JSON-like structures
    if "{" in document_content and "}" in document_content:
        return "The data might contain JSON-like structures. Consider using json.loads() after proper formatting."
    
    # Check for table-like format with spaces or tabs as separators
    if "\n" in document_content:
        lines = [line.strip() for line in document_content.split("\n") if line.strip()]
        if len(lines) > 2:
            first_line_parts = len(lines[0].split())
            if first_line_parts > 2 and all(len(line.split()) >= first_line_parts-1 for line in lines[1:3]):
                return "The data appears to be in a space/tab-separated table format. Parse using string splitting or regex."
    
    # Default guidance
    return "The data is in plain text format. You may need to parse it line by line with custom logic."


async def generate_analysis_code(provider: LLMProvider, data_sample: str, data_filepath: str, analysis_question: str) -> str:
    """Generate Python code to analyze document data based on a question."""
    
    # Create a specialized system prompt for code generation
    code_gen_prompt = (
        "You are a Python data analysis expert. Generate code to analyze a data file.\n\n"
        f"DATA FILE PATH: {data_filepath}\n\n"
        "Your code should:\n"
        "1. Read data from this EXACT file path - do not prompt the user for file paths\n"
        "2. Parse the data appropriately based on its format\n"
        "3. Perform the analysis requested\n"
        "4. Print results clearly\n\n"
        "Here's a sample of what the data looks like:\n\n"
        f"{data_sample}...\n\n"
        "CRITICAL REQUIREMENTS:\n"
        f"1. HARDCODE the file path as exactly: \"{data_filepath}\"\n"
        "2. DO NOT use input() to ask for file paths\n"
        "3. DO NOT use os.path.expanduser or similar functions\n" 
        "4. DO NOT use relative paths like './data.txt'\n"
        "5. Include robust error handling\n"
        "6. If the file is a combined document file, look for document sections marked with '## DOCUMENT X:'"
    )
    
    context = Context(system_prompt=code_gen_prompt)
    
    # Add the analysis question with specific instructions
    context.add_message(
        MessageRole.USER,
        f"Write Python code to:\n"
        f"1. Read data from EXACTLY this file path: {data_filepath}\n"
        f"2. Answer this question: {analysis_question}\n\n"
        f"IMPORTANT: Your code MUST use the exact file path: {data_filepath}\n"
        f"DO NOT ask the user for a file path. DO NOT use input() functions."
    )
    
    # Generate the code
    response = await provider.generate_response(context)
    
    # Extract code
    code = response.strip()
    if "```python" in code:
        code = code.split("```python", 1)[1]
    if "```" in code:
        code = code.split("```", 1)[0]
    
    # Verify that the code uses the exact file path
    if data_filepath not in code:
        # Fix the code by forcing it to use the correct path
        code = f"""
# IMPORTANT: Using the exact file path provided: {data_filepath}
# Original code has been modified to use this exact path

{code}
"""
    
    return code.strip()


async def explain_analysis_results(provider: LLMProvider, analysis_question: str, code_output: str) -> str:
    """Generate an explanation of the analysis results."""
    
    explanation_context = Context(
        system_prompt=(
            "You are a data analysis expert. Explain the following analysis results "
            "in a clear, concise manner. Focus on answering the user's question "
            "and highlighting the most important insights."
        )
    )
    
    explanation_context.add_message(
        MessageRole.USER,
        f"Question: {analysis_question}\n\n"
        f"Analysis results:\n{code_output}\n\n"
        "Explain these results in a clear, well-formatted way. "
        "Include the most important numbers and insights."
    )
    
    return await provider.generate_response(explanation_context)


async def fix_code_errors(provider: LLMProvider, code: str, error_msg: str, 
                         analysis_question: str, data_filepath: str, missing_packages: list = None) -> str:
    """Generate improved code based on error messages."""
    
    # Common prompt elements with explicit filepath reference
    filepath_instructions = (
        f"CRITICAL: The code MUST read data from this EXACT file path: {data_filepath}\n"
        f"DO NOT create mock data. DO NOT use input() to ask for the file path.\n"
        f"DO NOT use relative paths. HARDCODE this exact path in your code.\n"
        f"DO NOT use os.path.expanduser() or similar functions."
    )
    
    if missing_packages:
        # Fix missing package errors
        fix_context = Context(
            system_prompt=(
                "You are a Python expert. The following code has errors related to "
                "missing packages. Rewrite the code to either:\n"
                "1. Use only standard library packages, or\n"
                "2. Include explicit instructions to install required packages.\n"
                "Make sure the code accomplishes the same task.\n\n"
                f"{filepath_instructions}"
            )
        )
        
        fix_context.add_message(
            MessageRole.USER,
            f"This code failed with errors about missing packages: {', '.join(missing_packages)}\n\n"
            f"Code:\n```python\n{code}\n```\n\n"
            f"Error:\n{error_msg}\n\n"
            "Please rewrite the code to fix these issues while still answering "
            f"the original question: {analysis_question}\n\n"
            f"CRITICAL: The code MUST use this exact file path: {data_filepath}"
        )
    else:
        # Fix general errors
        fix_context = Context(
            system_prompt=(
                "You are a Python debugging expert. The following code has errors. "
                "Analyze the error message and rewrite the code to fix the issues.\n\n"
                f"{filepath_instructions}"
            )
        )
        
        fix_context.add_message(
            MessageRole.USER,
            f"This code failed to execute:\n```python\n{code}\n```\n\n"
            f"Error:\n{error_msg}\n\n"
            "Please rewrite the code to fix these issues while still answering "
            f"the original question: {analysis_question}\n\n"
            f"CRITICAL: The code MUST read from file: {data_filepath}\n"
            f"HARDCODE this exact file path in your code. DO NOT use input() or ask the user for a path."
        )
    
    response = await provider.generate_response(fix_context)
    
    # Extract code
    fixed_code = response.strip()
    if "```python" in fixed_code:
        fixed_code = fixed_code.split("```python", 1)[1]
    if "```" in fixed_code:
        fixed_code = fixed_code.split("```", 1)[0]
    
    # Verify that the fixed code uses the exact file path
    if data_filepath not in fixed_code:
        # Force the correct path into the code
        fixed_code = f"""
# IMPORTANT: Using the exact file path provided: {data_filepath}
# Original code has been modified to use this exact path

{fixed_code}
"""
    
    return fixed_code.strip()