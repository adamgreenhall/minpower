import os
import glob
#add all .py modules too __all__ namespace
__all__ = [ os.path.basename(f)[:-3] for f in glob.glob(os.path.dirname(__file__)+"/*.py")]
