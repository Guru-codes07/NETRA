import { useEffect, useRef, useState } from "react";
import { askQuestion } from "./api";
import "./ChatPanel.css";

/*
 * ChatPanel — natural-language query interface for NETRA.
 *
 * Sends investigator questions to POST /ask (Llama 3.1 via Ollama on the
 * backend) and renders the plain-English answer, with the generated
 * Cypher query available on demand for transparency/audit.
 */
export default function ChatPanel({ open, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const result = await askQuestion(question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.answer,
          cypher: result.cypher,
          isError: Boolean(result.error),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Could not reach the NETRA API. Is the backend running on :8000?",
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-title">AI ASSISTANT</span>
        <button className="chat-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            Ask a question about the network in plain English.
            <br />
            <span className="chat-empty-example">
              e.g. "Which persons are linked to case C004?"
            </span>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="chat-bubble chat-bubble-assistant">
            <span className="chat-typing">
              <span></span><span></span><span></span>
            </span>
          </div>
        )}
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Ask NETRA..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          ➤
        </button>
      </form>
    </div>
  );
}

function ChatBubble({ message }) {
  const [showCypher, setShowCypher] = useState(false);
  const isUser = message.role === "user";

  return (
    <div className={`chat-bubble ${isUser ? "chat-bubble-user" : "chat-bubble-assistant"} ${message.isError ? "chat-bubble-error" : ""}`}>
      <p className="chat-bubble-text">{message.text}</p>

      {message.cypher && (
        <>
          <button className="chat-cypher-toggle" onClick={() => setShowCypher((v) => !v)}>
            {showCypher ? "Hide query" : "View query"}
          </button>
          {showCypher && <pre className="chat-cypher">{message.cypher}</pre>}
        </>
      )}
    </div>
  );
}
