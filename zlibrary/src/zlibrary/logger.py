import logging
import sys

# Get the logger instance
logger = logging.getLogger('zlibrary')

# Remove existing handlers (specifically the NullHandler)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create a StreamHandler to output to stderr
handler = logging.StreamHandler(sys.stderr)

# Set a formatter (optional, but good practice)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

# Set the logging level to DEBUG to capture all messages
logger.setLevel(logging.DEBUG)

# Optional: Prevent propagation to root logger if it has handlers you don't want
# logger.propagate = False
