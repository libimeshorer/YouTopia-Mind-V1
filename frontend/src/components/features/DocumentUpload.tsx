import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Upload, File, X, Search, Eye, Trash2, Loader2 } from "lucide-react";
import { apiClient } from "@/api/client";
import { Document } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { DocumentPreview } from "./DocumentPreview";

interface DocumentUploadProps {
  onUploadComplete?: () => void;
}

export const DocumentUpload = ({ onUploadComplete }: DocumentUploadProps) => {
  const [dragActive, setDragActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [uploadingFiles, setUploadingFiles] = useState<Map<string, number>>(new Map());
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: documents = [], isLoading } = useQuery<Document[]>({
    queryKey: ["documents"],
    queryFn: () => apiClient.documents.list(),
  });

  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      const uploadPromises = files.map(async (file) => {
        const fileId = `${file.name}-${Date.now()}`;
        setUploadingFiles((prev) => new Map(prev.set(fileId, 0)));

        try {
          // Simulate upload progress (in real implementation, this would come from the API)
          const progressInterval = setInterval(() => {
            setUploadingFiles((prev) => {
              const current = prev.get(fileId) || 0;
              if (current < 90) {
                return new Map(prev.set(fileId, current + 10));
              }
              return prev;
            });
          }, 200);

          await apiClient.documents.upload([file]);

          clearInterval(progressInterval);
          setUploadingFiles((prev) => {
            const newMap = new Map(prev);
            newMap.set(fileId, 100);
            return newMap;
          });

          setTimeout(() => {
            setUploadingFiles((prev) => {
              const newMap = new Map(prev);
              newMap.delete(fileId);
              return newMap;
            });
          }, 1000);
        } catch (error) {
          clearInterval(progressInterval);
          setUploadingFiles((prev) => {
            const newMap = new Map(prev);
            newMap.delete(fileId);
            return newMap;
          });
          throw error;
        }
      });

      await Promise.all(uploadPromises);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      onUploadComplete?.();
    },
    onSuccess: () => {
      toast({
        title: "Upload Successful",
        description: "Documents uploaded successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Upload Failed",
        description: error instanceof Error ? error.message : "Failed to upload documents",
        variant: "destructive",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.documents.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({
        title: "Document Deleted",
        description: "Document has been removed",
      });
    },
    onError: () => {
      toast({
        title: "Delete Failed",
        description: "Failed to delete document",
        variant: "destructive",
      });
    },
  });

  const searchMutation = useMutation({
    mutationFn: (query: string) => apiClient.documents.search(query),
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      const files = Array.from(e.dataTransfer.files).filter((file) => {
        const ext = file.name.split(".").pop()?.toLowerCase();
        return ["pdf", "docx", "doc", "txt"].includes(ext || "");
      });

      if (files.length > 0) {
        uploadMutation.mutate(files);
      }
    },
    [uploadMutation]
  );

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      uploadMutation.mutate(files);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchMutation.mutate(searchQuery);
    }
  };

  const filteredDocuments = searchQuery
    ? searchMutation.data || documents
    : documents;

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  const getStatusColor = (status: Document["status"]) => {
    switch (status) {
      case "complete":
        return "text-green-500";
      case "processing":
        return "text-blue-500";
      case "error":
        return "text-red-500";
      default:
        return "text-yellow-500";
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
            }`}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground mb-4">
              Drag and drop files here, or click to select
            </p>
            <p className="text-xs text-muted-foreground mb-4">
              Supported formats: PDF, DOCX, DOC, TXT
            </p>
            <Input
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt"
              onChange={handleFileInput}
              className="hidden"
              id="file-upload"
            />
            <Button
              onClick={() => document.getElementById("file-upload")?.click()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Select Files
                </>
              )}
            </Button>
          </div>

          {/* Upload Progress */}
          {Array.from(uploadingFiles.entries()).map(([fileId, progress]) => (
            <div key={fileId} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{fileId.split("-")[0]}</span>
                <span className="text-muted-foreground">{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button type="submit" variant="outline">
              Search
            </Button>
            {searchQuery && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setSearchQuery("");
                  searchMutation.reset();
                }}
              >
                Clear
              </Button>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardHeader>
          <CardTitle>Uploaded Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? "No documents found" : "No documents uploaded yet"}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <File className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{doc.name}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{formatFileSize(doc.size)}</span>
                        <span className={getStatusColor(doc.status)}>
                          {doc.status}
                        </span>
                        {doc.chunksExtracted && (
                          <span>{doc.chunksExtracted} chunks</span>
                        )}
                        <span>{new Date(doc.uploadedAt).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <DocumentPreview document={doc} />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteMutation.mutate(doc.id)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

