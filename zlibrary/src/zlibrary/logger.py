import logging
import sys

# Get the logger instance
logger = logging.getLogger('zlibrary')

# Remove existing handlers (specifically the NullHandler)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create a StreamHandler to output to stderr
stream_handler = logging.StreamHandler(sys.stderr)

# Create a FileHandler to output to a file
# Log file will be in the zlibrary package directory, adjust path as needed for workspace root.
# For now, let's try a relative path which might end up inside the zlibrary package.
# A better approach might be an absolute path or one derived from an environment variable.
# Using a path relative to the workspace root for now:
log_file_path = './logs/zlibrary_debug.log' # Changed to logs/ subdirectory
# Ensure the directory exists
import os
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
file_handler = logging.FileHandler(log_file_path, mode='a') # Append mode

# Set a formatter (optional, but good practice)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

# Set the logging level to DEBUG to capture all messages
logger.setLevel(logging.DEBUG)

# Optional: Prevent propagation to root logger if it has handlers you don't want
# logger.propagate = False
