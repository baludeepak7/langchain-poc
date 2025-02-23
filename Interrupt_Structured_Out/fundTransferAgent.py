#from langchain_ollama import ChatOllama
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
#from typing import List
#from langchain_deepseek import ChatDeepSeek
from langchain.chat_models import init_chat_model
import os
from fastapi import FastAPI  
import uvicorn 
from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

appServer = FastAPI()

class State(TypedDict):
   """The graph state."""
   some_text: str
   
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
    It ensures the input provided by the user is in the correct format for partnerId, transferId.
    """

    partnerId: Optional[str] = Field(
        default=None, 
        description="The Mastercard-assigned unique ID for the partner registered to use Mastercard Send. String, length 32.",
    )
    transferId: Optional[str] = Field(
        default=None, 
        description="The system-generated Transfer ID (id) that was returned when you created the funding transfer. Alphanumeric and * , - . _ ~.",
    )
    
# The ServiceExtractor class will handle different service extraction logic
class ServiceExtractor:
    def __init__(self):
        os.environ["OPENAI_API_KEY"] = ""
        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")
       # self.llm = ChatOllama(model="llama3.3",temperature=0)

    def extract_service_intent(self, user_prompt: str) -> dict:
        # Define structured output for different services
        structured_llm = self.llm.with_structured_output(AssistantSelection ,method="json_schema")

        try:
            # Invoke the LLM to process the prompt and extract the relevant service intent and arguments
            result = structured_llm.invoke(user_prompt)
            print(result)
            # Construct and return the final response
            if result.selectedAssistant==AssistantType.CREATE_FUNDTRANSFER:
             assitant_llm = self.llm.with_structured_output(CreateFundTransferAssistant ,method="json_schema")
             llm_result = assitant_llm.invoke(user_prompt)
             response = {
                 "status": "Success",
                 "message": "Parameters retrieved Successfully for CreateFundTransferAssistant",
                "parameters":[
                     {
                     "name":"partnerId",
                     "value":llm_result.partnerId
                 },
                 {
                     "name":"amount",
                     "value":llm_result.amount
                 },
                     {
                     "name":"currency",
                     "value":llm_result.currency
                 },
                 {
                     "name":"sender_account_uri",
                     "value":llm_result.sender_account_uri
                 },  
                {
                     "name":"recipient_account_uri",
                     "value":llm_result.recipient_account_uri
                 },
                 {
                     "name":"statement_descriptor",
                     "value":llm_result.statement_descriptor
                 }                               
                ]
             }
            elif result.selectedAssistant==AssistantType.GET_FUNDTRANSFER:
             assitant_llm = self.llm.with_structured_output(GetFundTransferAssistant ,method="json_schema")
             llm_result = assitant_llm.invoke(user_prompt)
             response = {
                 "status": "Success",
                 "message": "Parameters retrieved Successfully for GetFundTransferAssistant",
                 "parameters":[
                     {
                     "name":"partnerId",
                     "value":llm_result.partnerId
                 },
                 {
                     "name":"transferId",
                     "value":llm_result.transferId
                 }
                               
                ]
             }
            else:
             response = {
                 "status": "error",
                 "message": "Unable to find the assistant"
             }
            print(llm_result)    
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
                 }

class PromptRequest(BaseModel):
    prompt: str
    
@appServer.post("/api/v1/assist")
async def respond_with_prompt(request: PromptRequest):
    extractor = ServiceExtractor()
    result = extractor.extract_service_intent(request.prompt)
    return result
if __name__ == "__main__":
    uvicorn.run(appServer, host="0.0.0.0", port=8000)