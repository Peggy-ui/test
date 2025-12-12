import os
import glob
import sys

dist_dir = 'dist'
# "米匯寶資料匯入.exe" using unicode escapes to avoid encoding issues
target_name = '\u7c73\u532f\u5bf6\u8cc7\u6599\u532f\u5165.exe'
target_path = os.path.join(dist_dir, target_name)

# Get all exe files in dist
exes = glob.glob(os.path.join(dist_dir, '*.exe'))
if not exes:
    print("No exe files found in dist")
    sys.exit(1)

# Find the newest file
newest_exe = max(exes, key=os.path.getmtime)
print(f"Newest exe found: {newest_exe!r}")
print(f"Target name: {target_name!r}")
print(f"Comparison (basename == target): {os.path.basename(newest_exe) == target_name}")

# Check if it is already the target name
if os.path.basename(newest_exe) == target_name:
    print("Newest exe is already named correctly.")
    sys.exit(0)

# Rename
try:
    if os.path.exists(target_path):
        # Check if the existing one is the one we want to rename (same file)
        if os.path.abspath(target_path) == os.path.abspath(newest_exe):
             print("Newest exe is already named correctly (path match).")
             sys.exit(0)
        
        print(f"Removing existing target {target_path}")
        os.remove(target_path)

    os.rename(newest_exe, target_path)
    print(f"Renamed {newest_exe!r} to {target_path!r}")
except Exception as e:
    print(f"Error renaming: {e}")
    sys.exit(1)