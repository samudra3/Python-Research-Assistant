from langgraph.graph import StateGraph,MessagesState,START,END
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Annotated
from langchain_tavily import TavilySearch
from langchain_core.messages import ToolMessage
from dotenv import load_dotenv
import json
load_dotenv()
def merge_evidence(existing,new):
      return existing+new
class State(MessagesState):
      research_evidence: Annotated[list[dict],merge_evidence]

llm = ChatGoogleGenerativeAI(
      model="gemini-3.1-flash-lite"
)
search_tool= TavilySearch(
      name="web-search",
      description="search the web for the relevant contents to answer the query",
      max_results=3
)
@tool
def synthesize_evidence():
      """
      when you find enough of the evidence and you don't need to search any further, then you should call
      this tool to syntesize the finding and generate the final answer.
      Don't call it before the proper searching or finding.
      """
      return "synthesize evidence"
llm_with_tools= llm.bind_tools([search_tool,synthesize_evidence])
tools=ToolNode([search_tool])
def call_model(state:State):
      print("before the invoking ai")
      response= llm_with_tools.invoke(state["messages"])
      print("after response")
      return {
            "messages":[response]
      }
def router(state:State):
      message=state["messages"][-1]

      if not message.tool_calls:

            return "end"
      for tool_calls in message.tool_calls:
            if tool_calls["name"] == "synthesize_evidence":
                  return "synthesize"
      return "tools"
def collect_evidence(state:State):
      message=state["messages"][-1]
      if message.name=="web-search":
            evidence=json.loads(message.content)
            research_evidence=[]
            for item in evidence["results"]:
                  collect={
                        "url":item["url"],
                        "title":item["title"],
                        "snippet":item["content"]
                  }
                  research_evidence.append(collect)

            return {
                  "research_evidence":research_evidence
            }
      return {}
def synthesize_node(state:State):
      message= state["messages"][-1]
      evidence= json.dumps(state["research_evidence"])
      synthesize_messsage= next(
            call for call in message.tool_calls
            if call["name"]=="synthesize_evidence"
      )
      tool_call_id=synthesize_messsage["id"]
      tool_message= ToolMessage(
            name="synthesize_evidence",
            content=evidence,
            tool_call_id=tool_call_id
      )
      return {
            "messages":[tool_message]
      }
builder=StateGraph(State)
builder.add_node("call_model",call_model)
builder.add_node("tools",tools)
builder.add_node("collect_evidence",collect_evidence)
builder.add_node("synthesize_node",synthesize_node)
builder.add_edge("tools","collect_evidence")
builder.add_edge(START,"call_model")
builder.add_conditional_edges("call_model",router,{
      "tools":"tools",
      "end":END,
      "synthesize":"synthesize_node"
})
builder.add_edge("collect_evidence","call_model")
builder.add_edge("synthesize_node","call_model")
graph= builder.compile()
result=graph.invoke({
      "messages":[
            {
                  "role":"user",
                  "content":"""
- Use web_search when more information is needed.
- Call synthesize_evidence when sufficient evidence has been gathered.
- After receiving the evidence from synthesize_evidence, write the final answer using that evidence.
- Do not call synthesize_evidence again for the same research task.
- Cite the relevant source URLs and distinguish supported facts from uncertainty.

Question: who is the best characters in Attack of Titan Anime?
"""
            }
      ]
})
print(result["messages"][-1])
# for item in result["research_evidence"]:
#       print(item["title"])
#       print(item["url"])
#       print(item["snippet"])
#       print("-"*40)

# result= search_tool.invoke({"query":"coomand to see desktop envrionment in linux"})
# print(result)
# class ResearchAssitant(TypedDict):
#       question:str
#       research_notes:list[str]
#       answer:str

# def research_node(state:ResearchAssitant):
#       return {
#             "research_notes":["it is a pipeline"]
#       }
# def analysis_node(state:ResearchAssitant):
#       return {
#             "answer":"it is a pipeline or a sequence of steps"
#       }
# def answer_node(state:ResearchAssitant):
#       return state
