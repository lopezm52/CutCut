# Verificar archivos del proyecto
import os
print("Archivos en el proyecto CutCut:")
for root, dirs, files in os.walk("/Users/lopezm52/Projects/CutCut"):
    level = root.replace("/Users/lopezm52/Projects/CutCut", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files:
        if not file.startswith('.'):
            print(f"{subindent}{file}")