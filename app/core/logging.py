import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", format_type: str = "detailed") -> None:
    """Setup logging configuration for the application"""
    
    # Define log formats
    formats = {
        "simple": "%(levelname)s - %(message)s",
        "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "json": '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
    }
    
    # Get the format
    log_format = formats.get(format_type, formats["detailed"])
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Set specific logger levels for external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Create application logger
    logger = logging.getLogger("ticker_api")
    logger.info(f"Logging configured with level: {level}, format: {format_type}")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name or "ticker_api")