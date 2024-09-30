import time
import openai
import streamlit as st
import requests
pip install python-dotenv
# OpenAI 클라이언트 설정
openai_client = openai

# 상수 정의
PAGE_TITLE = "전화통화 to Data (AI상상력)"
PAGE_DESCRIPTION = "주선사와 차주가 통화 파일을 업로드해주세요"

def setup_page():
    """Streamlit 페이지 설정 함수"""
    st.set_page_config(page_title=PAGE_TITLE, page_icon=":speech_balloon:")
    st.title(PAGE_TITLE)
    

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

def initialize_session_state():
    """세션 상태를 초기화하는 함수"""
    if "thread_id" not in st.session_state:
        thread = openai_client.beta.threads.create()
        st.session_state.thread_id = thread.id
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "first_message_shown" not in st.session_state:  # 속성을 초기화
        st.session_state.first_message_shown = False  # 플래그를 False로 초기화
    if "voice_result" not in st.session_state:
        st.session_state.voice_result = None  # 음성 인식 결과를 저장할 공간
    if "gpt_response_complete" not in st.session_state:
        st.session_state.gpt_response_complete = False  # GPT 응답이 완료되었는지 추적하는 플래그

def display_chat_history():
    """채팅 기록을 표시하는 함수"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def get_user_input():
    """사용자 입력을 받는 함수"""
    return st.chat_input("채팅을 입력해주세요.")

def add_user_message(prompt):
    """사용자 메시지를 추가하고 표시하는 함수"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

def send_message_to_thread(prompt):
    """OpenAI 스레드에 메시지를 보내는 함수"""
    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

def create_assistant_run():
    """OpenAI 어시스턴트 실행을 생성하는 함수"""
    return openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=ASSISTANT_ID,
        stream=True
    )

def process_stream(stream):
    """스트림을 처리하고 메시지를 표시하는 함수"""
    placeholder = st.empty()
    full_response = ""
    for chunk in stream:
        if chunk.event == "thread.message.delta":
            if hasattr(chunk.data, 'delta') and hasattr(chunk.data.delta, 'content'):
                content_delta = chunk.data.delta.content[0].text.value
                full_response += content_delta
                placeholder.markdown(full_response + "▌")
    placeholder.markdown(full_response)
    return full_response

def process_voice_to_text(uploaded_file):
    """MP3 파일을 음성 인식 API로 전송하고 결과를 반환하는 함수"""
 

    # STT API 요청 URL
    url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor"

    # 요청 헤더 설정
    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
        "Content-Type": "application/octet-stream"
    }

    # 업로드된 파일을 바이너리 모드로 읽기
    audio_data = uploaded_file.read()

    # STT API 요청 보내기
    response = requests.post(url, headers=headers, data=audio_data)

    # API 요청 결과 처리
    if response.status_code == 200:
        result = response.json()
        return result.get('text', '결과 없음')
    else:
        return f"오류 발생: {response.status_code}"

def add_custom_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

def main():
    """메인 함수"""
    initialize_session_state()
    setup_page()
    st.subheader("①통화 파일을 업로드 해주세요")

    uploaded_file = st.file_uploader("MP3 파일 업로드", type="mp3")
    
    # 파일이 업로드되고 음성 인식 결과가 아직 없다면 처리
    if uploaded_file is not None:
        # 음성 파일 업로드 후 두 번째 메시지가 실행되지 않도록 방지
        if not st.session_state.first_message_shown:
            st.subheader("②업로드 후 잠시 기다려주세요")
            st.session_state.voice_result = process_voice_to_text(uploaded_file)  # 음성 인식 결과 저장

            # 음성 인식 결과를 첫 메시지로 추가하고 어시스턴트와 상호작용
            if st.session_state.voice_result:  # 중복 방지 조건 추가
                text = st.session_state.voice_result
                add_user_message(text)
                send_message_to_thread(text)

                # 어시스턴트 응답 처리
                with st.chat_message("assistant"):
                    stream = create_assistant_run()
                    full_response = process_stream(stream)

                st.session_state.messages.append({"role": "assistant", "content": full_response})

                # 메시지가 한 번 실행되었음을 기록하여 중복 방지
                st.session_state.first_message_shown = True
                st.session_state.gpt_response_complete = True  # GPT 응답 완료 상태 설정
    
    # GPT 응답 완료 이후에만 표시
    if st.session_state.gpt_response_complete:
        st.subheader("③통화내용이 성공적으로 반영되었습니다.")

    # # 채팅 기록을 표시
    # display_chat_history()
    
    # 사용자가 채팅 입력을 추가로 할 수 있도록 처리
    if prompt := get_user_input():
        add_user_message(prompt)
        send_message_to_thread(prompt)

        # 어시스턴트 응답 처리
        with st.chat_message("assistant"):
            stream = create_assistant_run()
            full_response = process_stream(stream)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()
