import sys
if sys.platform == 'win32':
    from resources.lib.tzlocal.win32 import get_localzone, reload_localzone
elif 'darwin' in sys.platform:
    from resources.lib.tzlocal.darwin import get_localzone, reload_localzone
else:
    from resources.lib.tzlocal.unix import get_localzone, reload_localzone
