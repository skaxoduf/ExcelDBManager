import shutil
from PIL import Image
import os

# Source path (artifact) - UPDATED with actual path from previous step
source_path = r"C:/Users/Administrator/.gemini/antigravity/brain/76e857f8-5af6-4f5d-a7ac-13f71748c279/app_logo_1767160084264.png"
dest_dir = r"D:/NTY/01_마이그레이션/3_src/Dev3/ExcelDBManager/src/assets"
dest_png = os.path.join(dest_dir, "logo.png")
dest_ico = r"D:/NTY/01_마이그레이션/3_src/Dev3/ExcelDBManager/logo.ico" # ICO at root for pyinstaller

os.makedirs(dest_dir, exist_ok=True)

# Copy PNG
shutil.copy2(source_path, dest_png)
print(f"Copied logo to {dest_png}")

# Convert to ICO
img = Image.open(dest_png)
img.save(dest_ico, format='ICO', sizes=[(256, 256)])
print(f"Converted logo to {dest_ico}")
