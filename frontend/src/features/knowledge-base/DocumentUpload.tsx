
import { FileUp, Upload } from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

export default function DocumentUpload({
  onUpload,
  disabled = false,
}: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  async function uploadFile(file: File) {
    setError("");
    setUploading(true);

    try {
      await onUpload(file);

      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch {
      setError("Upload failed. Please check the file and try again.");
    } finally {
      setUploading(false);
    }
  }

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (file) {
      await uploadFile(file);
    }
  }

  return (
    <div
      className={`kb-upload-area ${dragging ? "dragging" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled && !uploading) setDragging(true);
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setDragging(false);
      }}
      onDrop={async (event) => {
        event.preventDefault();
        setDragging(false);

        if (disabled || uploading) return;

        const file = event.dataTransfer.files?.[0];
        if (file) await uploadFile(file);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="kb-hidden-input"
        onChange={handleChange}
        disabled={disabled || uploading}
      />

      <div className="kb-upload-icon">
        {uploading ? <FileUp size={25} /> : <Upload size={25} />}
      </div>

      <div className="kb-upload-copy">
        <strong>
          {uploading ? "Uploading document..." : "Upload a document"}
        </strong>
        <p>Drag and drop a file here, or choose a file from your device.</p>
      </div>

      <button
        type="button"
        className="kb-button kb-button-secondary"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? "Uploading..." : "Choose file"}
      </button>

      <small>Supported file types and size limits are validated by the server.</small>

      {error && <div className="kb-inline-error">{error}</div>}
    </div>
  );
}
