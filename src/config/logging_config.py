import logging
import logging.handlers
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
CONSOLE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging():
    """Set up logging configuration"""
    # Create a formatter
    file_formatter = logging.Formatter(LOG_FORMAT)
    console_formatter = logging.Formatter(CONSOLE_FORMAT)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    root_logger.handlers = []

    # Console handler (always add this)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # Check if we're in a read-only environment (like Vercel)
    # We'll try to create a temporary file to test if we can write
    is_read_only = False
    try:
        test_file_path = os.path.join(os.getcwd(), '.write_test')
        with open(test_file_path, 'w') as f:
            f.write('test')
        os.remove(test_file_path)
    except (OSError, IOError):
        is_read_only = True
        logging.warning("Detected read-only filesystem. File logging disabled.")

    # Only add file handlers if we're not in a read-only environment
    if not is_read_only:
        # File handler for all logs
        all_logs_file = os.path.join(LOGS_DIR, f'babywise_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.handlers.RotatingFileHandler(
            all_logs_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

        # Error log file handler
        error_logs_file = os.path.join(LOGS_DIR, f'babywise_error_{datetime.now().strftime("%Y%m%d")}.log')
        error_file_handler = logging.handlers.RotatingFileHandler(
            error_logs_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_file_handler.setFormatter(file_formatter)
        error_file_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_file_handler)

    # Create loggers for different components
    loggers = {
        'agent': logging.getLogger('agent'),
        'memory': logging.getLogger('memory'),
        'graph': logging.getLogger('graph'),
        'database': logging.getLogger('database'),
        'api': logging.getLogger('api')
    }

    # Configure component loggers
    for logger in loggers.values():
        logger.propagate = True
        logger.setLevel(logging.DEBUG)

    return loggers

# Initialize logging when module is imported
loggers = setup_logging()

def get_logger(name: str) -> logging.Logger:
    """Get a logger by name"""
    return logging.getLogger(name) 