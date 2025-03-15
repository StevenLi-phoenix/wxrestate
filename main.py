import wxauto
import pyautogui as pg
import openai
import time
from tqdm import tqdm
import os
import json
import logging
import subprocess


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_base_url = "http://127.0.0.1:18000/v1/"
api_key = "lm-studio-api-key"
model = "qwen2.5-7b-instruct@q4_k_m"
temperature = 0.4
client = openai.OpenAI(base_url=openai_base_url, api_key=api_key)

# secret = json.load(open("secret.json", "r"))
# base_url = secret.get("base_url")
# api_key = secret.get("api_key")
# model = secret.get("model")
# client = openai.OpenAI(base_url=base_url, api_key=api_key)

white_list = ["李东荣","胡运心","文件传输助手"]
check_message_interval = 1

STANDBY_MODE = True


def cot(content:str, think_start = "<think>", think_end = "</think>", return_think_content = False):
    # 当使用cot模型时，content中会包含<think>和</think>，用于分割出思考内容和回复内容
    think_content = content.split(think_start)[1].split(think_end)[0]
    if return_think_content:
        return think_content, content.split(think_end)[1]
    else:
        return content.split(think_end)[1]

def convert_chat_messages_to_str(list_of_messages:list):
    chat_history = ""
    for one_message in list_of_messages:
        chat_history += f'{str(one_message.type)}说：{str(one_message.content)}\n'
    return chat_history

wx = wxauto.WeChat()
for name in white_list:
    wx.AddListenChat(name)


# 持续监听消息，并且收到消息后回复“收到”
logger.info("开始监听消息")
tqdm_bar = tqdm(desc="监听消息", unit="条", unit_scale=True)
while True:
    msgs = wx.GetListenMessage()
    for chat in msgs:
        tqdm_bar.update(1)
        who = chat.who              # 获取聊天窗口名（人或群名）
        one_msgs = msgs.get(chat)   # 获取消息内容
        for msg in one_msgs:
            msgtype = msg.type       # 获取消息类型
            content = msg.content    # 获取消息内容，字符串类型的消息内容
            logger.info(f'【{who}】：[{msgtype}]{content}')
            if "@re" in content and msgtype == "self":
                STANDBY_MODE = False
                content = content.replace("@restate", "")
                logger.debug("收到@restate消息" + "content:" + content)
                previous_message_str = convert_chat_messages_to_str(chat.GetAllMessage())
                if len(previous_message_str) > 0:
                    previous_message_str = "以下是用户(self)和对方(friend)的之前发的消息：\n" + previous_message_str
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你的任务是帮助有语言障碍的用户使用幽默和不冒犯的语言风格**重新组织语言**，**不要回答问题**，使用\n分割多条消息。"},
                        {"role": "user", "content": previous_message_str + "\n\n以下是原用户的聊天文本：" + str(content) + "\n\n**不要回答问题**请根据以上信息，以第一人称帮助用户**重新组织语言**:"}
                    ],
                    temperature=temperature
                )
                content = response.choices[0].message.content
                content = content.replace("@restate", "")
                logger.debug("AI回复：" + content) # 禁止AI回复@restate
                for single_response in content.split("\n"):
                    if single_response.strip() != "":
                        chat.SendMsg(single_response)
            elif "@ask" in content:
                STANDBY_MODE = False
                content = content.replace("@ask", "")
                logger.debug("收到@ask消息" + "content:" + content)
                previous_message_str = convert_chat_messages_to_str(chat.GetAllMessage())
                if len(previous_message_str) > 0:
                    previous_message_str = "以下是用户(self)和对方(friend)的之前发的消息：\n" + previous_message_str
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": previous_message_str + "\n\n以下是原用户的聊天文本：" + str(content) + "\n\n请根据以上信息，回答用户的问题:"}],
                    temperature=temperature
                )
                content = response.choices[0].message.content
                content = content.replace("@ask", "")
                logger.debug("AI回复：" + content) # 禁止AI回复@ask
                chat.SendMsg(content)
            else:
                if STANDBY_MODE and msgtype == "friend":
                    previous_message_str = convert_chat_messages_to_str(chat.GetAllMessage())
                    if len(previous_message_str) > 0:
                        previous_message_str = "以下是用户(self)和对方(friend)的之前发的消息：\n" + previous_message_str
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": "你的任务是友善的告知对方目前用户处于待机模式，请不要打扰用户。"},
                        {"role": "user", "content": previous_message_str + "\n\n以下是原用户的聊天文本：" + str(content) + "\n\n请用第一人称回复:"}
                    ],
                    temperature=temperature
                    )
                    content = response.choices[0].message.content
                    content = content.replace("@restate", "")
                    logger.debug("AI回复：" + content) # 禁止AI回复@restate
                    for single_response in content.split("\n"):
                        if single_response.strip() != "":
                            chat.SendMsg(single_response)
            if who == "文件传输助手" and msgtype == "self":
                if content.startswith("@command"):
                    content = content.replace("@command", "")
                    if "standby" in content.lower():
                        STANDBY_MODE = True
                    elif "active" in content.lower():
                        STANDBY_MODE = False
                    elif "switch" in content.lower():
                        STANDBY_MODE = not STANDBY_MODE
                    elif "status" in content.lower():
                        if STANDBY_MODE:
                            chat.SendMsg("当前处于待机模式")
                        else:
                            chat.SendMsg("当前处于激活模式")
                    logger.debug("收到@command消息" + "content:" + content)
                if content.startswith("@execute"):
                    content = content.replace("@execute", "")
                    output = subprocess.check_output(content.strip().split(" "))
                    chat.SendMsg(output.decode())
            # if msgtype == 'friend':
            #     chat.SendMsg('收到')  # 回复收到
        
        
    time.sleep(check_message_interval)









