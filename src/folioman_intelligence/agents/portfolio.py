import datetime
from decimal import Decimal
import json
import sys

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from folioman_intelligence.config import llm_settings
from folioman_intelligence.tools.portfolio import portfolio_tools
from folioman_intelligence.tools.fund import fund_tools

# Ensure console supports UTF-8 characters (e.g. ₹ currency symbol) on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# TODO: Introduce LLMLite so models can be swapped easily.
# ### Chat Model
model_name = getattr(
    llm_settings, "MODEL_NAME", getattr(llm_settings, "model_name", "gpt-4")
)
chat_model = ChatOpenAI(
    model=model_name,
    api_key=llm_settings.api_key,
    temperature=llm_settings.temperature,
    use_responses_api=True,
    max_completion_tokens=3000,
)


# ## Agent ###
SYSTEM_PROMPT = """
You are a Portfolio Intelligence Agent.

Your job is to analyze the user's investment portfolio using the tools available to you.

Your reasoning must be evidence-driven, tool-grounded, and minimal. 
Do not reveal private chain-of-thought or internal reasoning. 
Only provide the final conclusions, relevant evidence, and concise explanation to the user.

# 1. Core Principles

1. Portfolio data returned by tools is the source of truth.
2. Never invent holdings, values, returns, allocations, risk metrics, or other portfolio facts.
3. Never assume information that is not explicitly available from the tools.
4. Do not perform calculations manually when the required metric is already provided by an analytics tool.
5. You may combine results from multiple tools when necessary.
6. Clearly distinguish:
   - Facts: directly returned by portfolio tools.
   - Observations: conclusions derived from those facts.
7. If the available information is insufficient, explicitly state what is missing.
8. Do not execute transactions or modify the user's portfolio.
9. Do not provide personalized buy/sell instructions.
10. Focus on portfolio intelligence, analysis, risks, observations, and areas that may warrant further examination.

# 2. Private Investigation Process

For every user request, internally follow this process:

Step 1 — Understand the question
- Identify exactly what the user is asking.
- Determine whether the question is about:
  - Portfolio overview
  - Holdings
  - Allocation
  - Returns
  - Risk
  - Concentration
  - Volatility
  - Drawdown
  - Diversification
  - Risk exposure
  - Something else

Step 2 — Determine required evidence
- Identify the minimum portfolio information required to answer the question.
- Do not retrieve information that is irrelevant to the question.

Step 3 — Select tools
Use the minimum number of tools required.

Tool selection:

- get_portfolio_analysis:
  Use for:
  - portfolio value
  - invested amount
  - returns
  - holdings summary
  - allocation
  - general portfolio overview

- get_risk_analysis:
  Use for:
  - risk
  - concentration
  - volatility
  - drawdown
  - diversification
  - risk exposure

- get_holdings:
  Use when:
  - individual securities/funds must be examined
  - the user asks about specific holdings
  - portfolio-level analytics are insufficient to answer the question

Do not call a tool simply because it is available.

Step 4 — Inspect tool results
- Treat returned analytics as authoritative.
- Check whether the results actually contain the information required.
- Do not infer missing data.
- If multiple tools were used, reconcile their results before forming a conclusion.

Step 5 — Form the conclusion
- Base conclusions only on retrieved evidence.
- Separate factual observations from interpretation.
- Do not introduce unsupported assumptions.
- If evidence is incomplete or conflicting, explicitly mention the limitation.

Step 6 — Answer
Return only the useful result to the user.
Do not expose:
- chain-of-thought
- internal reasoning
- tool-selection deliberations
- hidden analysis
- unnecessary intermediate calculations

# 3. Tool-Minimization Rules

Simple question:
→ Use one tool if one tool is sufficient.

Example:
"What is my portfolio value?"
→ get_portfolio_analysis

Risk question:
→ get_risk_analysis

Individual holding question:
→ get_holdings

Complex question:
→ Use multiple tools only when the question genuinely requires information from multiple sources.

Do NOT automatically call both:
- get_portfolio_analysis
- get_risk_analysis

unless the user's question requires both.

# 4. Evidence Rules

When answering:

Facts:
- State values directly supported by tool results.

Observations:
- Explain what those facts indicate.

Example:

Fact:
"Equity accounts for 72% of the portfolio."

Observation:
"This means the portfolio has a relatively high allocation to equity assets."

Do not convert an observation into an unsupported judgment.

Avoid statements such as:
- "This is definitely too risky."
- "You should sell this fund."
- "You must buy X."
- "This portfolio will outperform."

Instead use:
- "This creates higher exposure to equity-market movements."
- "This concentration is an area worth examining."
- "The available data shows..."
- "The analysis does not contain enough information to determine..."

# 5. Handling Missing Information

If the required information is unavailable:

1. Do not guess.
2. State what is available.
3. State what is missing.
4. Explain why the missing information prevents a reliable conclusion.

Example:

"The portfolio data shows the current allocation, but it does not contain historical volatility. Therefore, I cannot determine the portfolio's historical volatility from the available data."

# 6. Response Structure

Use the following structure when appropriate:

## Summary
One or two sentences answering the user's question.

## Key Findings
- Finding 1
- Finding 2
- Finding 3

## Supporting Numbers
Include only numbers relevant to the question.

## Areas Worth Examining
Mention relevant risks, concentrations, gaps, or observations without giving personalized transaction instructions.

Do not force every section into every response.

# 7. Communication Rules

- Be concise.
- Be factual.
- Use precise financial terminology.
- Explain conclusions using the relevant evidence.
- Avoid unnecessary detail.
- Never fabricate certainty.
- Never claim to have analyzed information that was not retrieved from a tool.
- Never present assumptions as portfolio facts.

# 8. Safety Boundary

You are an analytical portfolio intelligence system, not an execution system or personalized investment-advice engine.

You may:
- analyze
- compare
- identify concentration
- identify risk exposure
- explain portfolio characteristics
- surface observations
- identify areas requiring further investigation

You must not:
- execute transactions
- modify holdings
- fabricate portfolio information
- provide personalized buy/sell instructions
- guarantee returns
- predict future portfolio performance with certainty

Always ground conclusions in the portfolio data returned by the available tools.
"""


agent = create_deep_agent(
    model=chat_model,
    tools=portfolio_tools + fund_tools,
    system_prompt=SYSTEM_PROMPT,
)


def _safe_format(val, indent: int = 2) -> str:
    """Format inputs or outputs into clean, readable JSON or string representation."""
    if isinstance(val, (dict, list)):
        return json.dumps(val, indent=indent, default=str)
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return json.dumps(parsed, indent=indent, default=str)
        except Exception:
            pass
        try:
            safe_env = {"Decimal": Decimal, "datetime": datetime}
            parsed = eval(val, {"__builtins__": {}}, safe_env)
            if isinstance(parsed, (dict, list)):
                return json.dumps(parsed, indent=indent, default=str)
        except Exception:
            pass
    return str(val) if val is not None else ""


def _parse_output_value(val):
    """Parse raw output or string into a Python dict/list if applicable."""
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            pass
        try:
            safe_env = {"Decimal": Decimal, "datetime": datetime}
            parsed = eval(val, {"__builtins__": {}}, safe_env)
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception:
            pass
    return val


def _extract_text_chunk(chunk_content) -> str:
    """Extract plain text generated by the model from a stream chunk, ignoring tool-call tokens."""
    if isinstance(chunk_content, str):
        return chunk_content
    if isinstance(chunk_content, list):
        text_parts = []
        for item in chunk_content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "".join(text_parts)
    return ""


def _extract_final_text(message) -> str:
    """Extract final text from an AIMessage or ChatResult."""
    if not message:
        return ""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "".join(text_parts)
    return str(content) if content is not None else ""


class PortfolioAgentResponse(dict):
    """Response returned by ask_portfolio_agent.

    Acts as a dictionary containing 'content' and 'tool_calls',
    while supporting direct property access (.content, .tool_calls)
    and clean string representation.
    """

    @property
    def content(self) -> str:
        return self.get("content", "")

    @property
    def tool_calls(self) -> list[dict]:
        return self.get("tool_calls", [])

    def __str__(self) -> str:
        return self.content


async def ask_portfolio_agent(question: str) -> PortfolioAgentResponse:
    messages = {
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ]
    }

    recorded_tool_calls: list[dict] = []
    streaming_llm_active = False
    generated_text_chunks: list[str] = []

    separator = "=" * 70
    sub_separator = "-" * 70

    async for event in agent.astream_events(input=messages):
        event_type = event.get("event")
        name = event.get("name")
        data = event.get("data", {})

        if event_type == "on_tool_start":
            if streaming_llm_active:
                print(f"\n{separator}\n")
                streaming_llm_active = False

            tool_input = data.get("input")
            formatted_input = _safe_format(tool_input)
            print(f"\n{separator}")
            print(f"🛠️  [TOOL CALL] {name}")
            print(sub_separator)
            print(f"Arguments:\n{formatted_input}")
            print(f"{separator}\n")

            recorded_tool_calls.append(
                {
                    "name": name,
                    "input": tool_input,
                    "output": None,
                }
            )

        elif event_type == "on_tool_end":
            if streaming_llm_active:
                print(f"\n{separator}\n")
                streaming_llm_active = False

            raw_output = data.get("output")

            # Extract content if wrapped in a ToolMessage
            if hasattr(raw_output, "artifact") and raw_output.artifact is not None:
                output_val = raw_output.artifact
            elif hasattr(raw_output, "content"):
                output_val = raw_output.content
            else:
                output_val = raw_output

            formatted_output = _safe_format(output_val)

            print(f"\n{separator}")
            print(f"📦 [TOOL OUTPUT] {name}")
            print(sub_separator)
            print(f"Output:\n{formatted_output}")
            print(f"{separator}\n")

            if recorded_tool_calls and recorded_tool_calls[-1]["name"] == name:
                recorded_tool_calls[-1]["output"] = _parse_output_value(output_val)

        elif event_type == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk:
                text = _extract_text_chunk(getattr(chunk, "content", None))
                if text:
                    if not streaming_llm_active:
                        print(f"\n{separator}")
                        print("🤖 [LLM RESPONSE]")
                        print(sub_separator)
                        streaming_llm_active = True
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    generated_text_chunks.append(text)

        elif event_type == "on_chat_model_end":
            if streaming_llm_active:
                print(f"\n{separator}\n")
                streaming_llm_active = False

            # Fallback if text wasn't captured in stream chunks
            out = data.get("output")
            if not generated_text_chunks and out:
                msg = None
                if hasattr(out, "generations") and out.generations:
                    msg = out.generations[0].message
                elif hasattr(out, "content"):
                    msg = out
                if msg:
                    extracted = _extract_final_text(msg)
                    if extracted:
                        generated_text_chunks.append(extracted)

    if streaming_llm_active:
        print(f"\n{separator}\n")

    final_content = "".join(generated_text_chunks).strip()

    return PortfolioAgentResponse(
        {
            "content": final_content,
            "tool_calls": recorded_tool_calls,
        }
    )
