import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Eye, Loader2, FileText } from "lucide-react";
import { Document } from "@/types";
import { apiClient } from "@/api/client";
import { useQuery } from "@tanstack/react-query";

interface DocumentPreviewProps {
  document: Document;
}

export const DocumentPreview = ({ document }: DocumentPreviewProps) => {
  const [open, setOpen] = useState(false);

  const { data: previewData, isLoading } = useQuery<{ url: string }>({
    queryKey: ["documentPreview", document.id],
    queryFn: () => apiClient.documents.preview(document.id),
    enabled: open && document.status === "complete",
  });

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen(true)}
        disabled={document.status !== "complete"}
      >
        <Eye className="w-4 h-4" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>{document.name}</DialogTitle>
            <DialogDescription>
              Preview of {document.name} ({document.type})
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading preview...</span>
              </div>
            ) : previewData?.url ? (
              <div className="space-y-4">
                {document.type.toLowerCase().includes("pdf") ? (
                  <iframe
                    src={previewData.url}
                    className="w-full h-[600px] border rounded"
                    title={document.name}
                  />
                ) : (
                  <div className="p-4 border rounded bg-muted">
                    <FileText className="w-8 h-8 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-center text-muted-foreground">
                      Preview not available for this file type. Download to view.
                    </p>
                  </div>
                )}
              </div>
            ) : document.status !== "complete" ? (
              <div className="text-center py-12 text-muted-foreground">
                <p>Document is still processing. Preview will be available once processing is complete.</p>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <p>Preview not available for this document.</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

