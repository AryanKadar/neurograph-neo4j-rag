import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Rocket, Upload, FileText, CheckCircle, X, Loader2, ExternalLink } from 'lucide-react';
import ChatMessage, { Message } from './ChatMessage';
import ChatInput from './ChatInput';
import CosmicLoader from './CosmicLoader';
import { Button } from './ui/button';

// ═══════════════════════════════════════════════════════════════
//  🌌 API Configuration
// ═══════════════════════════════════════════════════════════════

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface UploadedFile {
  id: string;
  name: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  statusMessage?: string;
  error?: string;
}

// ═══════════════════════════════════════════════════════════════
//  📄 Document Inline Preview Component
// ═══════════════════════════════════════════════════════════════

const DocumentInlinePreview = ({ filename, fileId }: { filename: string; fileId: string }) => {
  const isPdf = filename.toLowerCase().endsWith('.pdf');
  const previewUrl = `${API_BASE_URL}/api/documents/${fileId}/view`;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      className="mt-3 overflow-hidden rounded-xl border border-cosmic-cyan/20 bg-black/40 backdrop-blur-md shadow-[0_0_15px_rgba(6,182,212,0.1)]"
    >
      <div className="flex items-center justify-between p-2 px-3 bg-cosmic-cyan/10 border-b border-cosmic-cyan/10 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-cosmic-cyan" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-cosmic-cyan/80">
            Document Content Insight
          </span>
        </div>
        <a href={previewUrl} target="_blank" rel="noreferrer">
          <Button size="icon" variant="ghost" className="h-6 w-6 text-cosmic-cyan/60 hover:text-cosmic-cyan">
            <ExternalLink size={12} />
          </Button>
        </a>
      </div>

      <div className="w-full h-48 bg-white/5 backdrop-blur-sm">
        {isPdf ? (
          <iframe
            src={`${previewUrl}#toolbar=0&navpanes=0`}
            className="w-full h-full border-none opacity-90"
            title={filename}
          />
        ) : (
          <iframe
            src={previewUrl}
            className="w-full h-full border-none opacity-90 bg-white/10"
            title={filename}
          />
        )}
      </div>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════
//  📤 Document Upload Component
// ═══════════════════════════════════════════════════════════════

const DocumentUpload = ({
  onFileUploaded
}: {
  onFileUploaded: (fileId: string, filename: string) => void
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    const tempId = `temp-${Date.now()}`;

    // Add to upload list
    setFiles(prev => [...prev, { id: tempId, name: file.name, status: 'uploading' }]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();

      // Update status to processing
      setFiles(prev => prev.map(f =>
        f.id === tempId
          ? { ...f, id: data.file_id, status: 'processing' }
          : f
      ));

      // Poll for completion
      pollStatus(data.file_id, tempId);

    } catch (error) {
      console.error('Upload error:', error);
      setFiles(prev => prev.map(f =>
        f.id === tempId
          ? { ...f, status: 'error', error: 'Upload failed - check server connection' }
          : f
      ));
    }
  };

  const pollStatus = async (fileId: string, tempId: string) => {
    let attempts = 0;
    const maxAttempts = 300; // Increased to 5 minutes for deep graph analysis

    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/analyze/status/${fileId}`);

        if (!response.ok) {
          // If backend error, keep polling a few times, then fail?
          // For now, assume temporary glitch and retry
        } else {
          const data = await response.json();

          if (data.status === 'completed') {
            setFiles(prev => prev.map(f =>
              f.id === fileId || f.id === tempId
                ? { ...f, id: fileId, status: 'completed', statusMessage: 'Ready' }
                : f
            ));

            // Notify parent
            const file = files.find(f => f.id === tempId || f.id === fileId);
            if (file) {
              onFileUploaded(fileId, file.name);
            }
            return;
          } else if (data.status === 'failed') {
            setFiles(prev => prev.map(f =>
              f.id === fileId || f.id === tempId
                ? { ...f, id: fileId, status: 'error', error: data.error || 'Processing failed' }
                : f
            ));
            return;
          }
        }

        attempts++;
        if (attempts < maxAttempts) {
          // Update status message for long waits
          if (attempts > 10 && attempts % 5 === 0) {
            setFiles(prev => prev.map(f =>
              f.id === fileId || f.id === tempId
                ? { ...f, statusMessage: 'Extracting knowledge graph... this can take a minute' }
                : f
            ));
          }
          if (attempts > 30 && attempts % 10 === 0) {
            setFiles(prev => prev.map(f =>
              f.id === fileId || f.id === tempId
                ? { ...f, statusMessage: 'Still analyzing deep connections...' }
                : f
            ));
          }

          setTimeout(checkStatus, 1000);
        } else {
          setFiles(prev => prev.map(f =>
            f.id === fileId || f.id === tempId
              ? { ...f, status: 'error', error: 'Processing timed out' }
              : f
          ));
        }
      } catch (error) {
        console.error('Status check failed:', error);
        // Retry even on network error
        attempts++;
        if (attempts < maxAttempts) setTimeout(checkStatus, 2000);
      }
    };

    checkStatus();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    droppedFiles.forEach(handleFileUpload);
  };

  const handleRemove = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="mb-4">
      {/* Drop zone */}
      <motion.div
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          p-4 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-300
          ${isDragOver
            ? 'border-cosmic-cyan bg-cosmic-cyan/10'
            : 'border-border/50 hover:border-cosmic-cyan/50 bg-card/30'
          }
        `}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.docx,.md"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileUpload(file);
          }}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Upload className={`w-8 h-8 ${isDragOver ? 'text-cosmic-cyan' : ''}`} />
          <p className="text-sm">
            Drop a document here or <span className="text-cosmic-cyan">click to browse</span>
          </p>
          <p className="text-xs opacity-60">Supports PDF, TXT, DOCX, MD</p>
        </div>
      </motion.div>

      {/* File list with inline preview */}
      <AnimatePresence>
        {files.map(file => (
          <div key={file.id}>
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-2 p-3 rounded-lg bg-card/50 border border-border/50 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-cosmic-cyan" />
                <div>
                  <p className="text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {file.status === 'error' ? file.error : (file.statusMessage || file.status)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {file.status === 'uploading' && (
                  <Loader2 className="w-4 h-4 animate-spin text-cosmic-cyan" />
                )}
                {file.status === 'processing' && (
                  <Loader2 className="w-4 h-4 animate-spin text-yellow-500" />
                )}
                {file.status === 'completed' && (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                )}
                {file.status === 'error' && (
                  <X className="w-4 h-4 text-red-500" />
                )}

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRemove(file.id)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </motion.div>

            {/* Inline Preview when completed */}
            {file.status === 'completed' && (
              <DocumentInlinePreview filename={file.name} fileId={file.id} />
            )}
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
//  💬 Main Chat Container
// ═══════════════════════════════════════════════════════════════

const ChatContainer = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeFileId, setActiveFileId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleFileUploaded = (fileId: string, filename: string) => {
    setActiveFileId(fileId);

    // Add system message about the upload
    const systemMessage: Message = {
      id: `system-${Date.now()}`,
      role: 'assistant',
      content: `📄 **Document Ready!**\n\nI've analyzed "${filename}" and I'm ready to answer questions about it. What would you like to know?`,
    };
    setMessages(prev => [...prev, systemMessage]);
  };

  const handleSend = async (content: string) => {
    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantId = `assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };

    setTimeout(() => {
      setMessages((prev) => [...prev, assistantMessage]);
    }, 300);

    try {
      // Build history for context
      const history = messages.slice(-10).map(m => ({
        role: m.role,
        content: m.content
      }));

      // Stream response from backend
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: content,
          history,
          use_rag: true,
          file_ids: activeFileId ? [activeFileId] : null
        })
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.content) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? { ...msg, content: msg.content + data.content }
                        : msg
                    )
                  );
                }

                if (data.done) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? { ...msg, isStreaming: false }
                        : msg
                    )
                  );
                }

                if (data.error) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? { ...msg, content: `Error: ${data.error}`, isStreaming: false }
                        : msg
                    )
                  );
                }
              } catch (e) {
                // Skip malformed JSON
              }
            }
          }
        }
      }

    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: 'Sorry, I encountered an error. Please try again.', isStreaming: false }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-shrink-0 px-4 py-4 border-b border-border/30 bg-card/30 backdrop-blur-xl"
      >
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <motion.div
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-cosmic-cyan via-cosmic-purple to-cosmic-pink flex items-center justify-center animate-cosmic-pulse"
            whileHover={{ scale: 1.05 }}
          >
            <Sparkles className="w-5 h-5 text-foreground" />
          </motion.div>
          <div>
            <h1 className="font-display text-lg font-semibold text-glow-cyan tracking-wide">
              COSMIC AI
            </h1>
            <p className="text-xs text-muted-foreground">
              {activeFileId ? '📄 Document loaded - Ask me anything!' : 'Upload a document to get started'}
            </p>
          </div>
        </div>
      </motion.header>

      {/* Messages area */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto cosmic-scrollbar px-4 py-6"
      >
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="flex flex-col items-center justify-center min-h-[400px] text-center"
            >
              <motion.div
                className="mb-6"
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              >
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-cosmic-cyan via-cosmic-purple to-cosmic-pink p-1 animate-cosmic-pulse">
                  <div className="w-full h-full rounded-xl bg-card flex items-center justify-center">
                    <Rocket className="w-10 h-10 text-cosmic-cyan" />
                  </div>
                </div>
              </motion.div>

              <h2 className="font-display text-2xl md:text-3xl font-bold mb-3 bg-gradient-to-r from-cosmic-cyan via-cosmic-purple to-cosmic-pink bg-clip-text text-transparent">
                Welcome to Cosmic AI
              </h2>
              <p className="text-muted-foreground max-w-md mb-8 leading-relaxed">
                Upload a document and I'll help you explore its contents.
                Ask me anything about your uploaded files!
              </p>

              {/* Document Upload */}
              <div className="w-full max-w-md">
                <DocumentUpload onFileUploaded={handleFileUploaded} />
              </div>
            </motion.div>
          ) : (
            <>
              {/* Show upload when there are messages */}
              <div className="mb-4">
                <DocumentUpload onFileUploaded={handleFileUploaded} />
              </div>

              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isLatest={index === messages.length - 1}
                />
              ))}

              {isLoading && messages[messages.length - 1]?.role === 'user' && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3 mb-4"
                >
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-cosmic-purple to-cosmic-pink flex items-center justify-center glow-purple">
                    <Sparkles className="w-5 h-5 text-foreground" />
                  </div>
                  <div className="message-bot">
                    <div className="flex items-center gap-3">
                      <CosmicLoader size="sm" />
                      <span className="text-muted-foreground text-sm">
                        Searching the cosmos...
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 px-4 py-4 bg-gradient-to-t from-background via-background to-transparent">
        <div className="max-w-4xl mx-auto">
          <ChatInput onSend={handleSend} isLoading={isLoading} />
          <p className="text-center text-xs text-muted-foreground/60 mt-3">
            Cosmic AI answers based on your uploaded documents only.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatContainer;
