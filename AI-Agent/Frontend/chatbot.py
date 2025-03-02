import chainlit as cl
import requests,re
from typing import Optional, List
from pydantic import BaseModel


API_URL = "http://localhost:8001/api/v1/assist"
API_URL_RESUME = "http://localhost:8001/api/v1/resume"
status = ""
thread_id = ""

class AssistantResponse(BaseModel):
    name: Optional[str]
    value: Optional[str]
    regex: Optional[str]
    
class State(BaseModel):
    input: Optional[str] = None
    response: Optional[str] = None
    response_debug: Optional[str] = None
    thread_id: Optional[str] = None
    assistantType: Optional[str] = None
    assistantResponseName: Optional[str] = None
    assistantResponse: Optional[List[AssistantResponse]] = None
    
state = State()

def getRegexValue(state):
    assistant_response_name = state['assistantResponseName']
    matching_response = next((item for item in state['assistantResponse'] if item['name'] == assistant_response_name), None)
    return matching_response

def updateState(state,updated_response):
    assistant_response_name = state['assistantResponseName']
    response_index = next((index for index, item in enumerate(state['assistantResponse']) if item['name'] == assistant_response_name), None)
    if response_index is not None:
        state['assistantResponse'][response_index] = updated_response
    return state
@cl.on_message
async def on_message(message: cl.Message):
    global status, thread_id, state    
    if status == "interrupted":
        assistantResponse = getRegexValue(state)   
        print(assistantResponse)
        regex = assistantResponse['regex']
        if not re.match(regex, message.content):
            await cl.Message(content="❌ "+assistantResponse['regexFailure']).send()
            return
        assistantResponse['value'] = message.content
        state = updateState(state,assistantResponse)
        state['thread_id'] = thread_id
        response = resume_chat(state)   
    else:
     response = get_chat_response(message.content)
    
    if isinstance(response, dict):
        if response.get("status") == "completed":
          await cl.Message(content=response.get("message").get("response_debug")).send()
          await cl.Message(content=response.get("message").get("response")).send()
          state = response.get("message")
          status = response.get("status", "")
          thread_id = response.get("thread_id", "")
        else:
          state = response.get("message")
          status = response.get("status", "")
          thread_id = response.get("thread_id", "")
          await cl.Message(content=response.get("message").get("response")).send()
    else:
        await cl.Message(content=response).send()

def get_chat_response(user_input: str):
    global status
    try:
        response = requests.post(API_URL, json={"prompt": user_input})
        print(response)
        if response.status_code == 200:
            json_response = response.json()
            return json_response
        else:
            return "Error: Unable to fetch response from the chatbot API."
    except Exception as e:
        return f"Error: {str(e)}"
    
def resume_chat(state: State):
    global status
    try:
        response = requests.post(API_URL_RESUME, json=state)
        if response.status_code == 200:
            json_response = response.json()
            return json_response
        else:
            return "Error: Unable to fetch response from the chatbot API."
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    cl.run()
