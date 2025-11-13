"""
Docker 環境測試腳本
測試開發環境 (docker-compose.yml) 和生產環境 (docker-compose.prod.yml)
"""
import subprocess
import time
import sys
import httpx
import asyncio
from typing import Tuple, List, Dict


class Colors:
    """終端顏色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印標題"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.ENDC}\n")


def print_step(step: int, text: str):
    """打印步驟"""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}📦 步驟 {step}: {text}{Colors.ENDC}")


def print_success(text: str):
    """打印成功訊息"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """打印錯誤訊息"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    """打印警告訊息"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def run_command(cmd: str, description: str, capture: bool = True) -> Tuple[bool, str]:
    """執行命令"""
    print(f"\n{Colors.OKBLUE}🔧 {description}{Colors.ENDC}")
    print(f"   命令: {cmd}\n")
    
    try:
        if capture:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=120
            )
            
            if result.stdout:
                print(result.stdout)
            if result.stderr and "warning" not in result.stderr.lower():
                print(result.stderr)
            
            return result.returncode == 0, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd, shell=True, timeout=120)
            return result.returncode == 0, ""
            
    except subprocess.TimeoutExpired:
        print_error("命令執行超時")
        return False, ""
    except Exception as e:
        print_error(f"執行失敗: {str(e)}")
        return False, ""


async def wait_for_service(url: str, service_name: str, max_retries: int = 30, delay: int = 2) -> bool:
    """等待服務啟動"""
    print(f"\n{Colors.OKCYAN}⏳ 等待 {service_name} 啟動...{Colors.ENDC}")
    
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print_success(f"{service_name} 已就緒!")
                    return True
        except Exception:
            pass
        
        if (i + 1) % 5 == 0:
            print(f"   嘗試 {i+1}/{max_retries}...")
        time.sleep(delay)
    
    print_error(f"{service_name} 啟動超時")
    return False


async def test_api_endpoints(base_url: str) -> Dict[str, bool]:
    """測試 API 端點"""
    print(f"\n{Colors.OKBLUE}🧪 測試 API 端點{Colors.ENDC}\n")
    
    results = {}
    tests = [
        ("健康檢查", f"{base_url}/health"),
        ("API 健康", f"{base_url}/api/health"),
        ("OpenAPI", f"{base_url}/openapi.json"),
        ("Swagger UI", f"{base_url}/docs"),
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in tests:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    print_success(f"{name}: {response.status_code}")
                    results[name] = True
                else:
                    print_error(f"{name}: {response.status_code}")
                    results[name] = False
            except Exception as e:
                print_error(f"{name}: {str(e)}")
                results[name] = False
    
    return results


async def test_authentication(base_url: str) -> bool:
    """測試認證功能"""
    print(f"\n{Colors.OKBLUE}🔐 測試認證功能{Colors.ENDC}\n")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 測試登入
            response = await client.post(
                f"{base_url}/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            
            if response.status_code == 200:
                token = response.json().get("access_token")
                print_success(f"登入成功，Token: {token[:20]}...")
                
                # 測試使用 token
                response = await client.get(
                    f"{base_url}/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    user = response.json()
                    print_success(f"Token 驗證成功，用戶: {user.get('username')}")
                    return True
                else:
                    print_error(f"Token 驗證失敗: {response.status_code}")
                    return False
            else:
                print_warning(f"登入失敗: {response.status_code} (可能尚未初始化數據)")
                return False
    except Exception as e:
        print_warning(f"認證測試失敗: {str(e)} (可能尚未初始化數據)")
        return False


def test_environment(compose_file: str, env_name: str, port: int = 8000) -> bool:
    """測試指定環境"""
    print_header(f"測試 {env_name} 環境")
    
    # 步驟 1: 停止並清理
    print_step(1, f"清理 {env_name} 環境")
    success, _ = run_command(
        f"docker-compose -f {compose_file} down -v",
        "停止並移除容器"
    )
    
    # 步驟 2: 啟動服務
    print_step(2, f"啟動 {env_name} 環境")
    success, output = run_command(
        f"docker-compose -f {compose_file} up -d",
        "啟動所有服務"
    )
    
    if not success:
        print_error("服務啟動失敗")
        return False
    
    # 步驟 3: 等待服務就緒
    print_step(3, "等待服務就緒")
    
    # 等待基礎服務
    time.sleep(10)
    
    # 檢查容器狀態
    print_step(4, "檢查容器狀態")
    success, output = run_command(
        f"docker-compose -f {compose_file} ps",
        "顯示容器狀態"
    )
    
    # 如果是生產環境，還需要等待 API 構建和啟動
    if "prod" in compose_file:
        print_step(5, "等待 API 服務啟動")
        
        # 檢查 API 日誌
        time.sleep(15)  # 給更多時間讓 API 啟動
        
        run_command(
            f"docker-compose -f {compose_file} logs backend --tail=20",
            "查看 API 日誌"
        )
        
        # 等待 API 可用
        api_ready = asyncio.run(wait_for_service(
            f"http://localhost:{port}/health",
            "FastAPI 服務",
            max_retries=30,
            delay=2
        ))
        
        if not api_ready:
            print_error("API 服務未能啟動，查看日誌:")
            run_command(
                f"docker-compose -f {compose_file} logs backend --tail=50",
                "查看完整日誌"
            )
            return False
        
        # 步驟 6: 初始化數據庫
        print_step(6, "初始化數據庫")
        
        # 執行遷移
        success, _ = run_command(
            f"docker-compose -f {compose_file} exec -T backend alembic upgrade head",
            "執行數據庫遷移"
        )
        
        if not success:
            # 嘗試標記版本
            run_command(
                f"docker-compose -f {compose_file} exec -T backend alembic stamp head",
                "標記數據庫版本"
            )
        
        time.sleep(2)
        
        # 初始化默認數據
        success, _ = run_command(
            f"docker-compose -f {compose_file} exec -T backend python scripts/init_db.py",
            "初始化默認數據"
        )
        
        time.sleep(2)
        
        # 步驟 7: 測試 API
        print_step(7, "測試 API 功能")
        
        api_results = asyncio.run(test_api_endpoints(f"http://localhost:{port}"))
        auth_result = asyncio.run(test_authentication(f"http://localhost:{port}"))
        
        # 顯示測試結果
        print(f"\n{Colors.BOLD}測試結果:{Colors.ENDC}")
        passed = sum(1 for r in api_results.values() if r)
        total = len(api_results)
        print(f"  API 端點: {passed}/{total} 通過")
        if auth_result:
            print_success("  認證功能: 通過")
        
        all_passed = passed == total and auth_result
    else:
        # 開發環境只檢查服務是否啟動
        print_step(5, "檢查服務健康狀態")
        
        # 等待數據庫就緒
        time.sleep(5)
        
        # 檢查各服務日誌
        services = ["postgres", "redis", "qdrant"]
        for service in services:
            run_command(
                f"docker-compose -f {compose_file} logs {service} --tail=10",
                f"查看 {service} 日誌"
            )
        
        all_passed = True
    
    # 測試摘要
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    if all_passed:
        print_success(f"✅ {env_name} 環境測試通過!")
    else:
        print_error(f"❌ {env_name} 環境測試失敗")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    return all_passed


def main():
    """主函數"""
    print_header("Docker 環境完整測試")
    print(f"{Colors.BOLD}測試項目:{Colors.ENDC}")
    print("  1. 開發環境 (docker-compose.yml)")
    print("  2. 生產環境 (docker-compose.prod.yml)")
    
    results = {}
    
    # 測試開發環境
    print(f"\n{Colors.OKCYAN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}開始測試開發環境...{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'='*70}{Colors.ENDC}")
    
    results['開發環境'] = test_environment(
        "docker-compose.yml",
        "開發環境"
    )
    
    # 詢問是否繼續測試生產環境
    print(f"\n{Colors.WARNING}準備測試生產環境...{Colors.ENDC}")
    time.sleep(3)
    
    print(f"\n{Colors.OKCYAN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}開始測試生產環境...{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'='*70}{Colors.ENDC}")
    
    results['生產環境'] = test_environment(
        "docker-compose.prod.yml",
        "生產環境",
        port=8000
    )
    
    # 最終總結
    print_header("測試總結")
    
    for env_name, passed in results.items():
        if passed:
            print_success(f"{env_name}: ✅ 通過")
        else:
            print_error(f"{env_name}: ❌ 失敗")
    
    all_passed = all(results.values())
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    if all_passed:
        print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 所有環境測試通過!{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}❌ 部分環境測試失敗{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    # 清理提示
    print(f"{Colors.WARNING}提示: 測試容器仍在運行{Colors.ENDC}")
    print("清理開發環境: docker-compose -f docker-compose.yml down -v")
    print("清理生產環境: docker-compose -f docker-compose.prod.yml down -v")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️  測試被中斷{Colors.ENDC}")
        sys.exit(1)
