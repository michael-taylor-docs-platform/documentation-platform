import subprocess
import sys

print("Running transformation...")
result = subprocess.run(["python", "scripts/transform.py"])

if result.returncode != 0:
    print("Transformation failed.")
    sys.exit(1)

print("Building MkDocs site...")
subprocess.run(["mkdocs", "build"])