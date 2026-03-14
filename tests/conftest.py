import sys
import os

# Add the src directory to sys.path so that tests can import the mqsim package
# This is necessary when running pytest from the project root.
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
