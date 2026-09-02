"""Wrapper to run generate_5stacks_combined.py with correct sys.path."""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')
sys.stderr.write("sys.path inserted\n")
sys.stderr.flush()

try:
    import httpx
    sys.stderr.write(f"httpx imported: {httpx.__version__}\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"httpx import failed: {e}\n")
    sys.stderr.flush()
    sys.exit(1)

# Now run the actual generation
exec(open(r'C:\Code\screenshot-to-code\backend\generate_5stacks_combined.py').read())
