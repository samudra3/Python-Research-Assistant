# 🕵️ Python Research Assistant

> **An AI that researches the web by itself, takes notes, and then writes a cited answer.**
> Built with **LangGraph**, **Gemini** and **Tavily web search**, to show in the simplest form how an *AI agent* works.

---

## 📖 Table of Contents

1. [What is this project?](#-what-is-this-project)
2. [Normal chatbot vs. research agent](#-normal-chatbot-vs-research-agent)
3. [The big idea: an agent is a loop](#-the-big-idea-an-agent-is-a-loop)
4. [Key words explained simply](#-key-words-explained-simply)
5. [Project structure](#-project-structure)
6. [How the graph works, step by step](#-how-the-graph-works-step-by-step)
7. [Code walkthrough](#-code-walkthrough)
8. [A sample run, in plain English](#-a-sample-run-in-plain-english)
9. [How to run](#-how-to-run)
10. [Tech used](#-tech-used)
11. [Known limitations and ideas](#-known-limitations-and-ideas)

---

## 🎯 What is this project?

You ask a question, for example:

> *"Who are the best characters in Attack on Titan?"*

The assistant then:

1. **Decides** it needs to look things up
2. **Searches the web** (as many times as it thinks necessary)
3. **Saves** the useful findings (title, link, snippet) in a notebook
4. **Decides** when it has *enough* evidence
5. **Writes the final answer** using only that evidence, citing the source links and separating facts from uncertainty

The whole thing lives in one file: [`resAssistant.py`](resAssistant.py).

---

## 🆚 Normal chatbot vs. research agent

| Normal chatbot | This research agent |
|---|---|
| Answers from memory only | Searches the live web first |
| One question → one answer | One question → *think → search → think → search → answer* |
| Can't show where facts came from | Collects source URLs and cites them |
| May be out of date | Uses fresh search results |

**Analogy:** A normal chatbot is like a student answering an exam from memory. This project is like a student who is allowed to go to the library, **take notes**, and then write the essay with references.

---

## 🔁 The big idea: an agent is a loop

The key idea is that the AI is **not following a fixed script**. After every step, *the AI itself decides what to do next*:

```mermaid
flowchart TD
    A([▶ START: user question]) --> B[🧠 call_model<br/>AI thinks: what should I do next?]
    B --> C{🔀 router<br/>What did the AI ask for?}
    C -- "Search the web" --> D[🔎 tools<br/>Tavily web search]
    D --> E[📝 collect_evidence<br/>Save title, url, snippet]
    E --> B
    C -- "I have enough evidence" --> F[📦 synthesize_node<br/>Hand over all saved evidence]
    F --> B
    C -- "No tool needed, just answer" --> G([⏹ END: final answer])
```

Read it like a story:

- **🧠 The AI thinks** → *"I don't know enough. Let me search."*
- **🔎 Search runs** → results come back.
- **📝 Notes are saved** → back to the AI.
- **🧠 The AI thinks again** → *"Still need more"* → search again... or *"I have enough!"*
- **📦 Evidence is handed over** → the AI writes the final answer → **END**.

This *think → act → observe → think again* loop is the heart of what people call an **AI agent**.

---

## 🧰 Key words explained simply

| Term | Simple meaning | Where it is in the code |
|---|---|---|
| **LLM** (Large Language Model) | The "brain" that reads text and writes text. Here it is Google Gemini. | `llm = ChatGoogleGenerativeAI(...)` |
| **Tool** | An ability the AI can *choose* to use, like a search engine. The AI can't browse the web by itself, so we give it a tool. | `search_tool` (Tavily) and `synthesize_evidence` |
| **Tool calling** | The AI replying *"please run the search tool with this query"* instead of a normal text answer. | `llm.bind_tools([...])` |
| **Graph** | A flowchart made of boxes and arrows that describes the workflow. | `StateGraph(State)` |
| **Node** | One box in the flowchart: a small job done by a Python function. | `call_model`, `collect_evidence`, `synthesize_node`, `tools` |
| **Edge** | An arrow saying "after this box, go to that box". | `builder.add_edge(...)` |
| **Conditional edge / Router** | A *decision arrow*. A function looks at the situation and chooses which box comes next. | `router` + `add_conditional_edges` |
| **State** | A shared notebook that every node can read and write. | `class State(MessagesState)` |
| **Reducer** | A rule for *how new notes are merged* into the notebook (add to the list instead of replacing it). | `merge_evidence` |
| **Evidence** | The facts collected from the web: `url`, `title`, `snippet`. | `research_evidence` |

---

## 📁 Project structure

```
Python-Research-Assistant/
│
├── resAssistant.py      # The complete agent: tools, nodes, router, graph and a sample run
└── requirements.txt     # Python dependencies
```

---

## 🪜 How the graph works, step by step

### 🗒️ The State: the shared notebook
Every node reads from and writes to one shared **State**. It holds two things:

1. **`messages`**: the whole conversation (question, AI replies, tool results)
2. **`research_evidence`**: a list of everything useful found on the web

```python
class State(MessagesState):
    research_evidence: Annotated[list[dict], merge_evidence]
```

The `merge_evidence` reducer is a tiny rule: `existing + new`. Without it, each new search would **erase** the previous findings. With it, evidence **piles up** across searches. 📚

### 🧠 Node 1: `call_model`: *the thinker*
Sends the conversation so far to Gemini. Gemini answers with one of three things:

- 🔎 "Run a web search for ..." *(a tool call)*
- ✅ "I'm ready to wrap up: call `synthesize_evidence`" *(a special tool call)*
- 💬 A normal text reply with no tool *(the final answer)*

### 🔀 The `router`: *the decision-maker*
Looks at the AI's last message and picks the next box:

| AI's message contains | Router sends us to |
|---|---|
| No tool call at all | **END** (it's the final answer) |
| A `synthesize_evidence` call | **synthesize_node** |
| Any other tool call (search) | **tools** |

### 🔎 Node 2: `tools`: *the searcher*
Runs the **Tavily** web search and returns up to **3 results** per search (`max_results=3`).

### 📝 Node 3: `collect_evidence`: *the note-taker*
Takes the raw search results and keeps just three useful fields from each one: **url**, **title** and **snippet**. These are added to `research_evidence` in the State. Then control goes back to the thinker.

### 📦 Node 4: `synthesize_node`: *the hand-over*
When the AI says "I have enough", this node packages **all the saved evidence** and gives it back to the AI as a tool reply. The AI then reads all the notes at once and writes the final cited answer.

> 💡 **A neat trick:** `synthesize_evidence` doesn't do any real work. It is a *signal tool*. Calling it is just the AI's way of saying *"stop searching, I'm ready to write"*. The real work happens in `synthesize_node`.

---

## 🔬 Code walkthrough

| What you want to understand | Where to look in [`resAssistant.py`](resAssistant.py) |
|---|---|
| The shared notebook and the merge rule | `merge_evidence`, `class State` |
| The AI brain | `llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")` |
| The web search tool (3 results max) | `search_tool = TavilySearch(...)` |
| The "I'm done searching" signal | `@tool def synthesize_evidence()` |
| Giving the AI its tools | `llm.bind_tools([search_tool, synthesize_evidence])` |
| The thinker | `call_model(state)` |
| The decision logic | `router(state)` |
| The note-taker | `collect_evidence(state)` |
| The hand-over of evidence | `synthesize_node(state)` |
| Wiring nodes and arrows together | `builder = StateGraph(State)` … `builder.compile()` |
| Running it with a question | `graph.invoke({...})` |

### The instructions given to the AI
The prompt tells the agent how to behave:

- Use web search when more information is needed
- Call `synthesize_evidence` when enough evidence has been gathered
- After receiving the evidence, write the final answer from it
- Don't call `synthesize_evidence` twice for the same task
- **Cite source URLs and distinguish supported facts from uncertainty**

---

## 🎬 A sample run, in plain English

Question: *"Who are the best characters in Attack on Titan?"*

```
1. 🧠 AI:      "I need information about fan opinions." → asks for a web search
2. 🔀 Router:  search requested → go to tools
3. 🔎 Search:  3 results come back
4. 📝 Notes:   url + title + snippet of each saved to research_evidence
5. 🧠 AI:      "Let me check one more angle." → asks for another search
6. 🔎📝 Search again → 3 more results saved (the old ones are kept!)
7. 🧠 AI:      "That's enough." → calls synthesize_evidence
8. 🔀 Router:  synthesize requested → go to synthesize_node
9. 📦 Hand-over: all saved evidence given back to the AI
10. 🧠 AI:     writes the final answer with source links
11. 🔀 Router: no tool call → END ✅
```

The final answer is printed with `print(result["messages"][-1])`.

> The number of searches isn't fixed. The AI decides. That's what makes it an *agent*.

---

## ▶️ How to run

### 1. Clone the repo
```bash
git clone https://github.com/samudra3/Python-Research-Assistant.git
cd Python-Research-Assistant
```

### 2. Install the requirements
```bash
pip install -r requirements.txt
pip install langchain
```
*(`langchain` is imported in the code for the `@tool` decorator, so it is installed here to be safe.)*

### 3. Add your API keys
Create a `.env` file in the project folder:
```
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```
- Gemini key: [Google AI Studio](https://aistudio.google.com/)
- Tavily key: [tavily.com](https://tavily.com/) (has a free tier)

### 4. Run it
```bash
python resAssistant.py
```

### 5. Ask your own question
Open `resAssistant.py`, find the line starting with `Question:` near the bottom, change the text, and run again.

---

## 🛠 Tech used

| Purpose | Tool |
|---|---|
| Language | Python |
| Agent workflow (graph, nodes, edges, state) | [LangGraph](https://github.com/langchain-ai/langgraph) |
| The AI model | Google Gemini via `langchain-google-genai` |
| Web search | [Tavily](https://tavily.com/) via `langchain-tavily` |
| Loading secret keys | `python-dotenv` |

---

## ⚠️ Known limitations and ideas

This is a **learning project**, kept small on purpose:

- The question is **hard-coded** in the script, so there is no interactive input yet.
- There is **no loop limit**, so in theory the AI could keep searching. Adding a maximum number of searches would make it safer.
- The `router` sends the AI to `synthesize_node` as soon as it sees `synthesize_evidence`. If the AI ever asks for a search *and* synthesize in the *same* message, that search would be skipped.
- It only searches the web, with 3 results per search. It does not read the full pages, only the snippets.
- The commented-out code at the bottom of the file (`research_node`, `analysis_node`, `answer_node`) shows an earlier, **fixed** pipeline design (research → analysis → answer). The current version replaced it with a flexible agent loop.

**Ideas to extend it:**
- Take the question from the user with `input()`
- Add a maximum search count
- Add more tools (Wikipedia, a PDF reader, a calculator)
- Save the final report to a file

---

## 🎯 Key takeaway

> **A research agent = an AI brain + tools + a notebook + a loop that lets the AI decide when it's done.**

---

⭐ If this project helped you understand AI agents, consider giving it a star!