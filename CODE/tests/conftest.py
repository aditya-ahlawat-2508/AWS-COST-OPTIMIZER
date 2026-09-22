import os
import sys

# handler.py does `import cost_explorer, services_inventory, service_actions`
# assuming those modules sit next to it on sys.path (how Lambda deploys them),
# so tests need the same layout rather than importing lambda_ as a package.
LAMBDA_DIR = os.path.join(os.path.dirname(__file__), "..", "lambda_")
sys.path.insert(0, os.path.abspath(LAMBDA_DIR))
