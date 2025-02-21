# test_graph.py
import pytest
from test3 import (
    detect_ambiguity,
    clarify_question,
    process_clarification,
    transform_query,
    retrieve_wikipedia,
    grade_wikipedia,
    retrieve_web,
    rerank_documents,
    generate_answer,
    workflow
)
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI  # We'll monkeypatch on the class


# A fixture for a base state with a dummy session_id
@pytest.fixture
def base_state():
    return {
        "original_question": "Test question",
        "clarified_question": None,
        "wikipedia_docs": [],
        "web_docs": [],
        "reranked_docs": [],
        "final_answer": None,
        "needs_clarification": False,
        "session_id": "test-session"
    }


#####################################
# Helper dummy_invoke functions
#####################################

def dummy_invoke_yes(self, prompt):
    class DummyResponse:
        content = "yes"

    return DummyResponse()


def dummy_invoke_no(self, prompt):
    class DummyResponse:
        content = "no"

    return DummyResponse()


def dummy_invoke_clarification(self, prompt):
    class DummyResponse:
        content = "- Are you asking about Tesla's headquarters, a specific Tesla store, or something else?"

    return DummyResponse()


def dummy_invoke_process(self, prompt):
    class DummyResponse:
        content = "Where is Tesla's headquarters located?"

    return DummyResponse()


def dummy_invoke_generate(self, prompt):
    class DummyResponse:
        content = "Tesla HQ is located in Palo Alto (Wikipedia)"

    return DummyResponse()


def dummy_invoke_rerank(self, prompt):
    class DummyResponse:
        content = "0,2"

    return DummyResponse()


#####################################
# detect_ambiguity tests
#####################################

def test_detect_ambiguity_ambiguous(base_state, monkeypatch):
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_yes)
    base_state["original_question"] = "Where is Tesla?"
    result = detect_ambiguity(base_state)
    assert result["needs_clarification"] is True


def test_detect_ambiguity_not_ambiguous(base_state, monkeypatch):
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_no)
    base_state["original_question"] = "Where is Tesla HQ?"
    result = detect_ambiguity(base_state)
    assert result["needs_clarification"] is False


#####################################
# clarify_question tests
#####################################

def test_clarify_question(base_state, monkeypatch):
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_clarification)
    base_state["original_question"] = "Where is Tesla?"
    result = clarify_question(base_state)
    assert "clarified_question" in result
    assert result["needs_clarification"] is True


#####################################
# process_clarification tests
#####################################

def test_process_clarification_too_ambiguous(base_state, monkeypatch):
    # Provide a clarification with multiple bullet points
    base_state["clarified_question"] = "- Option 1\n- Option 2"
    # In this case, we expect no processing and still need clarification.
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_process)
    result = process_clarification(base_state)
    assert result["needs_clarification"] is True
    assert result["clarified_question"] == base_state["clarified_question"]


def test_process_clarification_not_ambiguous(base_state, monkeypatch):
    base_state["clarified_question"] = "- Only one option"
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_process)
    result = process_clarification(base_state)
    assert result["needs_clarification"] is False
    assert result["clarified_question"] == "Where is Tesla's headquarters located?"


#####################################
# transform_query tests
#####################################

def test_transform_query_skip_if_ambiguous(base_state):
    base_state["needs_clarification"] = True
    base_state["clarified_question"] = "Ambiguous clarification text"
    result = transform_query(base_state)
    assert result == {}


def test_transform_query_tesla(monkeypatch, base_state):
    base_state["needs_clarification"] = False
    base_state["original_question"] = "Where is Tesla HQ?"
    base_state["clarified_question"] = "Where is Tesla HQ?"
    result = transform_query(base_state)
    expected = "Where is Tesla's main corporate headquarters located?"
    assert "clarified_question" in result
    assert result["clarified_question"] == expected


def test_transform_query_sequoia(monkeypatch, base_state):
    base_state["needs_clarification"] = False
    base_state["original_question"] = "Which companies has Sequoia invested in?"
    base_state["clarified_question"] = "Which companies has Sequoia invested in?"
    result = transform_query(base_state)
    expected = "Sequoia Capital investments 2025"
    assert "clarified_question" in result
    assert result["clarified_question"] == expected


def test_transform_query_no_transformation(monkeypatch, base_state):
    base_state["needs_clarification"] = False
    base_state["original_question"] = "How tall is the Eiffel Tower?"
    base_state["clarified_question"] = "How tall is the Eiffel Tower?"
    result = transform_query(base_state)
    assert result == {}


#####################################
# retrieve_wikipedia tests
#####################################

def test_retrieve_wikipedia(monkeypatch, base_state):
    def dummy_wiki_run(query):
        return ["Wiki doc 1 content", "Wiki doc 2 content"]

    monkeypatch.setattr("test3.wikipedia.run", dummy_wiki_run)
    base_state["original_question"] = "Where is Tesla HQ?"
    result = retrieve_wikipedia(base_state)
    assert "wikipedia_docs" in result
    assert len(result["wikipedia_docs"]) == 2


#####################################
# grade_wikipedia tests
#####################################

def test_grade_wikipedia_sufficient(monkeypatch, base_state):
    base_state["wikipedia_docs"] = [Document(page_content="Good answer content", metadata={"source": "Wikipedia"})]
    base_state["original_question"] = "Where is Tesla HQ?"
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_yes)
    result = grade_wikipedia(base_state)
    # generate_answer should have been called, so final_answer should be set.
    assert "final_answer" in result
    assert result["final_answer"] is not None


def test_grade_wikipedia_insufficient(monkeypatch, base_state):
    base_state["wikipedia_docs"] = [Document(page_content="Bad content", metadata={"source": "Wikipedia"})]
    base_state["original_question"] = "Where is Tesla HQ?"
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_no)
    result = grade_wikipedia(base_state)
    assert result["final_answer"] is None


#####################################
# retrieve_web tests
#####################################

def test_retrieve_web(monkeypatch, base_state):
    def dummy_web_invoke(query):
        return [
            {"content": "Web doc 1", "url": "http://example.com/1"},
            {"content": "Web doc 2", "url": "http://example.com/2"}
        ]

    monkeypatch.setattr("test3.web_search.invoke", dummy_web_invoke)
    base_state["original_question"] = "Where is Tesla HQ?"
    result = retrieve_web(base_state)
    assert "web_docs" in result
    assert len(result["web_docs"]) == 2


#####################################
# rerank_documents tests
#####################################

def test_rerank_documents(monkeypatch, base_state):
    base_state["web_docs"] = [
        Document(page_content="Doc A about Tesla", metadata={"source": "urlA"}),
        Document(page_content="Doc B not related", metadata={"source": "urlB"}),
        Document(page_content="Doc C about Tesla headquarters", metadata={"source": "urlC"})
    ]
    base_state["original_question"] = "Where is Tesla HQ?"
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_rerank)
    result = rerank_documents(base_state)
    assert "reranked_docs" in result
    assert len(result["reranked_docs"]) == 2


#####################################
# generate_answer tests
#####################################

def test_generate_answer_with_wikipedia(monkeypatch, base_state):
    base_state["wikipedia_docs"] = [Document(page_content="Wikipedia answer snippet", metadata={"source": "Wikipedia"})]
    base_state["original_question"] = "Where is Tesla HQ?"
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_generate)
    result = generate_answer(base_state)
    assert "final_answer" in result
    assert "Palo Alto" in result["final_answer"]


def test_generate_answer_with_web(monkeypatch, base_state):
    base_state["wikipedia_docs"] = []
    base_state["reranked_docs"] = [
        Document(page_content="Web answer snippet", metadata={"source": "http://example.com"})]
    base_state["original_question"] = "Where is Tesla HQ?"
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_generate)
    result = generate_answer(base_state)
    assert "final_answer" in result
    assert "Palo Alto" in result["final_answer"]


#####################################
# Integration test: Full Workflow
#####################################

def test_full_workflow(monkeypatch, base_state):
    # Detect ambiguity: no ambiguity.
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_no)
    base_state["original_question"] = "Where is Tesla HQ?"

    # Wikipedia retrieval.
    def dummy_wiki_run(query):
        return ["Wiki doc for Tesla HQ"]

    monkeypatch.setattr("test3.wikipedia.run", dummy_wiki_run)

    # For grade_wikipedia, simulate sufficient content.
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_yes)

    # For generate_answer, simulate a generated answer.
    monkeypatch.setattr(ChatOpenAI, "invoke", dummy_invoke_generate)

    result = workflow.invoke(base_state)
    assert "final_answer" in result
    assert "Palo Alto" in result["final_answer"]
