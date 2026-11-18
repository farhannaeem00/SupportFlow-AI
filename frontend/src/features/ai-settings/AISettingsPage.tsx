
import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Bot, Brain, Save, ShieldCheck, SlidersHorizontal, Sparkles } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { aiSettingsApi } from "./aiSettingsApi";
import type { AISettings } from "./types";
import "./AISettings.css";

const defaultSettings: AISettings = {
  ai_enabled: true,
  suggestions_enabled: true,
  confidence_threshold: 0.6,
  escalation_priority_level: 3,
  max_context_messages: 20,
};

const priorityLabels: Record<number, string> = {
  1: "Low",
  2: "Normal",
  3: "High",
  4: "Urgent",
};

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Something went wrong. Please try again."
    );
  }

  return "Something went wrong. Please try again.";
}

export default function AISettingsPage() {
  const { organization, organizations } = useAuth();

  const currentMembership = organizations.find(
    (item) => item.id === organization?.id
  );

  const canManage = currentMembership?.role?.toLowerCase() === "owner";

  const [settings, setSettings] = useState<AISettings>(defaultSettings);
  const [savedSettings, setSavedSettings] =
    useState<AISettings>(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await aiSettingsApi.getSettings();
      setSettings(data);
      setSavedSettings(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const updateField = <K extends keyof AISettings>(
    field: K,
    value: AISettings[K]
  ) => {
    setSettings((current) => ({
      ...current,
      [field]: value,
    }));
    setSuccess("");
  };

  const hasChanges =
    JSON.stringify(settings) !== JSON.stringify(savedSettings);

  const handleSave = async () => {
    if (!canManage || !hasChanges || saving) return;

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updated = await aiSettingsApi.updateSettings(settings);
      setSettings(updated);
      setSavedSettings(updated);
      setSuccess("AI settings saved successfully.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSettings(savedSettings);
    setError("");
    setSuccess("");
  };

  if (loading) {
    return (
      <div className="ai-settings-page">
        <div className="ai-settings-loading">
          <div className="ai-settings-spinner" />
          <p>Loading AI settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-settings-page">
      <div className="ai-settings-header">
        <div>
          <div className="ai-settings-eyebrow">
            <Sparkles size={15} />
            WORKSPACE CONFIGURATION
          </div>
          <h1>AI Settings</h1>
          <p>
            Control how AI handles customer conversations and assists your
            support team.
          </p>
        </div>

        <div className="ai-settings-header-icon">
          <Bot size={27} />
        </div>
      </div>

      {error && (
        <div className="ai-settings-alert ai-settings-alert-error">
          {error}
        </div>
      )}

      {success && (
        <div className="ai-settings-alert ai-settings-alert-success">
          {success}
        </div>
      )}

      {!canManage && (
        <div className="ai-settings-readonly-notice">
          <ShieldCheck size={18} />
          <span>
            You can view these settings, but only workspace owners can change
            them.
          </span>
        </div>
      )}

      <div className="ai-settings-content">
        <section className="ai-settings-card">
          <div className="ai-settings-card-heading">
            <div className="ai-settings-card-icon">
              <Brain size={20} />
            </div>
            <div>
              <h2>AI assistant</h2>
              <p>Enable or disable automated AI assistance.</p>
            </div>
          </div>

          <div className="ai-settings-option">
            <div className="ai-settings-option-copy">
              <h3>Enable AI responses</h3>
              <p>
                Allow the AI assistant to process eligible customer
                conversations.
              </p>
            </div>

            <button
              type="button"
              className={`ai-settings-toggle ${
                settings.ai_enabled ? "is-enabled" : ""
              }`}
              role="switch"
              aria-checked={settings.ai_enabled}
              aria-label="Enable AI responses"
              disabled={!canManage}
              onClick={() => updateField("ai_enabled", !settings.ai_enabled)}
            >
              <span />
            </button>
          </div>

          <div className="ai-settings-option">
            <div className="ai-settings-option-copy">
              <h3>Agent suggestions</h3>
              <p>
                Allow AI-generated suggestions to assist agents during
                customer support.
              </p>
            </div>

            <button
              type="button"
              className={`ai-settings-toggle ${
                settings.suggestions_enabled ? "is-enabled" : ""
              }`}
              role="switch"
              aria-checked={settings.suggestions_enabled}
              aria-label="Enable agent suggestions"
              disabled={!canManage}
              onClick={() =>
                updateField(
                  "suggestions_enabled",
                  !settings.suggestions_enabled
                )
              }
            >
              <span />
            </button>
          </div>
        </section>

        <section className="ai-settings-card">
          <div className="ai-settings-card-heading">
            <div className="ai-settings-card-icon">
              <SlidersHorizontal size={20} />
            </div>
            <div>
              <h2>Response configuration</h2>
              <p>Fine-tune AI response behavior for your workspace.</p>
            </div>
          </div>

          <div className="ai-settings-field">
            <div className="ai-settings-field-heading">
              <div>
                <h3>Confidence threshold</h3>
                <p>
                  Minimum confidence required for the AI to act on its
                  response.
                </p>
              </div>
              <strong>
                {Math.round(settings.confidence_threshold * 100)}%
              </strong>
            </div>

            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={settings.confidence_threshold}
              disabled={!canManage}
              onChange={(event) =>
                updateField(
                  "confidence_threshold",
                  Number(event.target.value)
                )
              }
            />

            <div className="ai-settings-range-labels">
              <span>More flexible</span>
              <span>More conservative</span>
            </div>
          </div>

          <div className="ai-settings-field">
            <label htmlFor="escalation-priority">
              Escalation priority level
            </label>
            <p>
              Priority assigned when a conversation requires escalation.
            </p>

            <select
              id="escalation-priority"
              value={settings.escalation_priority_level}
              disabled={!canManage}
              onChange={(event) =>
                updateField(
                  "escalation_priority_level",
                  Number(event.target.value)
                )
              }
            >
              {Object.entries(priorityLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="ai-settings-field">
            <div className="ai-settings-field-heading">
              <div>
                <label htmlFor="max-context-messages">
                  Conversation context messages
                </label>
                <p>
                  Maximum previous messages included in AI conversation
                  context.
                </p>
              </div>
              <strong>{settings.max_context_messages}</strong>
            </div>

            <input
              id="max-context-messages"
              type="range"
              min="1"
              max="50"
              step="1"
              value={settings.max_context_messages}
              disabled={!canManage}
              onChange={(event) =>
                updateField(
                  "max_context_messages",
                  Number(event.target.value)
                )
              }
            />

            <div className="ai-settings-range-labels">
              <span>1 message</span>
              <span>50 messages</span>
            </div>
          </div>
        </section>

        <div className="ai-settings-footer">
          <p>
            Changes apply to your workspace's AI behavior after they are saved.
          </p>

          {canManage && (
            <div className="ai-settings-actions">
              <button
                type="button"
                className="ai-settings-reset-button"
                disabled={!hasChanges || saving}
                onClick={handleReset}
              >
                Discard changes
              </button>

              <button
                type="button"
                className="ai-settings-save-button"
                disabled={!hasChanges || saving}
                onClick={handleSave}
              >
                <Save size={16} />
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
