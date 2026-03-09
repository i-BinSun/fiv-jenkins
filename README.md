# Jenkins Test Automation Framework

本项目提供了在 Ubuntu 上部署 Jenkins 的完整解决方案，用于定期执行测试脚本并在测试失败时发送邮件通知。

## 项目结构

```
fiv-jenkins/
├── install_jenkins.sh      # Jenkins 安装脚本 (Ubuntu)
├── Jenkinsfile             # Jenkins Pipeline 配置
├── Dockerfile              # Docker 镜像构建文件
├── docker-compose.yml      # Docker Compose 编排文件
├── .dockerignore           # Docker 构建忽略文件
├── .gitignore              # Git 忽略文件
├── requirements.txt        # Python 依赖
├── .env.example            # 邮件配置示例
├── scripts/
│   ├── run_tests.py        # 测试运行脚本（收集失败信息）
│   └── send_email.py       # 邮件发送脚本
└── tests/
    ├── __init__.py
    └── test_api_example.py # 示例测试文件
```

## 快速开始

### 1a. Docker 方式部署（推荐）

```bash
# 克隆项目
git clone <your-repo> /opt/fiv-jenkins
cd /opt/fiv-jenkins

# 复制环境变量配置文件并填写实际值
cp .env.example .env
# 编辑 .env 填入 SMTP 和邮件配置

# 构建并启动容器
docker compose up -d --build

# 查看 Jenkins 日志
docker compose logs -f jenkins

# 停止容器
docker compose down
```

容器启动后访问 http://localhost:8080 即可使用 Jenkins（已跳过初始设置向导并预装所需插件）。

### 1b. 直接安装 Jenkins (Ubuntu)

```bash
# 下载项目到 Ubuntu 服务器
git clone <your-repo> /opt/fiv-jenkins
cd /opt/fiv-jenkins

# 运行安装脚本
sudo bash install_jenkins.sh
```

安装完成后：
- 访问 http://localhost:8080
- 使用安装脚本显示的初始密码登录
- 安装推荐的插件
- 创建管理员账户

### 2. 配置 Jenkins

#### 2.1 安装必要插件

在 Jenkins 中安装以下插件：
- **Pipeline** (通常已预装)
- **Email Extension Plugin** (邮件通知)
- **Git Plugin** (Git 集成)

#### 2.2 配置凭据

进入 `Jenkins > Manage Jenkins > Manage Credentials`，添加以下凭据：

| 凭据 ID | 类型 | 描述 |
|---------|------|------|
| `smtp-server` | Secret text | SMTP 服务器地址 (如 smtp.gmail.com) |
| `smtp-user` | Secret text | SMTP 用户名 |
| `smtp-password` | Secret text | SMTP 密码/App Password |
| `email-sender` | Secret text | 发件人邮箱 |
| `email-recipients` | Secret text | 收件人邮箱（逗号分隔） |

#### 2.3 创建 Pipeline Job

1. 点击 `New Item`
2. 输入名称，选择 `Pipeline`
3. 在 Pipeline 配置中：
   - 选择 `Pipeline script from SCM`
   - SCM 选择 `Git`
   - 填写仓库 URL
   - 脚本路径填写 `Jenkinsfile`

### 3. 编写测试用例

在 `tests/` 目录下创建测试文件，文件名需要以 `test_` 开头：

```python
import unittest
import requests

class TestYourAPI(unittest.TestCase):
    BASE_URL = "http://your-webapp.com/api"
    
    def test_submit_data(self):
        """测试数据提交"""
        response = requests.post(
            f"{self.BASE_URL}/submit",
            json={"name": "test", "value": 100}
        )
        self.assertEqual(response.status_code, 200)
    
    def test_get_data(self):
        """测试数据获取"""
        response = requests.get(f"{self.BASE_URL}/data")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

if __name__ == "__main__":
    unittest.main()
```

### 4. 配置定时执行

在 `Jenkinsfile` 中修改 cron 表达式：

```groovy
triggers {
    cron('0 8 * * *')  // 每天早上8点执行
}
```

常用 cron 表达式：
- `0 8 * * *` - 每天 8:00
- `0 */2 * * *` - 每2小时
- `0 8,18 * * 1-5` - 工作日 8:00 和 18:00
- `H/30 * * * *` - 每30分钟

## 邮件配置说明

### Gmail 配置

1. 在 Google 账户中启用两步验证
2. 生成应用专用密码: https://myaccount.google.com/apppasswords
3. 使用应用专用密码作为 SMTP_PASSWORD

配置参数：
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### 其他邮箱

| 邮箱服务 | SMTP 服务器 | 端口 |
|----------|-------------|------|
| Outlook/Office365 | smtp.office365.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |
| QQ邮箱 | smtp.qq.com | 587 |
| 163邮箱 | smtp.163.com | 465 |

## 测试报告格式

测试运行后会生成 `test_report.json`，包含以下信息：

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "duration_seconds": 5.23,
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 1,
    "errors": 1,
    "skipped": 0
  },
  "all_passed": false,
  "failures": [
    {
      "test_name": "test_api_example.TestAPI.test_submit",
      "test_class": "TestAPI",
      "test_method": "test_submit",
      "error_type": "AssertionError",
      "error_message": "200 != 500",
      "stack_trace": "..."
    }
  ],
  "errors": [...]
}
```

## 本地测试

在部署到 Jenkins 之前，可以在本地测试：

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
python scripts/run_tests.py --test-dir tests --output test_report.json

# 发送测试邮件（需要配置环境变量）
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export EMAIL_SENDER=your-email@gmail.com
export EMAIL_RECIPIENTS=recipient@example.com

python scripts/send_email.py --report test_report.json --always-send
```

## 故障排除

### Jenkins 无法启动
```bash
# 检查 Jenkins 服务状态
sudo systemctl status jenkins

# 查看日志
sudo journalctl -u jenkins -f
```

### 邮件发送失败
1. 检查 SMTP 凭据是否正确
2. 确认邮箱已启用 SMTP 访问
3. 对于 Gmail，确保使用应用专用密码

### 测试发现失败
```bash
# 手动运行测试确认
cd /path/to/project
python -m pytest tests/ -v
```

## 自定义扩展

### 添加更多测试目录
修改 `Jenkinsfile` 中的测试命令：
```groovy
python scripts/run_tests.py \
    --test-dir tests \
    --test-dir integration_tests \
    --pattern "test_*.py"
```

### 添加 Slack 通知
可以扩展 `send_email.py` 添加 Slack webhook 支持，或安装 Jenkins Slack Notification Plugin。

### 生成 HTML 报告
安装 `pytest-html` 并修改测试命令以生成可视化报告。

## 📄 License
