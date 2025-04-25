import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PodcastUploader } from "@/components/PodcastUploader";
import { PodcastProgress } from "@/components/PodcastProgress";
import { toast } from "@/components/ui/sonner";

// Base URL for backend API; fallback ensures correct port if env var missing
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const Index = () => {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append("pdf_file", file);

    try {
      const response = await fetch(`${API_BASE}/create-podcast`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to upload file");
      }

      const data = await response.json();
      setCurrentTaskId(data.task_id);
      toast.success("PDF uploaded successfully");
    } catch (error) {
      console.error("Error uploading file:", error);
      toast.error("Failed to upload PDF");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="text-center space-y-4 mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            PDF to Podcast Converter
          </h1>
          <p className="text-muted-foreground">
            Transform your PDFs into engaging audio content
          </p>
        </div>

        <Card className="backdrop-blur-sm bg-white/80 dark:bg-gray-900/80 border-0 shadow-lg">
          <CardHeader className="text-center">
            <CardTitle>Upload Your PDF</CardTitle>
          </CardHeader>
          <CardContent>
            <PodcastUploader onUpload={handleUpload} />
            {isUploading && <p className="text-center mt-2">Uploading PDF...</p>}
          </CardContent>
        </Card>

        {currentTaskId && <PodcastProgress taskId={currentTaskId} />}
      </div>
    </div>
  );
};

export default Index;
