interface AssistantPanelProps {
  open: boolean;
  onClose: () => void;
}

export function AssistantPanel({ open, onClose }: AssistantPanelProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="assistant-layer">
      <button
        type="button"
        className="assistant-backdrop"
        aria-label="Close assistant"
        onClick={onClose}
      />
      <aside
        className="assistant-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="assistant-title"
      >
        <div className="assistant-panel-header">
          <div>
            <p className="page-kicker">Assistant</p>
            <h2 id="assistant-title">AI assistant</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            Close
          </button>
        </div>
        <p>
          The assistant is an entry point only in this milestone. It is not
          connected to a model, research jobs, or dataset search.
        </p>
      </aside>
    </div>
  );
}
