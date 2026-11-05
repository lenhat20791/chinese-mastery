import os
import subprocess
import argparse
from pathlib import Path
from config import SRC_DIR, REPO_CEFR, REPO_DICT

def run_command(cmd, cwd=None):
    """Chạy lệnh shell và in kết quả"""
    print(f"🔄 Đang chạy: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Lỗi: {result.stderr}")
        exit(1)
    return result.stdout

def clone_repo(repo_url, target_path):
    """Clone repo nếu chưa tồn tại"""
    if target_path.exists():
        print(f"✅ Đã tồn tại: {target_path.name}. Đang pull bản mới nhất...")
        run_command(["git", "pull"], cwd=target_path)
    else:
        print(f"⬇️ Đang clone {repo_url} vào {target_path.name}...")
        run_command(["git", "clone", "--depth", "1", repo_url, str(target_path)])
    
    # Lấy commit hash để sau này ghi công (ATTRIBUTION)
    hash_output = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=target_path)
    print(f"📌 Commit hash ({target_path.name}): {hash_output.strip()}\n")

def main():
    parser = argparse.ArgumentParser(description="Tải dữ liệu nguồn cho English Mastery")
    parser.parse_args()

    # Tạo thư mục work/src nếu chưa có
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    
    # Đảm bảo bỏ qua thư mục work/ trong git
    gitignore_path = SRC_DIR.parent / ".gitignore"
    if not gitignore_path.exists():
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("*\n")
            
    print("🚀 BẮT ĐẦU TẢI DỮ LIỆU NGUỒN...\n")
    
    clone_repo(REPO_CEFR, SRC_DIR / "Words-CEFR-Dataset")
    clone_repo(REPO_DICT, SRC_DIR / "english-vietnamese-dictionary")
    
    print("🎉 HOÀN TẤT! Dữ liệu đã sẵn sàng trong tools/english/work/src/")

if __name__ == "__main__":
    main()