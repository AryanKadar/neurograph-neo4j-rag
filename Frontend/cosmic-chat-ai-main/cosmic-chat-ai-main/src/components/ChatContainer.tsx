
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Rocket, Upload, FileText, CheckCircle, X, Loader2, ExternalLink, Zap } from 'lucide-react';
import ChatMessage, { Message } from './ChatMessage';
import ChatInput from './ChatInput';
import CosmicLoader from './CosmicLoader';
import { Button } from './ui/button';
import { Progress } from './ui/progress';

// ═══════════════════════════════════════════════════════════════
//  🌌 API Configuration
// ═══════════════════════════════════════════════════════════════

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ProcessingState {
  fileId: string;
  filename: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  stage?: string;
  progress: number;
  substage?: string;
  error?: string;
}

// ═══════════════════════════════════════════════════════════════
//  📊 Cool Processing Status Bar (Floating)
// ═══════════════════════════════════════════════════════════════

const ProcessingStatus = ({ state }: { state: ProcessingState | null }) => {
  if (!state || state.status === 'completed') return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 100, opacity: 0, scale: 0.95 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 100, opacity: 0, scale: 0.95 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4"
      >
        <div className="bg-card/90 backdrop-blur-xl border border-cosmic-cyan/30 rounded-2xl shadow-[0_0_30px_rgba(6,182,212,0.2)] p-4 overflow-hidden relative">
          {/* Animated Background Gradient */}
          <div className="absolute inset-0 bg-gradient-to-r from-cosmic-cyan/10 via-cosmic-purple/10 to-cosmic-pink/10 animate-pulse" />

          <div className="relative flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-cosmic-cyan/20 flex items-center justify-center">
                {state.status === 'uploading' ? (
                  <Upload className="w-4 h-4 text-cosmic-cyan animate-bounce" />
                ) : state.status === 'error' ? (
                  <X className="w-4 h-4 text-red-500" />
                ) : (
                  <Zap className="w-4 h-4 text-yellow-400 animate-pulse" />
                )}
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-foreground">
                  {state.filename}
                </span>
                <span className="text-xs text-cosmic-cyan font-medium">
                  {state.error || state.stage || 'Initializing...'}
                </span>
              </div>
            </div>
            <span className="text-xs font-bold font-mono text-muted-foreground">
              {state.progress}%
            </span>
          </div>

          <Progress value={state.progress} className="h-1.5 bg-muted/50" indicatorClassName="bg-gradient-to-r from-cosmic-cyan to-cosmic-purple" />

          {state.substage && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-[10px] text-muted-foreground mt-2 text-center"
            >
              {state.substage}
            </motion.p>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

// ═══════════════════════════════════════════════════════════════
//  📤 Document Upload Component (Simplified)
// ═══════════════════════════════════════════════════════════════

const DocumentUpload = ({
  onUploadStart,
  disabled,
  statusText
}: {
  onUploadStart: (file: File) => void;
  disabled: boolean;
  statusText?: string;
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files?.[0]) {
      onUploadStart(e.dataTransfer.files[0]);
    }
  };

  return (
    <motion.div
      onDragOver={(e) => { if (!disabled) { e.preventDefault(); setIsDragOver(true); } }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && fileInputRef.current?.click()}
      className={`
        p-4 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-300
        ${disabled ? 'opacity-50 cursor-not-allowed border-border/30' : ''}
        ${isDragOver
          ? 'border-cosmic-cyan bg-cosmic-cyan/10'
          : 'border-border/50 hover:border-cosmic-cyan/50 bg-card/30'
        }
      `}
      whileHover={!disabled ? { scale: 1.01 } : {}}
      whileTap={!disabled ? { scale: 0.99 } : {}}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.docx,.md"
        onChange={(e) => e.target.files?.[0] && onUploadStart(e.target.files[0])}
        className="hidden"
        disabled={disabled}
      />

      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <Upload className={`w-8 h-8 ${isDragOver ? 'text-cosmic-cyan' : ''}`} />
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">
            {disabled ? (statusText || 'System Not Ready') : 'Drop document here'}
          </p>
          <p className="text-xs opacity-60">or click to browse</p>
        </div>
      </div>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════
//  💬 Main Chat Container
// ═══════════════════════════════════════════════════════════════

const ChatContainer = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeFileId, setActiveFileId] = useState<string | null>(null);
  const [backendReady, setBackendReady] = useState(false);

  // Centralized Processing State
  const [procState, setProcState] = useState<ProcessingState | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => scrollToBottom(), [messages]);

  // 1. Check Backend on Mount
  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/health`);
        if (mounted && res.ok) setBackendReady(true);
        else if (mounted) setTimeout(check, 2000);
      } catch {
        if (mounted) setTimeout(check, 2000);
      }
    };
    check();
    return () => { mounted = false; };
  }, []);

  // 2. Handle File Upload
  const handleUploadStart = async (file: File) => {
    // Set initial state
    setProcState({
      fileId: '',
      filename: file.name,
      status: 'uploading',
      progress: 0,
      stage: 'Uploading to server...'
    });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE_URL}/api/upload`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Upload failed');

      const data = await res.json();

      // Update state with ID and start processing
      setProcState(prev => prev ? {
        ...prev,
        fileId: data.file_id,
        status: 'processing',
        stage: 'Initializing analysis...',
        progress: 5
      } : null);

    } catch (error) {
      console.error(error);
      setProcState(prev => prev ? {
        ...prev,
        status: 'error',
        error: 'Upload failed',
        stage: 'Error'
      } : null);

      // Clear error after 3s
      setTimeout(() => setProcState(null), 3000);
    }
  };

  // 3. WebSocket Logic for Processing State
  useEffect(() => {
    if (!procState?.fileId || procState.status !== 'processing') return;

    // Construct WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use the API_BASE_URL but replace http/https with ws/wss, or handle relative URLs
    const baseUrl = API_BASE_URL.replace(/^http/, 'ws');
    const wsUrl = `${baseUrl}/api/ws/progress/${procState.fileId}`;

    console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ WebSocket Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('📊 Progress Update:', data);

        if (data.stage === 'completed') {
          // SUCCESS
          setActiveFileId(procState.fileId);
          setProcState(prev => prev ? { ...prev, status: 'completed', progress: 100 } : null);

          setMessages(prev => [...prev, {
            id: `system-${Date.now()}`,
            role: 'assistant',
            content: `📄 **Document Ready!**\n\nI've analyzed "${data.filename || 'your document'}". Ask me anything!`
          }]);

          ws.close();
        } else if (data.stage === 'failed') {
          // FAILURE
          setProcState(prev => prev ? { ...prev, status: 'error', error: data.error || 'Processing failed' } : null);
          ws.close();
        } else {
          // UPDATE
          setProcState(prev => {
            if (!prev) return null;
            return {
              ...prev,
              stage: data.stage_display || data.stage, // "Parsing Document", "Chunking...", etc.
              progress: data.progress || prev.progress,
              substage: data.details?.substage // "Batch 1/5", etc.
            };
          });
        }
      } catch (err) {
        console.error('WebSocket message error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Fallback or just let it hang in 'error' state for now? 
      // If WS fails, we might want to try one polling check just in case, or show error.
      // But usually if WS fails, the backend is down.
    };

    ws.onclose = () => {
      console.log('🔌 WebSocket Disconnected');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [procState?.fileId, procState?.status]);


  // 5. Chat Logic
  const handleSend = async (content: string) => {
    const userMsg: Message = { id: `user-${Date.now()}`, role: 'user', content };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    const assistantId = `ai-${Date.now()}`;
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', isStreaming: true };
    setTimeout(() => setMessages(prev => [...prev, assistantMsg]), 300);

    try {
      const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: content,
          history,
          use_rag: true,
          file_ids: activeFileId ? [activeFileId] : null
        })
      });

      if (!res.ok) throw new Error('Failed');

      const reader = res.body?.getReader();
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
                  setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + data.content } : m));
                }
                if (data.done || data.error) {
                  setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, isStreaming: false, content: data.error ? `Error: ${data.error}` : m.content } : m));
                }
              } catch { }
            }
          }
        }
      }
    } catch {
      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, isStreaming: false, content: "Sorry, I couldn't reach the stars." } : m));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* 1. Header */}
      <header className="flex-shrink-0 px-4 py-4 border-b border-border/30 bg-card/30 backdrop-blur-xl flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cosmic-cyan to-cosmic-purple flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <h1 className="font-display text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-cosmic-cyan to-cosmic-pink">
          COSMIC AI
        </h1>
      </header>

      {/* 2. Chat Area */}
      <div className="flex-1 overflow-y-auto cosmic-scrollbar px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
              <Rocket className="w-16 h-16 text-cosmic-cyan/50 mb-6 animate-pulse" />
              <h2 className="text-3xl font-bold mb-2">Welcome to Cosmic AI</h2>
              <p className="text-muted-foreground mb-8">Upload a document to begin your journey</p>
              <div className="w-full max-w-sm">
                <DocumentUpload
                  onUploadStart={handleUploadStart}
                  disabled={!backendReady || procState?.status === 'processing' || procState?.status === 'uploading'}
                  statusText={!backendReady ? "System Offline" : (procState?.status === 'processing' || procState?.status === 'uploading') ? "Processing..." : "System Not Ready"}
                />
              </div>
            </div>
          ) : (
            <>
              <div className="flex justify-end mb-4">
                {/* Small upload button if we already have messages */}
                {!procState && activeFileId && (
                  <div className="w-64">
                    <DocumentUpload onUploadStart={handleUploadStart} disabled={false} />
                  </div>
                )}
              </div>
              {messages.map((m, i) => (
                <ChatMessage key={m.id} message={m} isLatest={i === messages.length - 1} />
              ))}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 3. Status Bar (Cool & Floating) */}
      <ProcessingStatus state={procState} />

      {/* 4. Input Area */}
      <div className="flex-shrink-0 px-4 py-4 bg-gradient-to-t from-background to-transparent relative z-10">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            onSend={handleSend}
            isLoading={isLoading}
            disabled={!activeFileId || (procState?.status === 'processing')}
          />
          <p className="text-center text-[10px] text-muted-foreground/40 mt-2 uppercase tracking-widest">
            {backendReady ? 'System Online' : 'Connecting...'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatContainer;
