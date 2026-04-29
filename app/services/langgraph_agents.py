"""
LangGraph Multi-Agent System for Smart Classroom.

Agent A — Quiz Question Generator
Agent B — Student Doubt Solver

Both agents use RAG with FAISS + Gemini 2.5 Flash.
"""

import os
import json
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ─── Shared Utilities ───────────────────────────────────────────

def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_llm(temperature=0.7, model_name="gemini-1.5-flash"):
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=GOOGLE_API_KEY,
    )


# ═══════════════════════════════════════════════════════════════
#  AGENT A: Quiz Question Generator
# ═══════════════════════════════════════════════════════════════

class QuizGenState(TypedDict):
    pdf_path: str
    session_code: str
    vectorstore_dir: str      # base dir for vectorstores
    num_pages: int
    chunks: list
    context: str
    target_count: int
    questions: list
    error: str


def _quiz_load_pdf(state: QuizGenState) -> dict:
    """Node 1: Load PDF and split into chunks."""
    try:
        loader = PyPDFLoader(state["pdf_path"])
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        n = len(docs)
        target = 30 if n <= 3 else 50 if n <= 10 else 70 if n <= 25 else 100
        print(f"[Agent A] Loaded {n} pages → {len(chunks)} chunks, targeting {target} questions")
        return {"chunks": chunks, "num_pages": n, "target_count": target}
    except Exception as e:
        print(f"[Agent A] Error in _quiz_load_pdf: {e}")
        return {"error": str(e)}


def _quiz_build_vectorstore(state: QuizGenState) -> dict:
    """Node 2: Build FAISS vectorstore and save it."""
    if state.get("error"):
        return {}
    try:
        embeddings = get_embeddings()
        vectorstore = FAISS.from_documents(state["chunks"], embeddings)
        vs_path = os.path.join(state["vectorstore_dir"], state["session_code"])
        os.makedirs(vs_path, exist_ok=True)
        vectorstore.save_local(vs_path)
        print(f"[Agent A] Vectorstore saved to {vs_path}")
        return {"vectorstore_dir": vs_path}
    except Exception as e:
        print(f"[Agent A] Error in _quiz_build_vectorstore: {e}")
        return {"error": str(e)}


def _quiz_retrieve_context(state: QuizGenState) -> dict:
    """Node 3: Retrieve diverse context from the vectorstore."""
    if state.get("error"):
        return {}
    try:
        embeddings = get_embeddings()
        vectorstore = FAISS.load_local(
            state["vectorstore_dir"], embeddings,
            allow_dangerous_deserialization=True
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        topics = [
            "key concepts and definitions",
            "important principles and theories",
            "examples and applications",
            "comparisons and differences",
            "processes and procedures",
            "advantages and limitations",
            "summary and conclusions",
        ]
        unique_chunks = []
        for topic in topics:
            for doc in retriever.invoke(topic):
                if doc.page_content not in unique_chunks:
                    unique_chunks.append(doc.page_content)
        context = "\n\n---\n\n".join(unique_chunks)
        print(f"[Agent A] Retrieved {len(unique_chunks)} unique context chunks")
        return {"context": context}
    except Exception as e:
        print(f"[Agent A] Error in _quiz_retrieve_context: {e}")
        return {"error": str(e)}


def _quiz_generate_questions(state: QuizGenState) -> dict:
    """Node 4: Generate quiz questions with Gemini. Includes retry + fallback."""
    if state.get("error"):
        return {}

    import time

    prompt_template = PromptTemplate.from_template(
        """You are a highly experienced university professor designing a comprehensive assessment.

TASK: Generate exactly {num_questions} high-quality quiz questions from the provided course material.

CRITICAL RULES:
1. DO NOT copy-paste sentences from the material as questions. Every question must be REPHRASED in your own words.
2. Questions must TEST UNDERSTANDING — ask about concepts, relationships, applications, and reasoning.
3. For MCQs: all 4 options must be plausible. The wrong options should be realistic distractors.
4. For Fill-in-the-blanks: use a meaningful sentence that tests a KEY TERM or CONCEPT.
5. Cover DIFFERENT topics and sections from the material evenly.
6. Mix difficulty: easy recall, moderate application, and challenging analytical questions.
7. Produce roughly 70% MCQs and 30% Fill-in-the-blanks.

OUTPUT FORMAT: Return ONLY a valid JSON array. Each object must have:
- "question_text": The question (for fill_blank, use ______ to mark the blank)
- "question_type": "mcq" or "fill_blank"
- "options": A list of exactly 4 option strings (for mcq). Empty list [] for fill_blank.
- "correct_answer": The exact correct answer string

COURSE MATERIAL:
{context}

Generate {num_questions} questions now. JSON array only, no extra text:"""
    )

    # --- Retry with exponential backoff and Model Rotation ---
    # By rotating models, we bypass the strict per-model free tier quota limits
    fallback_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    max_retries = len(fallback_models)
    questions = []

    for attempt in range(max_retries):
        current_model = fallback_models[attempt]
        try:
            llm = get_llm(temperature=0.8, model_name=current_model)
            chain = prompt_template | llm
            response = chain.invoke({
                "num_questions": state["target_count"],
                "context": state["context"],
            })
            raw = response.content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)

            # Validate each question has required fields
            valid = []
            for q in parsed:
                if (q.get("question_text") and q.get("correct_answer")
                        and q.get("question_type") in ("mcq", "fill_blank")):
                    if q["question_type"] == "mcq" and (not q.get("options") or len(q["options"]) < 2):
                        continue  # Skip malformed MCQs
                    valid.append(q)

            if len(valid) >= 5:  # Minimum threshold
                print(f"[Agent A] {current_model} generated {len(valid)} valid questions")
                return {"questions": valid}
            else:
                print(f"[Agent A] {current_model} only generated {len(valid)} valid questions, retrying...")

        except Exception as e:
            print(f"[Agent A] Attempt with {current_model} failed: {e}")

        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)
            print(f"[Agent A] Waiting {wait}s before retry with next model...")
            time.sleep(wait)

    # --- Fallback: generate simple questions from raw chunks ---
    print("[Agent A] All retries failed. Using fallback question generator...")
    fallback_questions = _generate_fallback_questions(state.get("chunks", []), state.get("target_count", 30))

    if fallback_questions:
        print(f"[Agent A] Fallback generated {len(fallback_questions)} questions")
        return {"questions": fallback_questions}

    return {"questions": [], "error": "Question generation failed after all retries and fallback"}


def _generate_fallback_questions(chunks, target_count):
    """Generate basic fill-in-the-blank questions from raw text chunks as a last resort."""
    import re
    questions = []
    seen = set()

    for chunk in chunks:  # Process all chunks to get more fallback questions
        text = chunk.page_content if hasattr(chunk, 'page_content') else str(chunk)
        sentences = re.split(r'[.!?]\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            words = sentence.split()
            if len(words) < 6 or len(words) > 30:
                continue

            # Pick a keyword (longer word, likely a concept)
            keywords = [w for w in words if len(w) > 5 and w.isalpha()]
            if not keywords:
                continue

            keyword = max(keywords, key=len)
            if keyword.lower() in seen:
                continue
            seen.add(keyword.lower())

            blank_sentence = sentence.replace(keyword, "______", 1)
            questions.append({
                "question_text": blank_sentence,
                "question_type": "fill_blank",
                "options": [],
                "correct_answer": keyword,
            })

            if len(questions) >= target_count:
                break
        if len(questions) >= target_count:
            break

    return questions


def build_quiz_agent() -> StateGraph:
    """Compile the Quiz Question Generator agent graph."""
    graph = StateGraph(QuizGenState)
    graph.add_node("load_pdf", _quiz_load_pdf)
    graph.add_node("build_vectorstore", _quiz_build_vectorstore)
    graph.add_node("retrieve_context", _quiz_retrieve_context)
    graph.add_node("generate_questions", _quiz_generate_questions)

    graph.set_entry_point("load_pdf")
    graph.add_edge("load_pdf", "build_vectorstore")
    graph.add_edge("build_vectorstore", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_questions")
    graph.add_edge("generate_questions", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
#  AGENT B: Student Doubt Solver
# ═══════════════════════════════════════════════════════════════

class DoubtSolverState(TypedDict):
    query: str
    vectorstore_path: str
    chat_history: list          # list of {"role": ..., "content": ...}
    retrieved_chunks: list
    context: str
    answer: str
    sources: list               # list of source snippet strings
    error: str


def _doubt_retrieve(state: DoubtSolverState) -> dict:
    """Node 1: Retrieve relevant chunks for the student's question."""
    try:
        embeddings = get_embeddings()
        vectorstore = FAISS.load_local(
            state["vectorstore_path"], embeddings,
            allow_dangerous_deserialization=True
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        docs = retriever.invoke(state["query"])
        chunks = [doc.page_content for doc in docs]
        context = "\n\n---\n\n".join(chunks)
        # Keep top 3 as source snippets (truncated)
        sources = [c[:200] + "..." if len(c) > 200 else c for c in chunks[:3]]
        print(f"[Agent B] Retrieved {len(chunks)} chunks for query")
        return {"retrieved_chunks": chunks, "context": context, "sources": sources}
    except Exception as e:
        return {"error": str(e)}


def _doubt_generate_answer(state: DoubtSolverState) -> dict:
    """Node 2: Generate a grounded, educational answer with clean formatting."""
    if state.get("error"):
        return {"answer": f"Sorry, I encountered an error: {state['error']}"}
    try:
        llm = get_llm(temperature=0.5, model_name="gemini-2.5-flash-lite")

        # Build conversation context from history (last 10 messages max)
        history_text = ""
        recent_history = state.get("chat_history", [])[-10:]
        if recent_history:
            history_lines = []
            for msg in recent_history:
                role = "Student" if msg["role"] == "user" else "AI Tutor"
                history_lines.append(f"{role}: {msg['content']}")
            history_text = "\n".join(history_lines)

        prompt = PromptTemplate.from_template(
            """You are a friendly, knowledgeable tutor having a one-on-one conversation with a student.

Your personality:
- Talk like a helpful senior student or a young professor
- Be warm, approachable, and encouraging
- Explain things the way you would to a friend who is genuinely curious

STRICT FORMATTING RULES:
- Do NOT use any markdown: no **, no ##, no bullet points (-, *), no numbered lists
- Write in plain conversational paragraphs only
- Never start with "This assignment is about..." or any formal opener
- Never say "Here is the answer:" or similar boilerplate
- Do NOT structure your response like an essay or report
- Keep it short and clear. 2-4 paragraphs max

HOW TO ANSWER:
1. Start with a direct, concise answer to the question (1-2 sentences)
2. Then explain it simply with an example or analogy if it helps
3. End with a brief encouraging line like "Let me know if this makes sense!" or "Feel free to ask more about this."

IMPORTANT CONSTRAINTS:
- Answer ONLY from the provided course material. Do not make things up
- If the answer is NOT in the material, say something like: "Hmm, I could not find this in your uploaded material. It might be covered in a different section or chapter. Try checking [suggest topic]."
- Use simple everyday language. Avoid jargon unless the material uses it
- Consider the conversation history for follow-up questions

COURSE MATERIAL:
{context}

CONVERSATION SO FAR:
{history}

STUDENT ASKS:
{query}

YOUR RESPONSE (plain text, no markdown):"""
        )

        chain = prompt | llm
        response = chain.invoke({
            "context": state["context"],
            "history": history_text if history_text else "(First question in this chat)",
            "query": state["query"],
        })

        # Post-process: strip any markdown that leaked through
        answer = response.content
        answer = answer.replace("**", "").replace("##", "").replace("###", "")
        answer = answer.replace("```", "").replace("`", "")
        # Remove leading bullets/numbers at line starts
        import re
        answer = re.sub(r'^[\s]*[-*•]\s+', '', answer, flags=re.MULTILINE)
        answer = re.sub(r'^[\s]*\d+\.\s+', '', answer, flags=re.MULTILINE)
        answer = answer.strip()

        print(f"[Agent B] Generated answer ({len(answer)} chars)")
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Sorry, I encountered an error generating a response: {str(e)}"}


def build_doubt_agent() -> StateGraph:
    """Compile the Student Doubt Solver agent graph."""
    graph = StateGraph(DoubtSolverState)
    graph.add_node("retrieve", _doubt_retrieve)
    graph.add_node("generate_answer", _doubt_generate_answer)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


# ─── High-Level Runner Functions ────────────────────────────────

# Compiled agents (lazy-loaded singletons)
_quiz_agent = None
_doubt_agent = None


def run_quiz_agent(pdf_path: str, session_code: str, vectorstore_dir: str) -> list:
    """Run Agent A to generate quiz questions. Returns list of question dicts."""
    global _quiz_agent
    if _quiz_agent is None:
        _quiz_agent = build_quiz_agent()

    result = _quiz_agent.invoke({
        "pdf_path": pdf_path,
        "session_code": session_code,
        "vectorstore_dir": vectorstore_dir,
        "num_pages": 0,
        "chunks": [],
        "context": "",
        "target_count": 0,
        "questions": [],
        "error": "",
    })
    return result.get("questions", [])


def run_doubt_agent(query: str, vectorstore_path: str, chat_history: list = None) -> dict:
    """Run Agent B to answer a student doubt. Returns {"answer": ..., "sources": [...]}."""
    global _doubt_agent
    if _doubt_agent is None:
        _doubt_agent = build_doubt_agent()

    result = _doubt_agent.invoke({
        "query": query,
        "vectorstore_path": vectorstore_path,
        "chat_history": chat_history or [],
        "retrieved_chunks": [],
        "context": "",
        "answer": "",
        "sources": [],
        "error": "",
    })
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
    }
