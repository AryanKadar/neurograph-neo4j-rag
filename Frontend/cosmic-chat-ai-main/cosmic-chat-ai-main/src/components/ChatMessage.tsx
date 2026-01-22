import { memo, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import CosmicLoader from './CosmicLoader';
import 'highlight.js/styles/atom-one-dark.css';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  metadata?: {
    chunks_used?: number;
    response_time_ms?: number;
    model?: string;
  };
}

interface ChatMessageProps {
  message: Message;
  isLatest?: boolean;
}

const LOADING_MESSAGES = [
  "Consulting the star charts... 🌟",
  "Asking a black hole for directions... ⚫",
  "Decoding nebula signals... 📡",
  "Traversing the event horizon... 🚀",
  "Aligning the cosmic crystals... 💎",
  "Downloading knowledge from the void... 🌌",
  "Warping through spacetime... ⏳",
  "Polishing the telescope lenses... 🔭"
];

const ChatMessage = memo(({ message, isLatest }: ChatMessageProps) => {
  const isUser = message.role === 'user';
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0]);

  useEffect(() => {
    if (!message.isStreaming || message.content) return;

    // Rotate messages
    const interval = setInterval(() => {
      setLoadingMessage(prev => {
        const nextIdx = (LOADING_MESSAGES.indexOf(prev) + 1) % LOADING_MESSAGES.length;
        return LOADING_MESSAGES[nextIdx];
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [message.isStreaming, message.content]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-6`}
    >
      {/* Avatar */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${isUser
          ? 'bg-gradient-to-br from-cosmic-cyan to-cosmic-purple glow-cyan'
          : 'bg-gradient-to-br from-cosmic-purple to-cosmic-pink glow-purple'
          }`}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Sparkles className="w-5 h-5 text-white" />
        )}
      </motion.div>

      {/* Message Content */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.15 }}
        className={`flex-1 max-w-[85%] md:max-w-[75%] ${isUser ? 'message-user' : 'message-bot'
          }`}
      >
        {message.isStreaming && !message.content ? (
          /* Loading State */
          <div className="flex items-center gap-3 py-2">
            <CosmicLoader size="sm" />
            <span className="text-muted-foreground text-sm animate-pulse">
              {loadingMessage}
            </span>
          </div>
        ) : (
          /* Actual Message Content */
          <div className="prose prose-invert prose-sm max-w-none">
            {isUser ? (
              /* Simple text for user messages */
              <p className="text-foreground leading-relaxed whitespace-pre-wrap m-0">
                {message.content}
              </p>
            ) : (
              /* Markdown rendering for AI responses */
              <div className="markdown-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight, rehypeRaw]}
                  components={{
                    // Custom styling for markdown elements
                    h1: ({ node, ...props }) => (
                      <h1 className="text-2xl font-bold mb-4 mt-6 text-cosmic-cyan border-b border-cosmic-cyan/30 pb-2" {...props} />
                    ),
                    h2: ({ node, ...props }) => (
                      <h2 className="text-xl font-bold mb-3 mt-5 text-cosmic-purple" {...props} />
                    ),
                    h3: ({ node, ...props }) => (
                      <h3 className="text-lg font-semibold mb-2 mt-4 text-cosmic-pink" {...props} />
                    ),
                    p: ({ node, ...props }) => (
                      <p className="mb-3 leading-7 text-foreground" {...props} />
                    ),
                    ul: ({ node, ...props }) => (
                      <ul className="list-disc list-inside mb-4 space-y-2 text-foreground" {...props} />
                    ),
                    ol: ({ node, ...props }) => (
                      <ol className="list-decimal list-inside mb-4 space-y-2 text-foreground" {...props} />
                    ),
                    li: ({ node, ...props }) => (
                      <li className="ml-2 text-foreground" {...props} />
                    ),
                    code: ({ node, inline, ...props }: any) =>
                      inline ? (
                        <code className="bg-cosmic-dark/60 text-cosmic-cyan px-1.5 py-0.5 rounded text-sm font-mono border border-cosmic-cyan/20" {...props} />
                      ) : (
                        <code className="block bg-cosmic-dark/80 text-sm font-mono rounded-lg p-4 overflow-x-auto border border-cosmic-purple/20" {...props} />
                      ),
                    pre: ({ node, ...props }) => (
                      <pre className="bg-cosmic-dark/80 rounded-lg p-4 mb-4 overflow-x-auto border border-cosmic-purple/30" {...props} />
                    ),
                    blockquote: ({ node, ...props }) => (
                      <blockquote className="border-l-4 border-cosmic-cyan pl-4 italic my-4 text-muted-foreground" {...props} />
                    ),
                    table: ({ node, ...props }) => (
                      <div className="overflow-x-auto mb-4">
                        <table className="min-w-full border border-cosmic-purple/30 rounded-lg" {...props} />
                      </div>
                    ),
                    th: ({ node, ...props }) => (
                      <th className="border border-cosmic-purple/30 px-4 py-2 bg-cosmic-dark/60 text-cosmic-cyan font-semibold" {...props} />
                    ),
                    td: ({ node, ...props }) => (
                      <td className="border border-cosmic-purple/30 px-4 py-2" {...props} />
                    ),
                    a: ({ node, ...props }) => (
                      <a className="text-cosmic-cyan hover:text-cosmic-purple transition-colors underline" {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                    strong: ({ node, ...props }) => (
                      <strong className="font-bold text-cosmic-cyan" {...props} />
                    ),
                    em: ({ node, ...props }) => (
                      <em className="italic text-cosmic-purple" {...props} />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}

            {/* Streaming cursor */}
            {message.isStreaming && message.content && (
              <motion.span
                className="inline-block w-2 h-5 ml-1 bg-cosmic-cyan rounded-sm"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
              />
            )}
          </div>
        )}

        {/* Metadata footer for AI responses */}
        {!isUser && !message.isStreaming && message.metadata && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-3 pt-3 border-t border-cosmic-purple/20 flex flex-wrap gap-3 text-xs text-muted-foreground"
          >
            {message.metadata.chunks_used !== undefined && message.metadata.chunks_used > 0 && (
              <span className="flex items-center gap-1">
                <span className="text-cosmic-cyan">📚</span>
                {message.metadata.chunks_used} sources
              </span>
            )}
            {message.metadata.response_time_ms && (
              <span className="flex items-center gap-1">
                <span className="text-cosmic-purple">⏱️</span>
                {message.metadata.response_time_ms}ms
              </span>
            )}
            {message.metadata.model && (
              <span className="flex items-center gap-1">
                <span className="text-cosmic-pink">🤖</span>
                {message.metadata.model}
              </span>
            )}
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;
