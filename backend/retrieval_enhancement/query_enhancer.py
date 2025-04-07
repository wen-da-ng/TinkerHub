from typing import List, Dict, Any
from mcp.context import Context, MessageRole
from mcp.providers import LLMProvider

async def rewrite_query(provider: LLMProvider, original_query: str, rewriting_type: str = "expansion") -> str:
    """
    Rewrite a query to improve retrieval performance.
    
    Args:
        provider: The LLM provider to use for rewriting
        original_query: The user's original query
        rewriting_type: The type of rewriting to perform (expansion, disambiguation, or synonyms)
        
    Returns:
        The rewritten query
    """
    
    # Create a specialized system prompt based on the rewriting type
    if rewriting_type == "expansion":
        system_prompt = (
            "You are a query expansion specialist. Your task is to expand user queries to improve "
            "search results by adding related terms and concepts. Maintain the original meaning but "
            "make the query more comprehensive. Return ONLY the expanded query without explanations."
        )
    elif rewriting_type == "disambiguation":
        system_prompt = (
            "You are a query disambiguation specialist. Your task is to identify potential ambiguities "
            "in the user's query and create a version that clarifies the likely intent. "
            "Return ONLY the disambiguated query without explanations."
        )
    elif rewriting_type == "synonyms":
        system_prompt = (
            "You are a query enrichment specialist. Your task is to add synonyms and alternative "
            "phrasings to the user's query to improve search results. "
            "Return ONLY the enriched query without explanations."
        )
    else:
        # Default to expansion
        system_prompt = (
            "You are a query enhancement specialist. Your task is to improve the user's query "
            "for better search results by adding context, synonyms, or clarifications as needed. "
            "Return ONLY the enhanced query without explanations."
        )
    
    # Create context with the specialized system prompt
    context = Context(system_prompt=system_prompt)
    
    # Add the user's query with specific instructions
    context.add_message(
        MessageRole.USER,
        f"Original query: \"{original_query}\"\n\n"
        f"Rewrite this query to improve search results. Focus on preserving the original intent "
        f"while making it more comprehensive for retrieval purposes."
    )
    
    # Generate the rewritten query
    rewritten_query = await provider.generate_response(context)
    
    # Remove any extra formatting like quotes or prefixes
    rewritten_query = rewritten_query.strip('"\'')
    
    # If the result is very long, truncate it to a reasonable length
    if len(rewritten_query) > 500:
        rewritten_query = rewritten_query[:500]
    
    return rewritten_query


async def generate_hyde_document(provider: LLMProvider, query: str) -> str:
    """
    Generate a hypothetical document that would answer the query (HyDE technique).
    
    Args:
        provider: The LLM provider to use
        query: The user's query
        
    Returns:
        A synthetic document that would contain the answer to the query
    """
    # Create a specialized system prompt for HyDE
    system_prompt = (
        "You are an expert at creating synthetic documents. Given a query, your task is to create "
        "a short, factual passage that would directly answer the query. This synthetic passage "
        "should mimic the style and content of a real document that would contain the answer. "
        "Be concise but comprehensive."
    )
    
    # Create context with the specialized system prompt
    context = Context(system_prompt=system_prompt)
    
    # Add the user's query with specific instructions
    context.add_message(
        MessageRole.USER,
        f"Query: \"{query}\"\n\n"
        f"Generate a short passage (3-5 sentences) that directly answers this query. "
        f"The passage should read like an excerpt from a real document or article that "
        f"contains the answer to the query."
    )
    
    # Generate the synthetic document
    synthetic_document = await provider.generate_response(context)
    
    return synthetic_document