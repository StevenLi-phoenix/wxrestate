# WxRestate - 微信智能助手

WxRestate是一个基于Python的微信自动回复工具，它可以监听特定联系人的消息，并使用本地大语言模型(LLM)提供智能回复。

## 功能特点

- **消息监听**：自动监听白名单中联系人的微信消息
- **智能重组语言**：使用`@re`命令触发，帮助用户重新组织语言表达
- **问答功能**：使用`@ask`命令触发，回答用户的问题
- **待机模式**：在待机模式下，自动回复友好的提示信息
- **命令控制**：通过文件传输助手发送命令控制程序状态
- **本地LLM支持**：使用LM Studio本地部署的大语言模型，保护隐私

## 安装要求

- Python 3.6+
- 微信PC客户端
- LM Studio (用于本地部署大语言模型)

## 依赖库

```
wxauto
pyautogui
openai
tqdm
```

## 安装步骤

1. 克隆仓库到本地
```
git clone https://github.com/yourusername/wxrestate.git
cd wxrestate
```

2. 安装依赖
```
pip install -r requirements.txt
```

3. 配置LM Studio
   - 安装并启动LM Studio
   - 加载所需模型（默认使用qwen2.5-7b-instruct）
   - 启动API服务器（默认端口18000）

4. 配置secret.json（可选）
```json
{
    "base_url": "http://127.0.0.1:18000/v1/",
    "api_key": "lm-studio-api-key",
    "model": "qwen2.5-7b-instruct@q4_k_m",
    "temperature": 0.4
}
```

## 使用方法

1. 启动微信PC客户端并登录
2. 运行程序
```
python main.py
```

3. 使用命令：
   - `@re [文本]` - 重新组织语言表达
   - `@ask [问题]` - 回答问题
   - 在文件传输助手中使用以下命令控制程序：
     - `@command standby` - 进入待机模式
     - `@command active` - 进入激活模式
     - `@command switch` - 切换模式
     - `@command status` - 查看当前模式
     - `@execute [命令]` - 执行系统命令

## 白名单配置

在`main.py`中修改`white_list`变量，添加或删除需要监听的联系人：
```python
white_list = ["李东荣","胡运心","文件传输助手"]
```

## 注意事项

- 程序需要微信窗口保持打开状态
- 使用本地LLM可能需要较高的计算资源
- 请勿将此工具用于违反微信使用条款的行为

## 许可证

[MIT License](LICENSE) 