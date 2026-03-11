import subprocess
import tempfile
from pathlib import Path

def get_clipboard():
    try:
        return subprocess.check_output("pbpaste", text=True)
    except Exception:
        print("Could not read clipboard.")
        exit(1)

def main():

    jd_text = get_clipboard()

    if not jd_text.strip():
        print("Clipboard appears empty.")
        exit(1)

    # write temporary jd file
    tmp = Path(tempfile.gettempdir()) / "jd_clipboard.txt"
    tmp.write_text(jd_text)

    print("JD pulled from clipboard.")
    print(f"Temporary file: {tmp}")

    # call your existing script
    subprocess.run(["python3", "build_from_jd.py", str(tmp)])

if __name__ == "__main__":
    main()