from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_remote_address_with_options_exclusion(request: Request):
    """
    Custom key function that excludes OPTIONS requests from rate limiting.
    OPTIONS requests are CORS preflight requests and shouldn't be rate limited.
    """
    if request.method == "OPTIONS":
        return None  # Exclude OPTIONS requests from rate limiting
    return get_remote_address(request)

# Global limiter instance with custom key function that excludes OPTIONS
limiter = Limiter(key_func=get_remote_address_with_options_exclusion) 