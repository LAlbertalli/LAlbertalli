import os

# Configurable directories to search for recent images (expanded at runtime)
IMAGE_SEARCH_DIRS = [
    os.path.expanduser("~/Downloads"),
]

# Configurable regex pattern for images (case-insensitive)
IMAGE_PATTERN = r"^Gemini_Generated_Image_.*\.(png|jpg|jpeg)$"

# Maximum age of recent images in seconds (86400 seconds = 1 day)
IMAGE_MAX_AGE_SECONDS = 86400
