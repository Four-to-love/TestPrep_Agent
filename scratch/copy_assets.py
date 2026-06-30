import shutil
import os

src_path = "/Users/masha/.gemini/antigravity/brain/a3b6309d-1fa6-4f39-baa7-343f1060440a/recent_score_header_1782808562959.png"
dst_path = "/Users/masha/testprep_agent/recent_score_header.png"

try:
    if os.path.exists(src_path):
        shutil.copy(src_path, dst_path)
        print(f"Successfully copied banner image to: {dst_path}")
    else:
        print(f"Error: Source image not found at {src_path}")
except Exception as e:
    print(f"Error copying asset: {str(e)}")
