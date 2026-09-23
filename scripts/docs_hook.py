"""MkDocs preview/build hook. Never inspect local project or run state."""
import importlib.util
from pathlib import Path

def on_config(config):
    path = Path(__file__).with_name("generate_docs.py")
    spec = importlib.util.spec_from_file_location("workflow_docs_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate()
    return config
