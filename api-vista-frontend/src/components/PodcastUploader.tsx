
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileAudio, Upload } from "lucide-react";

interface PodcastUploaderProps {
  onUpload: (file: File) => void;
}

export function PodcastUploader({ onUpload }: PodcastUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
      setSelectedFile(file);
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  return (
    <div className="space-y-6">
      <div
        className={`border-2 border-dashed rounded-lg p-8 transition-colors ${
          isDragging
            ? "border-primary bg-primary/5"
            : "border-gray-200 dark:border-gray-700"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center text-center">
            <FileAudio className="h-12 w-12 text-muted-foreground mb-4" />
            <Label htmlFor="pdf" className="text-lg font-medium">
              Drop your PDF here or click to browse
            </Label>
            <p className="text-sm text-muted-foreground mt-1">
              Supports PDF files up to 10MB
            </p>
          </div>
          <Input
            id="pdf"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          {selectedFile && (
            <p className="text-sm text-center text-muted-foreground">
              Selected: {selectedFile.name}
            </p>
          )}
        </div>
      </div>

      <Button
        onClick={handleUpload}
        disabled={!selectedFile}
        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 transition-all duration-300"
      >
        <Upload className="mr-2" />
        Upload and Convert
      </Button>
    </div>
  );
}
