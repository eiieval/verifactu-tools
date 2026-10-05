# Copies _shared.py into every task file, between the shared markers. Each Kaggle task file must stand alone.
from pathlib import Path

HERE = Path(__file__).parent
START, END = "# ---- shared:", "# ---- end shared ----"
shared = (HERE / "_shared.py").read_text().strip("\n")
for f in sorted(HERE.glob("vf_*.py")):
    text = f.read_text()
    a = text.index(START)
    b = text.index(END) + len(END)
    f.write_text(text[:a] + shared + text[b:])
    print("synced", f.name)
