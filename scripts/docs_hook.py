"""MkDocs preview/build hook. Never inspect local project or run state."""
import importlib.util
from pathlib import Path
from mkdocs.exceptions import PluginError
from mkdocs.utils import get_relative_url

def module(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("workflow_" + name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded

content = module("docs_content")

def on_config(config):
    module("generate_docs").generate()
    try:
        content.validate()
    except content.ContentError as exc:
        raise PluginError(str(exc)) from exc
    return config

def on_page_markdown(markdown, page, config, files):
    try:
        return content.render(markdown, lambda target: get_relative_url(target, page.url), page.meta)
    except content.ContentError as exc:
        raise PluginError(f"{page.file.src_uri}: {exc}") from exc
