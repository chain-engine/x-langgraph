from typing import TypedDict

from langgraph.graph import StateGraph


class HelloState(TypedDict):
    message: str


# 定义节点
def start(_state: HelloState) -> HelloState:
    return {"message": "Hello, LangGraph!"}


def end(state: HelloState) -> HelloState:
    print(state["message"])
    return state


# 创建一个简单的工作流（StateGraph 是构建器，需要先 compile）
builder = StateGraph(HelloState)
builder.add_node("start", start)
builder.add_node("end", end)
builder.add_edge("start", "end")
builder.set_entry_point("start")
graph = builder.compile()


# 运行工作流
if __name__ == "__main__":
    print("Running LangGraph hello world example...")
    graph.invoke({"message": ""})
    print("Example completed successfully!")
