
import { useState, type FormEvent } from "react";
import { Send, LoaderCircle } from "lucide-react";

interface Props {
  disabled: boolean;
  sending: boolean;
  onSend: (content: string) => Promise<void>;
}

export default function ReplyComposer({
  disabled,
  sending,
  onSend,
}: Props) {
  const [content, setContent] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = content.trim();

    if (!trimmed || sending || disabled) return;

    setError("");

    try {
      await onSend(trimmed);
      setContent("");
    } catch {
      setError("Message could not be sent. Please try again.");
    }
  };

  return (
    <form className="reply-composer" onSubmit={handleSubmit}>
      {error && <div className="reply-error">{error}</div>}

      {disabled ? (
        <div className="composer-disabled">
          This conversation is closed. Reopen it to send a reply.
        </div>
      ) : (
        <>
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Write your reply..."
            rows={3}
            maxLength={10000}
            disabled={sending}
          />

          <div className="composer-footer">
            <span>Replies are sent directly to the conversation.</span>

            <button
              type="submit"
              disabled={!content.trim() || sending}
            >
              {sending ? (
                <LoaderCircle size={16} className="sf-spin" />
              ) : (
                <Send size={16} />
              )}
              {sending ? "Sending..." : "Send reply"}
            </button>
          </div>
        </>
      )}
    </form>
  );
}
