import { useMemo, useState } from "react";
import type { FormEvent } from "react";

type PaymentDraft = {
  id: string;
  payee: string;
  amount: string;
  invoice_id: string;
  status: string;
  approval_token?: string | null;
  block_reason?: string | null;
};

type AgentResponse = {
  agent: string;
  message: string;
  data?: unknown;
  approval_required: boolean;
  payment_draft?: PaymentDraft | null;
};

type ChatItem = {
  role: "user" | "assistant";
  text: string;
  response?: AgentResponse;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const quickPrompts = [
  "Show my account balance and available payment methods.",
  "Summarize my last ten transactions and spending by category.",
  "Pay Contoso Utilities $125.40 for invoice INV-2048.",
  "Review my recent transactions for suspicious activity.",
];

export default function App() {
  const [input, setInput] = useState(quickPrompts[0]);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ChatItem[]>([
    {
      role: "assistant",
      text: "Welcome. This is a synthetic banking demonstration. No real account or payment system is connected.",
    },
  ]);

  const latestDraft = useMemo(
    () =>
      [...items]
        .reverse()
        .find((item) => item.response?.payment_draft)?.response?.payment_draft,
    [items],
  );

  async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setItems((current) => [...current, { role: "user", text: message }]);
    setInput("");
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, user_id: "user-1001" }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Request failed");
      setItems((current) => [
        ...current,
        { role: "assistant", text: body.message, response: body },
      ]);
    } catch (error) {
      setItems((current) => [
        ...current,
        {
          role: "assistant",
          text: error instanceof Error ? error.message : "Unable to reach the API",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function decidePayment(decision: "approve" | "reject") {
    if (!latestDraft?.approval_token) return;
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/payments/${latestDraft.id}/decision?user_id=user-1001`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decision,
            approval_token: latestDraft.approval_token,
          }),
        },
      );
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Decision failed");
      setItems((current) => [
        ...current,
        {
          role: "assistant",
          text: `Payment ${body.id} is now ${body.status}.`,
          response: {
            agent: "payment_agent",
            message: `Payment ${body.id} is now ${body.status}.`,
            approval_required: false,
            payment_draft: body,
          },
        },
      ]);
    } catch (error) {
      setItems((current) => [
        ...current,
        {
          role: "assistant",
          text: error instanceof Error ? error.message : "Decision failed",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <span className="eyebrow">Agentic AI portfolio</span>
          <h1>Enterprise Banking Assistant</h1>
          <p className="subtitle">
            Supervisor routing, MCP tools, payment guardrails, and human approval.
          </p>
        </div>

        <section className="status-card">
          <span className="status-dot" />
          <div>
            <strong>Synthetic demo mode</strong>
            <p>No real banking connection</p>
          </div>
        </section>

        <section>
          <h2>Try a workflow</h2>
          <div className="quick-list">
            {quickPrompts.map((prompt) => (
              <button key={prompt} onClick={() => setInput(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </section>
      </aside>

      <section className="workspace">
        <header>
          <div>
            <span className="eyebrow">Secure conversational operations</span>
            <h2>Banking copilot</h2>
          </div>
          <span className="policy-chip">Human approval required</span>
        </header>

        <div className="conversation" aria-live="polite">
          {items.map((item, index) => (
            <article className={`message ${item.role}`} key={`${item.role}-${index}`}>
              <div className="message-label">
                {item.role === "user" ? "You" : item.response?.agent ?? "Assistant"}
              </div>
              <p>{item.text}</p>
              {item.response?.data ? (
                <pre>{JSON.stringify(item.response.data, null, 2)}</pre>
              ) : null}
              {item.response?.payment_draft ? (
                <div className="payment-card">
                  <div>
                    <span>Payee</span>
                    <strong>{item.response.payment_draft.payee}</strong>
                  </div>
                  <div>
                    <span>Amount</span>
                    <strong>${item.response.payment_draft.amount}</strong>
                  </div>
                  <div>
                    <span>Invoice</span>
                    <strong>{item.response.payment_draft.invoice_id}</strong>
                  </div>
                  <div>
                    <span>Status</span>
                    <strong>{item.response.payment_draft.status}</strong>
                  </div>
                </div>
              ) : null}
            </article>
          ))}
          {loading ? <div className="typing">Agent workflow is processing…</div> : null}
        </div>

        {latestDraft?.status === "awaiting_approval" ? (
          <div className="approval-bar">
            <div>
              <strong>Review required</strong>
              <span>The draft has not been executed.</span>
            </div>
            <button className="reject" onClick={() => decidePayment("reject")}>
              Reject
            </button>
            <button className="approve" onClick={() => decidePayment("approve")}>
              Approve payment
            </button>
          </div>
        ) : null}

        <form className="composer" onSubmit={sendMessage}>
          <textarea
            aria-label="Message"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about accounts, transactions, payments, or risk…"
            rows={2}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </section>
    </main>
  );
}
