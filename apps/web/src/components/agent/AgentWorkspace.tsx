import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspace } from "../../context/WorkspaceContext";
import { request } from "../../services/apiClient";
import { AgentOrchestrateResponsePayload, ProblemDetails } from "../../types/api";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconBot, IconSend, IconSparkles, IconTerminal } from "../ui/Icons";

interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  toolsUsed?: string[];
  toolResults?: any[];
  timestamp: string;
}

export const AgentWorkspace: React.FC = () => {
  const { token } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "init",
      sender: "agent",
      text: `Hello! I am your AuraML AI Platform Assistant. I have full context of workspace '${activeWorkspace.name}'. Ask me to analyze model metrics, compare model versions, explain Quality Gate evaluations, inspect dataset profiles, or run real-time model inference.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [inputText, setInputText] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);

  const suggestionChips = [
    "Compare churn model v1 and v2",
    "Why did churn-model fail quality gate?",
    "Summarize the customer churn dataset",
    "Predict churn for age 52, income 92000, tenure 5",
    "What models do we have registered?",
    "What datasets are available in workspace?",
  ];

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputText;
    if (!textToSend.trim() || isSending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsSending(true);
    setProblem(null);

    try {
      const res = await request<AgentOrchestrateResponsePayload>("/api/v1/agent/orchestrate", {
        method: "POST",
        token,
        body: {
          workspace_id: activeWorkspace.id,
          message: textToSend,
        },
      });

      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: "agent",
        text: res.answer,
        toolsUsed: res.tools_used,
        toolResults: res.tool_results,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      if (err.problem) {
        setProblem(err.problem);
      } else {
        setProblem({
          type: "about:blank",
          title: "Agent Assistant Error",
          status: 400,
          detail: err.message || "Failed to communicate with AI Agent assistant.",
          code: "agent_orchestration_error",
          request_id: "unknown",
        });
      }
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 180px)",
        maxHeight: "750px",
        backgroundColor: "var(--bg-surface)",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        overflow: "hidden",
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          padding: "1rem 1.25rem",
          backgroundColor: "var(--bg-card)",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--accent-purple-light)",
              color: "var(--accent-purple)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <IconBot size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              AuraML Intelligent Copilot
            </h3>
            <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)" }}>
              Workspace Context: <strong style={{ color: "var(--accent-blue)" }}>{activeWorkspace.name}</strong>
            </span>
          </div>
        </div>

        <Badge variant="purple" icon={<IconSparkles size={12} />}>
          Autonomous Tools Active
        </Badge>
      </div>

      {problem && (
        <div style={{ padding: "0.75rem 1rem" }}>
          <Alert problem={problem} onClose={() => setProblem(null)} />
        </div>
      )}

      {/* Message Feed */}
      <div
        style={{
          flex: 1,
          padding: "1.25rem",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "85%",
                padding: "0.875rem 1.125rem",
                borderRadius: "var(--radius-md)",
                backgroundColor: msg.sender === "user" ? "var(--accent-blue)" : "var(--bg-card)",
                color: msg.sender === "user" ? "#ffffff" : "var(--text-primary)",
                border: msg.sender === "user" ? "none" : "1px solid var(--border-subtle)",
                boxShadow: "var(--shadow-sm)",
                fontSize: "0.84375rem",
                lineHeight: "1.5",
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.text}

              {/* Tool Execution Badges */}
              {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                <div
                  style={{
                    marginTop: "0.75rem",
                    paddingTop: "0.5rem",
                    borderTop: "1px solid var(--border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: "0.71875rem", color: "var(--text-muted)", fontWeight: 600 }}>
                    Executed Tools:
                  </span>
                  {msg.toolsUsed.map((tool) => (
                    <span
                      key={tool}
                      style={{
                        fontSize: "0.6875rem",
                        fontFamily: "var(--font-mono)",
                        backgroundColor: "var(--accent-blue-light)",
                        color: "var(--accent-blue)",
                        padding: "0.15rem 0.45rem",
                        borderRadius: "var(--radius-xs)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3rem",
                      }}
                    >
                      <IconTerminal size={12} />
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
              {msg.sender === "user" ? "You" : "Copilot"} • {msg.timestamp}
            </span>
          </div>
        ))}

        {isSending && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", color: "var(--text-muted)", fontSize: "0.8125rem", padding: "0.5rem 0" }}>
            <span className="spinner" style={{ width: "16px", height: "16px" }} />
            <span>Copilot is inspecting database models and executing platform tools...</span>
          </div>
        )}
      </div>

      {/* Suggestion Chips */}
      <div
        style={{
          padding: "0.5rem 1.25rem",
          backgroundColor: "var(--bg-card)",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          gap: "0.5rem",
          overflowX: "auto",
        }}
      >
        {suggestionChips.map((chip) => (
          <button
            key={chip}
            onClick={() => handleSendMessage(chip)}
            disabled={isSending}
            style={{
              whiteSpace: "nowrap",
              fontSize: "0.75rem",
              padding: "0.35rem 0.75rem",
              borderRadius: "var(--radius-full)",
              backgroundColor: "var(--bg-surface)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
              cursor: "pointer",
              transition: "all var(--transition-fast)",
            }}
          >
            💡 {chip}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div
        style={{
          padding: "1rem 1.25rem",
          backgroundColor: "var(--bg-card)",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          gap: "0.75rem",
        }}
      >
        <input
          type="text"
          placeholder="Ask Copilot to analyze models, explain quality gates, or run predictions..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          disabled={isSending}
          className="aura-input"
          style={{ flex: 1 }}
        />
        <Button
          variant="primary"
          onClick={() => handleSendMessage()}
          disabled={isSending || !inputText.trim()}
          isLoading={isSending}
          icon={<IconSend size={15} />}
        >
          {isSending ? "Analyzing..." : "Send"}
        </Button>
      </div>
    </div>
  );
};
