import { useRef, useState } from "react";
import { importStatementPdf } from "../services/api";

const STATUS = {
  IDLE: "idle",
  UPLOADING: "uploading",
  SUCCESS: "success",
  ERROR: "error",
};

export default function UploadStatement({ onImportSuccess }) {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState(STATUS.IDLE);
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  function resetForNewFile(file) {
    setSelectedFile(file);
    setStatus(STATUS.IDLE);
    setResult(null);
    setErrorMessage(null);
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (file) resetForNewFile(file);
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) resetForNewFile(file);
  }

  function handleDragOver(event) {
    event.preventDefault();
    setDragActive(true);
  }

  function handleDragLeave() {
    setDragActive(false);
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setStatus(STATUS.UPLOADING);
    setErrorMessage(null);

    try {
      const response = await importStatementPdf(selectedFile);
      setResult(response);
      setStatus(STATUS.SUCCESS);
      onImportSuccess?.(response);
    } catch (err) {
      setErrorMessage(err.message || "Import failed.");
      setStatus(STATUS.ERROR);
    }
  }

  function handleChooseAnother() {
    setSelectedFile(null);
    setStatus(STATUS.IDLE);
    setResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div
      className={`upload-card ${dragActive ? "drag-active" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <div className="upload-info">
        <div className="upload-icon">
          <UploadIcon />
        </div>
        <div>
          <div className="upload-title">Upload Statement</div>
          <div className="upload-subtitle">
            PhonePe, Paytm, or GPay monthly transaction PDF — drag &amp; drop or browse
          </div>
          {selectedFile && status !== STATUS.SUCCESS && (
            <div className="upload-filename">{selectedFile.name}</div>
          )}
        </div>
      </div>

      <div className="upload-actions">
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />

        {status === STATUS.SUCCESS ? (
          <button className="upload-button" onClick={handleChooseAnother}>
            Upload Another
          </button>
        ) : (
          <>
            <button
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={status === STATUS.UPLOADING}
            >
              {selectedFile ? "Change File" : "Choose File"}
            </button>
            <button
              className="upload-button primary"
              onClick={handleUpload}
              disabled={!selectedFile || status === STATUS.UPLOADING}
            >
              {status === STATUS.UPLOADING ? (
                <>
                  <span className="upload-spinner" /> Analyzing…
                </>
              ) : (
                "Import"
              )}
            </button>
          </>
        )}
      </div>

      {status === STATUS.SUCCESS && result && (
        <div className="upload-status-line success">
          {result.imported === 0 && result.skipped_duplicates > 0 ? (
            <>
              No new transactions were added — every row in this statement was already imported
              {result.failed_rows > 0 && ` · ${result.failed_rows} row(s) could not be read`}
            </>
          ) : (
            <>
              {result.imported} transaction{result.imported === 1 ? "" : "s"} imported
              {result.skipped_duplicates > 0 &&
                ` · ${result.skipped_duplicates} duplicate${result.skipped_duplicates === 1 ? "" : "s"} skipped`}
              {result.failed_rows > 0 && ` · ${result.failed_rows} row(s) could not be read`}
            </>
          )}
        </div>
      )}

      {status === STATUS.SUCCESS && result?.warnings?.length > 0 && (
        <div className="upload-status-line warning">{result.warnings.join(" ")}</div>
      )}

      {status === STATUS.ERROR && (
        <div className="upload-status-line error">{errorMessage}</div>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 16V4M12 4L7 9M12 4l5 5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v3a2 2 0 002 2h12a2 2 0 002-2v-3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}