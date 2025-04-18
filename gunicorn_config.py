import os

# Bind to the port Render gives you
bind = f"0.0.0.0:{os.environ.get('PORT', 8050)}"

# Only one worker process
workers = 1

# Use the threaded worker class so that `threads` is honored
worker_class = "gthread"
threads = 4

# Give requests a bit more time if needed
timeout = 120

# Load your app before the workers fork, so preload + cache priming happens once
preload_app = True

# Optional: better startup logs
loglevel = "info"
