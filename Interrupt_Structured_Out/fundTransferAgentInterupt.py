#from langchain_ollama import ChatOllama
from typing import Optional,List
from pydantic import BaseModel, Field
from enum import Enum
#from typing import List
#from langchain_deepseek import ChatDeepSeek
from langchain.chat_models import init_chat_model
import os
from fastapi import FastAPI,HTTPException
import uvicorn 
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
import uuid
import requests

class PromptRequest(BaseModel):
    prompt: str
    thread_id: Optional[str] = None
    
class PromptRequestResume(BaseModel):
    prompt: str
    thread_id: str
    
thread_store = {}

class AssistantType(Enum):
    """
    Enum class for different categories of fund transfer requests. 
    """
    GET_FUNDTRANSFER = "getFundTransfer"
    CREATE_FUNDTRANSFER = "createFundTransfer"
    UNPREDICTABLE = "Unpredictable"

class AssistantSelection(BaseModel):
    """
You are an assistant selection model. You must categorize the user request into one of the following categories based on the content of the request. Use the categories below to classify the request.

1. **Get Funding Transfer Details** (GET_FUNDTRANSFER):Retrieve details of a funding transfer, including latest status, by using the transfer ID that was returned when you created the transfer.
2. **Create Funding Transaction** (CREATE_FUNDTRANSFER): Create a funding transfer (Funding Transaction) to secure funds from a sending account (Funding Account).
3. **Unpredictable Assistant** (UNPREDICTABLE): This assistant is used if the system cannot determine a clear match with any of the above categories. This can be a general inquiry or an ambiguous request.
   - Example queries:
     - "Tell me about the weather."
     - "I don't know what I need help with."
"""

    selectedAssistant: AssistantType = Field(
        description="suitable service depending on user's intent"
    )
    

class CreateFundTransferAssistant(BaseModel):
    """
    Create Funding Transaction Assistant Model.
    This model is designed to assist in extracting and validating the necessary information 
    It ensures the input provided by the user is in the correct format for partnerId, amount, currency, sender_account_uri, recipient_account_uri, statement_descriptor.
    This model validates the format of these inputs and ensures the user provides the required data.
    """

    partnerId: Optional[str] = Field(
        default=None, 
        description="The Mastercard-assigned unique ID for the partner registered to use Mastercard Send",
    )

    amount: Optional[str] = Field(
        default=None, 
        description="numerical value should be greater than 1.0",
    )

    currency: Optional[str] = Field(
        default=None, 
        description="currency of the amount",
    )
    sender_account_uri: Optional[str] = Field(
        default=None, 
        description="account uri of the sender",
    )

    recipient_account_uri: Optional[str] = Field(
        default=None, 
        description="account uri of the receipient",
    )

    statement_descriptor: Optional[str] = Field(
        default=None, 
        description="Transaction statement display text",
    )
  
class GetFundTransferAssistant(BaseModel):
    """
    Get Fund Transfer Assistant model for retrieving the details of funding transfer. 
    This model extracts and validates the necessary information for retrieving the details of funding transfer.
    It ensures the input provided by the user is in the correct format for partnerId, transferId and if user is not send do not pre-fill the values.
    """

    partnerId: Optional[str] = Field(
        default=None, 
        description="Unique ID for the partner registered to use Mastercard.",
    )
    transferId: Optional[str] = Field(
        default=None, 
        description="Id to track the fund transfer",
    )
    
class AssistantResponse(BaseModel):
    name: Optional[str]
    value: Optional[str]
    regex: Optional[str]
    regexFailure: Optional[str]
    
class State(BaseModel):
    input: Optional[str] = None
    response: Optional[str] = None
    thread_id: Optional[str] = None
    assistantType: Optional[AssistantType] = None
    assistantResponseName: Optional[str] = None
    assistantResponse: Optional[List[AssistantResponse]] = None
    
checkpointer = MemorySaver()
def create_graph():
    workflow = StateGraph(State)

    def find_assistant_node(state: State):
      if(state.assistantType == AssistantType.GET_FUNDTRANSFER):
         return "getfundagent"
      elif(state.assistantType == AssistantType.CREATE_FUNDTRANSFER):
         return "createfundagent"
      else:
         return "END"
     
    def getfundagent(state: State):   
        if(state.assistantResponse[0].value == None):
            state.response = "Please provide your partner Id"
            state.assistantResponseName = "partnerId"
            state = interrupt(state)
            state = state
        if(state.assistantResponse[1].value == None):
            print("Interuppt should be called")
            state.response = "Please provide your transfer Id"    
            state.assistantResponseName = "transferId" 
            state = interrupt(state)
            state = state
        partner_id = state.assistantResponse[0].value
        transfer_id = state.assistantResponse[1].value
        url = f"http://localhost:3000/v1/partners/{partner_id}/transfers/{transfer_id}"
        try:
         response = requests.get(url)
         response.raise_for_status() 
         id = response.json().get("transfer").get("id")
         transfer_amount = response.json().get("transfer").get("transfer_amount").get("value")
         agent_response = f"Your transfer transaction (ID: {id}) has been successfully approved! 🎉 The payment of {transfer_amount} USD was sent via MasterCard from John Tyler Jones to John Tyler Jones. The transaction was processed as a P2P debit transfer with authorization ID 49DX93. It was initiated on March 18, 2015, at 14:18:55 UTC through the web channel using device DEV123456. The statement descriptor for this transaction is 'THANKYOU.' Let me know if you need any further details!";
         state.response = agent_response
        except requests.exceptions.RequestException as e:
         state.response = f"Error fetching data: {str(e)}"
        return state
    
    def createfundagent(state: State):
        if(state.assistantResponse[0].value == None):
            state.response = "Please provide your partner Id"
            state.assistantResponseName = "partnerId"
            state = interrupt(state)
            state = state
        if(state.assistantResponse[1].value == None):
            print("Interuppt should be called")
            state.response = "Please enter your amount to be pulled"    
            state.assistantResponseName = "amount" 
            state = interrupt(state)
            state = state 
        if(state.assistantResponse[2].value == None):
            state.response = "Please enter the currency of the amount (USD,INR,AED)"
            state.assistantResponseName = "currency"
            state = interrupt(state)
            state = state
        if(state.assistantResponse[3].value == None):
            print("Interuppt should be called")
            state.response = "Please enter the sender account uri"    
            state.assistantResponseName = "sender_account_uri" 
            state = interrupt(state)
            state = state    
        if(state.assistantResponse[4].value == None):
            state.response = "Please enter the recipient acoount uri"
            state.assistantResponseName = "recipient_account_uri"
            state = interrupt(state)
            state = state
        if(state.assistantResponse[5].value == None):
            print("Interuppt should be called")
            state.response = "Please enter the statement descriptor"    
            state.assistantResponseName = "statement_descriptor" 
            state = interrupt(state)
            state = state   
        confirm_message = f"❗ You are initiating the fund transfer from {state.assistantResponse[3].value} to {state.assistantResponse[4].value} with amount of {state.assistantResponse[1].value} {state.assistantResponse[2].value} and please enter yes to confirm and proceed with the transfer"
        print("Interuppt should be called")
        state.response = confirm_message
        state.assistantResponseName = "confirm_message" 
        state = interrupt(state)
        state = state 
        if(state.assistantResponse[6].value == "yes"):
         partner_id = state.assistantResponse[0].value   
         url = f"http://localhost:3000/v1/partners/{partner_id}/transfers/funding"
         print(url)
         try:
          response = requests.post(url, json={})
          ref = response.json().get("transfer").get("id")
          agent_response = f"Your funding transfer has been successfully created! The requested funds have been secured from the designated funding account, ensuring a smooth and secure transaction.Please use the transfer reference for more details {ref}"
          state.response = agent_response
         except requests.exceptions.RequestException as e:
          state.response = f"Error fetching data: {str(e)}"
          print(state)
         return state
        else:
          state.response = "The fund Transfer is rejected"
          return state
        
    workflow.add_node("getfundagent", getfundagent)
    workflow.add_node("createfundagent", createfundagent)
    workflow.add_conditional_edges(START,find_assistant_node)

    return workflow.compile(checkpointer=checkpointer)

appServer = FastAPI()
    
class ServiceExtractor:
    def __init__(self):
        os.environ["OPENAI_API_KEY"] = ""
        self.llm = init_chat_model("gpt-4o", model_provider="openai",temperature=0)
       # self.llm = ChatOllama(model="llama3.3",temperature=0)

    def extract_service_intent(self, user_prompt: str) -> dict:
        # Define structured output for different services
        structured_llm = self.llm.with_structured_output(AssistantSelection ,method="json_schema")
  
        try:
            # Invoke the LLM to process the prompt and extract the relevant service intent and arguments
            result = structured_llm.invoke(user_prompt)
            # Construct and return the final response
            if result.selectedAssistant==AssistantType.CREATE_FUNDTRANSFER:
             assitant_llm = self.llm.with_structured_output(CreateFundTransferAssistant ,method="json_schema")
             llm_result = assitant_llm.invoke(user_prompt)
             response = [
                     {
                     "name":"partnerId",
                     "value":llm_result.partnerId,
                     "regex": "^.{32}$",
                     "regexFailure": "Please enter the proper partnerId"
                 },
                 {
                     "name":"amount",
                     "value":llm_result.amount,
                     "regex": "^\d+(\.\d{1,2})?$",
                     "regexFailure": "Please enter the valid amount"
                 },
                     {
                     "name":"currency",
                     "value":llm_result.currency,
                     "regex": "^.{3}$",
                     "regexFailure": "Please enter the valid currency"
                 },
                 {
                     "name":"sender_account_uri",
                     "value":llm_result.sender_account_uri,
                     "regex": "^.{40}$",
                     "regexFailure": "Please enter the proper sender account uri"
                 },  
                {
                     "name":"recipient_account_uri",
                     "value":llm_result.recipient_account_uri,
                     "regex": "^.{40}$",
                     "regexFailure": "Please enter the proper recipient account uri"
                 },
                 {
                     "name":"statement_descriptor",
                     "value":llm_result.statement_descriptor,
                     "regex": "^.{0,999}$",
                     "regexFailure": "Please enter the proper statement descriptor"
                 },
                 {
                     "name":"confirm_message",
                     "value":llm_result.recipient_account_uri,
                     "regex": "^(yes|no)$", 
                     "regexFailure": "Please enter the proper confirm message"
                 }                            
                ]
             
            elif result.selectedAssistant==AssistantType.GET_FUNDTRANSFER:
             assitant_llm = self.llm.with_structured_output(GetFundTransferAssistant ,method="json_schema")
             llm_result = assitant_llm.invoke(user_prompt)    
             response = [
                     {
                     "name":"partnerId",
                     "value":llm_result.partnerId,
                     "regex": "^.{32}$",
                     "regexFailure": "Please enter the proper partnerId"
                 },
                 {
                     "name":"transferId",
                     "value":llm_result.transferId,
                     "regex": "^.{24}$",
                      "regexFailure": "Please enter the proper transferId"
                 },
                          
                ]      
            else:
             response = {
                 "status": "error",
                 "message": "Unable to find the assistant"
             }
            state = State(input=user_prompt,assistantType=result.selectedAssistant,assistantResponse=response)
            return state
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
                 }

@appServer.post("/api/v1/assist")
async def respond_with_prompt(request: PromptRequest):
    extractor = ServiceExtractor()
    state = extractor.extract_service_intent(request.prompt)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    graph = create_graph()
    for chunk in graph.stream(state,config):
              if "__interrupt__" in chunk:
               thread_store[thread_id] = {
                    "status": "interrupted",
                    "input": request.prompt
                 }
               return {
                 "status": "interrupted",
                 "thread_id": thread_id,
                 "message": chunk["__interrupt__"][0].value,
                 }
    return state

@appServer.post("/api/v1/resume")
async def resume_graph(state: State):
    if state.thread_id not in thread_store:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Create the graph
    graph = create_graph()
    
    # Configuration for the specific thread
    config = {"configurable": {"thread_id": state.thread_id}}
    try:
        for chunk in graph.stream(Command(resume=state), 
            config, 
            stream_mode="values"
        ):
            # Check for completion
            if chunk.get("response"):
                # Clear the thread store
                del thread_store[state.thread_id]
                return {
                 "status": "completed",
                 "message": state,
                 }
        
        # If interrupted again
        return {
                 "status": "interrupted",
                 "thread_id": state.thread_id,
                 "message": state
                 }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@appServer.get("/api/v1/thread/{thread_id}")
async def check_thread_status(thread_id: str):
    thread_info = thread_store.get(thread_id)
    if not thread_info:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return {
        "thread_id": thread_id,
        "status": thread_info.get("status", "unknown")
    }
        
if __name__ == "__main__":
    uvicorn.run(appServer, host="0.0.0.0", port=8001)