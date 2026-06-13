import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

# 会话标识
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def session_save():
    if st.session_state.curren_session:
        session_data = {
            "session_id": st.session_state.curren_session,
            "messages": st.session_state.messages,
            "girlfriend_name": st.session_state.girlfriend_name,
            "girlfriend_character": st.session_state.girlfriend_character,
        }
    if not os.path.exists("session"):
        os.makedirs("session")
    # 保存会话数据
    with open(f"session/{st.session_state.curren_session}.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

# 加载所有的会话列表信息
def load_session_list():
    session_list = []
    if os.path.exists("session"):
        file_list = os.listdir("session")
        for file in file_list:
            if file.endswith(".json"):
                session_list.append(file[:-5])
    session_list.sort(reverse=True)
    return session_list

# 加载会话
def load_session(session_name):
    try:
        if os.path.exists(f"session/{session_name}.json"):
            with open(f"session/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
            st.session_state.messages = session_data["messages"]
            st.session_state.girlfriend_name = session_data["girlfriend_name"]
            st.session_state.girlfriend_character = session_data["girlfriend_character"]
            st.session_state.curren_session = session_name
    except Exception as e:
        st.error(f"加载会话失败: {e}")

# 删除会话
def delete_session(session_name):
    try:
        if os.path.exists(f"session/{session_name}.json"):
            os.remove(f"session/{session_name}.json")
            if session_name == st.session_state.curren_session:
                st.session_state.messages = []
                st.session_state.curren_session = generate_session_name()
    except Exception as e:
        st.error(f"删除失败: {e}")

client = OpenAI(
    api_key = os.getenv("api_key"),
    base_url=os.getenv("base_url"),
)

st.set_page_config(
    page_title="AI伴侣",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
    }
)


st.title("AI伴侣")
st.logo("👾")
if "messages" not in st.session_state:
    st.session_state.messages = []
if "girlfriend_name" not in st.session_state:
    st.session_state.girlfriend_name = "姜凌仙"
if "girlfriend_character" not in st.session_state:
    st.session_state.girlfriend_character = "温柔贤淑、外冷内热、古风古色的御姐"
if "curren_session" not in st.session_state:
    st.session_state.curren_session = generate_session_name()

st.text(f"当前会话:{st.session_state.curren_session}")

for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

system_prompt = """
    你叫%s,现在是用户的真实伴侣，请完全带入伴侣角色。
    规则：
        1.每次只回1条消息
        2.禁止任何场景或状态描述性文字
        3.匹配用户的语言
        4.回复简洁，像微信聊天一样
        5.有需要的化可以用emoji表情
        6.用符合伴侣性格的方式对话
        7.回复的内容，要充分体现伴侣性格特征
    伴侣性格：
        %s
    你必须严格遵守上述规则来回复用户
"""

# 左侧侧边栏
with st.sidebar:
    st.subheader("AI控制面板")
    if st.button("开始新的对话", width="stretch", icon="✏️"):
        # 保存会话信息
        if st.session_state.messages:
            session_save()
        # 创建新的会话
        if st.session_state.messages:
            st.session_state.curren_session = generate_session_name()
            st.session_state.messages = []
            session_save()
            st.rerun()

    st.text("历史会话")
    session_list = load_session_list()
    for session in session_list:
        coli, col2 = st.columns([4, 1])
        with coli:
            if st.button(session, width="stretch", key=f"load_{session}", icon="📝",type="primary" if session == st.session_state.curren_session else "secondary"):
                load_session(session)
                st.rerun()
        with col2:
            if st.button("", width="stretch", key=f"delete_{session}", icon="❌"):
                delete_session(session)
                st.rerun()

    # 加载分割线
    st.divider()

    st.subheader("伴侣信息")
    girlfriend_name = st.text_input("名字", placeholder="请输入伴侣的名字", value=st.session_state.girlfriend_name)
    if girlfriend_name:
        st.session_state.girlfriend_name = girlfriend_name
    girlfriend_character = st.text_area("性格", placeholder="请输入伴侣性格", value=st.session_state.girlfriend_character)
    if girlfriend_character:
        st.session_state.girlfriend_character = girlfriend_character




# 对话框
prompt = st.chat_input("请输入对话")
if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="qwen3.7-plus",
        messages=[
            {"role": "system", "content": system_prompt % (st.session_state.girlfriend_name, st.session_state.girlfriend_character)},
            *st.session_state.messages,
        ],
        stream=True
    )
    response_messages = st.empty()  # 创建一个空的消息框
    full_response = ""
    for chunk in response:
        if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            response_messages.chat_message("assistant").write(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    session_save()