import wxauto
import pyautogui as pg
import openai
import time
from tqdm import tqdm
import os
import json
import logging
import subprocess
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_base_url = "http://127.0.0.1:18000/v1/"
api_key = "lm-studio-api-key"
model = "deepseek-r1-distill-qwen-7b"
temperature = 0.4
client = openai.OpenAI(base_url=openai_base_url, api_key=api_key)

# secret = json.load(open("secret.json", "r"))
# base_url = secret.get("base_url")
# api_key = secret.get("api_key")
# model = secret.get("model")
# client = openai.OpenAI(base_url=base_url, api_key=api_key)

white_list = ["李东荣","胡运心","文件传输助手"]
check_message_interval = 1
commmand_keywords = ["@restate", "@ask", "@command", "@execute"]

STANDBY_MODE = True


# Do not need to cut COT anymore, lm studio will separate the think and return content automatically
# def cot(content:str, think_start = "<think>", think_end = "</think>", return_think_content = False):
#     # 当使用cot模型时，content中会包含<think>和</think>，用于分割出思考内容和回复内容
#     think_content = content.split(think_start)[1].split(think_end)[0]
#     if return_think_content:
#         return think_content, content.split(think_end)[1]
#     else:
#         return content.split(think_end)[1]

def convert_chat_messages_to_str(list_of_messages:list):
    chat_history = ""
    for one_message in list_of_messages:
        chat_history += f'{str(one_message.type)}说：{str(one_message.content)}\n'
    return chat_history

def creat_response(content:str, chat, system_prompt:str, user_prompt:str):
    # strip control characters
    for command in commmand_keywords:
        if command in content:
            content = content.replace(command, "")
    
    # gather previous messages
    previous_message_str = convert_chat_messages_to_str(chat.GetAllMessage())
    if len(previous_message_str) > 0:
        previous_message_str = "以下是用户(self)和对方(friend)的之前发的消息：\n" + previous_message_str + "\n\n"
    
    # create system prompt if it is not empty
    if system_prompt != "":
        messages = [{"role": "system", "content": system_prompt}]
    else:
        messages = []
    messages.append({"role": "user", "content": previous_message_str + "以下是原用户的聊天文本：" + str(content) + "\n\n" + user_prompt})
    
    # create response
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        content = response.choices[0].message.content
        
        # strip control characters
        for command in commmand_keywords:
            if command in content:
                content = content.replace(command, "")
        time.sleep(15)
        
        # send response in multiple messages
        for single_response in content.split("\n"):
            time.sleep(len(single_response) / 100)
            if single_response.strip() != "":
                chat.SendMsg(single_response)
        logger.debug("AI回复：" + content)
        
        return content
    
    except Exception as e:
        # send error message if error occurs
        logger.error(f"处理@restate消息时发生错误: {e}")
        chat.SendMsg(str(e))
        return str(e)

def main():
    global STANDBY_MODE
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
                    system_prompt = "你的任务是帮助有语言障碍的用户使用幽默和不冒犯的语言风格**重新组织语言**，**不要回答问题**，使用\n分割多条消息。"
                    user_prompt = "\n\n**不要回答问题**请根据以上信息，以第一人称帮助用户**重新组织语言**:"
                    creat_response(content, chat, system_prompt, user_prompt)
                elif "@ask" in content:
                    STANDBY_MODE = False
                    user_prompt = "请根据以上信息，回答用户的问题:"
                    creat_response(content, chat, "", user_prompt)
                elif who == "文件传输助手" and msgtype == "self":
                    if content.startswith("@command"):
                        content = content.replace("@command", "")
                        logger.debug("收到@command消息" + "content:" + content)
                        if "standby" in content.lower():
                            STANDBY_MODE = True
                        elif "active" in content.lower():
                            STANDBY_MODE = False
                        elif "switch" in content.lower():
                            STANDBY_MODE = not STANDBY_MODE
                        elif "status" in content.lower() or "stats" in content.lower():
                            if STANDBY_MODE:
                                chat.SendMsg("当前处于猫娘代理回复模式")
                            else:
                                chat.SendMsg("当前处于手动回复模式")
                        elif "restart" in content.lower():
                            raise Exception("重启程序")
                    elif content.startswith("@execute"):
                        content = content.replace("@execute", "")
                        try:
                            output = subprocess.check_output(content.strip().split(" "))
                            chat.SendMsg(output.decode())
                        except Exception as e:
                            logger.error(f"执行命令时发生错误: {e}")
                            # traceback.print_exc()
                            chat.SendMsg(f"执行命令时发生错误: {e}")
                            time.sleep(1)
                            chat.SendMsg(traceback.format_exc())
                else:
                    if STANDBY_MODE and msgtype == "friend":
                        system_prompt = "你是一只猫娘，请用第一人称回复，并在回复中使用猫娘的语气，使用'喵~'作为结尾:"
                        user_prompt = "你是一只可爱的猫娘，请用温柔甜美的语气回复消息，并告诉主人你会帮忙转达，等主人有空时会亲自回复喵~"
                        creat_response(content, chat, system_prompt, user_prompt)
                
                # if msgtype == 'friend':
                #     chat.SendMsg('收到')  # 回复收到
            
            
        time.sleep(check_message_interval)


if __name__ == "__main__":
    timeout = 1
    while True:
        try:
            main()
        except KeyboardInterrupt:
            logger.info("程序被手动终止")
            break
        except Exception as e:
            logger.error(f"程序发生错误: {e}")
            traceback.print_exc()
            time.sleep(timeout)
            timeout *= 2 # 指数增加, 避免频繁重试
            logger.info(f"程序发生错误，{timeout}秒后重试")






