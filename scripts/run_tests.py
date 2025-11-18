"""
測試執行腳本
提供便捷的測試執行命令
"""
import sys
import subprocess
from pathlib import Path


def run_tests(test_type: str = "all", coverage: bool = True, verbose: bool = True):
    """
    執行測試
    
    Args:
        test_type: 測試類型 (all, unit, integration, auth, api)
        coverage: 是否生成覆蓋率報告
        verbose: 是否顯示詳細輸出
    """
    # 基本命令 - 使用 python -m pytest 確保使用正確的 Python 環境
    cmd = [sys.executable, "-m", "pytest"]
    
    # 測試類型
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "auth":
        cmd.extend(["-m", "auth"])
    elif test_type == "api":
        cmd.extend(["-m", "api"])
    elif test_type == "database":
        cmd.extend(["-m", "database"])
    elif test_type != "all":
        cmd.append(f"tests/test_{test_type}.py")
    
    # 詳細輸出
    if verbose:
        cmd.append("-v")
    
    # 覆蓋率
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
        ])
    
    # 執行測試
    print(f"🧪 執行測試: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("\n" + "=" * 80)
            print("✅ 測試通過！")
            if coverage:
                print("📊 覆蓋率報告已生成: htmlcov/index.html")
        else:
            print("\n" + "=" * 80)
            print("❌ 測試失敗！")
            sys.exit(1)
    except FileNotFoundError:
        print("\n" + "=" * 80)
        print("❌ 錯誤：找不到 pytest")
        print("請先安裝 pytest：pip install pytest pytest-cov")
        sys.exit(1)


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="執行測試")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "auth", "api", "database", "users", "departments", "settings", "models"],
        help="測試類型",
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="不生成覆蓋率報告",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="減少輸出",
    )
    
    args = parser.parse_args()
    
    run_tests(
        test_type=args.test_type,
        coverage=not args.no_coverage,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
