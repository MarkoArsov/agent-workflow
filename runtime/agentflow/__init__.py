"""Deprecated import compatibility until 1.0; use plovi instead."""
import warnings
from plovi import *
from plovi import __version__, __path__
warnings.warn("agentflow is now plovi; import plovi instead (compatibility until 1.0)", DeprecationWarning, stacklevel=2)
