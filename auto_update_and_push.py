import subprocess
import datetime

DATA_FILES = ["cian_apartments.csv", "cian_apartments.json"]

def run_parser():
    print("🔍 Running parser...")
    try:
        result = subprocess.run(["python", "cian_parser.py"], check=True, capture_output=True, text=True)
        print("✅ Parser completed.\n")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Parser failed:\n{e.stderr}")
        return False

def file_changed(file_path):
    result = subprocess.run(["git", "diff", "--name-only", file_path], capture_output=True, text=True)
    return file_path in result.stdout

def commit_and_push(files):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"Auto-update CIAN data ({timestamp})"

    try:
        for file in files:
            print(f"📦 Staging {file}...")
            subprocess.run(["git", "add", file], check=True)

        print("📝 Committing...")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        print("🚀 Pushing...")
        subprocess.run(["git", "push"], check=True)

        print("✅ Pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error:\n{e}")

# === MAIN ===

if run_parser():
    changed_files = [f for f in DATA_FILES if file_changed(f)]
    if changed_files:
        commit_and_push(changed_files)
    else:
        print("⚠️ No changes detected in output files. Nothing to commit.")
