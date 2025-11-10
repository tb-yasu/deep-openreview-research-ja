"""Factory function for creating LLM instances with GPT-5 support."""

from langchain_openai import ChatOpenAI


def create_chat_openai(
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 1000,
    timeout: int = 60,
    **kwargs
) -> ChatOpenAI:
    """Create ChatOpenAI instance with appropriate parameters for the model.
    
    GPT-5 series requires 'max_completion_tokens' instead of 'max_tokens'.
    
    Args:
    ----
        model: Model name (e.g., 'gpt-4o', 'gpt-5-nano')
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum number of tokens to generate
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to ChatOpenAI
    
    Returns:
    -------
        ChatOpenAI instance configured for the specified model
    """
    # GPT-5 series uses max_completion_tokens instead of max_tokens
    if model.startswith("gpt-5"):
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            timeout=timeout,
            **kwargs
        )
    else:
        # GPT-4 and earlier use max_tokens
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs
        )

