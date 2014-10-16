import os
import sys


try:
    from tej.main import main
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from tej.main import main


if __name__ == '__main__':
    main()
