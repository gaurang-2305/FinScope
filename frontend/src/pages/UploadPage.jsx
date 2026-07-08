import { useState } from "react";
import apiClient from "../api/client";

function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState(null); // "success" | "error" | null
  const [message, setMessage] = useState("");

  function handleFileChange(event) {
    setSelectedFile(event.target.files[0]);
    setStatus(null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setStatus("error");
      setMessage("Please select a file first.");
      return;
    }

    if (selectedFile.type !== "application/pdf") {
      setStatus("error");
      setMessage("Only PDF files are allowed.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await apiClient.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setStatus("success");
      setMessage(`Uploaded: ${response.data.filename} (${response.data.size} bytes)`);
    } catch (error) {
      setStatus("error");
      setMessage(
        error.response?.data?.detail || "Upload failed. Please try again."
      );
    }
  }

  return (
    <div className="p-8">
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleUpload} className="ml-4 px-4 py-2 bg-blue-600 text-white rounded">
        Upload
      </button>
      {status === "success" && <p className="text-green-600 mt-4">{message}</p>}
      {status === "error" && <p className="text-red-600 mt-4">{message}</p>}
    </div>
  );
}

export default UploadPage;