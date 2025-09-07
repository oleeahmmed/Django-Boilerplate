# simple loader: কী environment use হবে সেটা .env থেকে পড়ে dev বা prod import করবে
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DEBUG=(bool, False))
# read project .env
environ.Env.read_env(BASE_DIR / '.env')

if env.bool('DEBUG', default=False):
    from .dev import *
else:
    from .prod import *
