"""WSGI entrypoint for gunicorn / production."""
from server import app
import util

util.load_saved_artifacts()
