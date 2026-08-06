"""
app/core/templating.py

Patches Starlette's Jinja2Templates so every instance created anywhere
in the app automatically gets the i18n/date globals, without editing
every router file individually.

Must be imported before any router module creates a Jinja2Templates
instance, so import this at the very top of main.py.
"""

from fastapi.templating import Jinja2Templates

from app.core.language import t, get_lang, lang_dir
from app.core.jdate import jdate, jdatetime

_original_init = Jinja2Templates.__init__


def _patched_init(self, *args, **kwargs):
    _original_init(self, *args, **kwargs)
    self.env.globals["t"] = t
    self.env.globals["current_lang"] = get_lang
    self.env.globals["lang_dir"] = lang_dir
    self.env.globals["jdate"] = jdate
    self.env.globals["jdatetime"] = jdatetime


Jinja2Templates.__init__ = _patched_init