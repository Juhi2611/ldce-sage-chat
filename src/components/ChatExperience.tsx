import { AnimatePresence, motion } from "motion/react";
import {
  BookOpen,
  Briefcase,
  Building2,
  Bus,
  Check,
  ChevronLeft,
  ChevronRight,
  Clipboard,
  CreditCard,
  ExternalLink,
  GraduationCap,
  HelpCircle,
  Home,
  MapPin,
  Mic,
  Phone,
  RefreshCw,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  TrendingUp,
  WalletCards,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQuery } from "@tanstack/react-query";
import logo from "@/assets/ldce-logo.png.asset.json";
import { api, type CategoryTile, type SuggestionItem } from "@/lib/api";
import { useChat, type ChatMessage } from "@/hooks/useChat";
import { Button } from "@/components/ui/button";

const ICON_MAP: Record<string, LucideIcon> = {
  GraduationCap,
  Building2,
  CreditCard,
  WalletCards,
  Home,
  Briefcase,
  BookOpen,
  Bus,
  MapPin,
  Phone,
  HelpCircle,
};

function getIconComponent(iconName: string): LucideIcon {
  return ICON_MAP[iconName] || HelpCircle;
}

const DEFAULT_PROMPTS = [
  "What is the admission process for Computer Engineering?",
  "How much is the hostel fee?",
  "What is the placement package for CSE?",
  "Does LDCE provide internships?",
  "What branches are available after diploma?",
];

function FormattedMarkdown({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-6 space-y-2 [&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-4 [&_li]:my-0.5 [&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-border [&_th]:bg-surface [&_th]:px-2.5 [&_th]:py-1.5 [&_th]:text-left [&_th]:text-xs [&_th]:font-bold [&_td]:border [&_td]:border-border [&_td]:px-2.5 [&_td]:py-1.5 [&_td]:text-xs [&_strong]:font-semibold [&_strong]:text-foreground">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a
              {...props}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-semibold text-primary underline hover:text-primary/80"
            >
              {props.children}
              <ExternalLink className="size-3 inline shrink-0" />
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function BotMessage({
  message,
  onSend,
  onRetry,
  onVote,
}: {
  message: ChatMessage;
  onSend: (text: string) => void;
  onRetry: (query: string) => void;
  onVote: (enquiryId: number, rating: "up" | "down") => void;
}) {
  const [copied, setCopied] = useState(false);

  const copyText = () => {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // Filter mined vs default suggestions
  const hasMinedSuggestions = message.suggestions?.some((s) => s.source === "mined");

  // Intent badge text
  const intentLabel = message.intent
    ? `Intent: ${message.intent}${message.department ? ` · Dept: ${message.department}` : ""}`
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex max-w-[92%] gap-3 sm:max-w-[82%]"
    >
      <div className="relative mt-1 size-9 shrink-0 rounded-full bg-card p-1 shadow-sm ring-1 ring-border">
        <img src={logo.url} alt="LDCE assistant" className="size-full" />
        <span className="absolute bottom-0 right-0 size-2.5 rounded-full bg-online ring-2 ring-background" />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={`rounded-2xl rounded-tl-sm border p-4 shadow-soft ${
            message.is_error
              ? "border-destructive/40 bg-destructive/5"
              : message.resolved === false
                ? "border-warm/30 bg-warm-soft/30"
                : "border-border bg-card"
          }`}
        >
          {message.resolved !== false && !message.is_error && intentLabel && (
            <span className="mb-3 inline-flex rounded-full bg-accent px-2.5 py-1 text-[10px] font-bold uppercase text-primary">
              {intentLabel}
            </span>
          )}

          <FormattedMarkdown content={message.text} />

          {message.source_url && (
            <a
              href={message.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline"
            >
              Open official page <ExternalLink className="size-3" />
            </a>
          )}

          {message.is_error && message.can_retry && message.last_query && (
            <div className="mt-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onRetry(message.last_query!)}
                className="gap-1.5 text-xs"
              >
                <RefreshCw className="size-3" /> Retry query
              </Button>
            </div>
          )}
        </div>

        {/* Suggestions / followups */}
        {message.suggestions && message.suggestions.length > 0 && (
          <div className="mt-3">
            {hasMinedSuggestions ? (
              <div className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase text-warm">
                <Sparkles className="size-3" /> Suggested from popular enquiries
              </div>
            ) : (
              <div className="mb-2 text-[10px] font-bold uppercase text-muted-foreground">
                You may also want to know
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {message.suggestions.map((s, idx) => (
                <button
                  key={`${s.label}-${idx}`}
                  onClick={() => onSend(s.question)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium transition-colors hover:border-primary/40 hover:bg-accent"
                >
                  {s.source === "mined" && <Sparkles className="size-3 text-warm" />}
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message footer / actions */}
        <div className="mt-2 flex items-center gap-1 text-muted-foreground">
          <span className="mr-2 text-[10px]">{message.time}</span>
          <button
            onClick={copyText}
            aria-label="Copy answer"
            className="rounded-md p-1.5 hover:bg-accent"
          >
            {copied ? (
              <Check className="size-3.5 text-online" />
            ) : (
              <Clipboard className="size-3.5" />
            )}
          </button>

          {message.enquiry_id != null && (
            <>
              <button
                onClick={() => onVote(message.enquiry_id!, "up")}
                aria-label="Helpful"
                className={`rounded-md p-1.5 hover:bg-accent ${
                  message.vote === "up" ? "text-primary bg-accent" : ""
                }`}
              >
                <ThumbsUp className="size-3.5" />
              </button>
              <button
                onClick={() => onVote(message.enquiry_id!, "down")}
                aria-label="Not helpful"
                className={`rounded-md p-1.5 hover:bg-accent ${
                  message.vote === "down" ? "text-destructive bg-destructive/10" : ""
                }`}
              >
                <ThumbsDown className="size-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function ChatExperience() {
  const { messages, input, setInput, typing, send, retry, clear, vote } = useChat();
  const [panel, setPanel] = useState(true);
  const end = useRef<HTMLDivElement>(null);
  const initialAskSent = useRef(false);

  // Fetch quick action categories
  const { data: categoriesData } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.getCategories(),
    staleTime: 1000 * 60 * 10,
  });

  // Handle URL query parameter `?ask=...`
  useEffect(() => {
    if (initialAskSent.current) return;
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const askParam = params.get("ask");
      if (askParam) {
        initialAskSent.current = true;
        send(askParam);
        // Clean URL parameter without reload
        const newUrl = window.location.pathname;
        window.history.replaceState({}, "", newUrl);
      }
    }
  }, [send]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const charCount = input.length;
  const isOverLimit = charCount > 500;
  const isNearLimit = charCount >= 400;

  const categories: CategoryTile[] = categoriesData || [
    {
      id: "cat-1",
      title: "Admissions",
      icon: "GraduationCap",
      question: "What is the admission process for Computer Engineering?",
    },
    {
      id: "cat-2",
      title: "Departments",
      icon: "Building2",
      question: "Which engineering departments are available at LDCE?",
    },
    {
      id: "cat-3",
      title: "Fees",
      icon: "CreditCard",
      question: "Can you share the fee structure for CSE?",
    },
    { id: "cat-4", title: "Hostel", icon: "Home", question: "How much is the hostel fee?" },
    {
      id: "cat-5",
      title: "Placements",
      icon: "Briefcase",
      question: "What is the placement package for CSE?",
    },
    {
      id: "cat-6",
      title: "Academics",
      icon: "BookOpen",
      question: "How is the academic curriculum structured?",
    },
    {
      id: "cat-7",
      title: "Campus Facilities",
      icon: "Bus",
      question: "What campus facilities are available?",
    },
    {
      id: "cat-8",
      title: "Contact",
      icon: "Phone",
      question: "How can I contact the LDCE admission office?",
    },
  ];

  return (
    <section className="mx-auto max-w-[1500px] px-3 pb-14 sm:px-4 lg:px-8">
      <div className="flex min-h-[680px] overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-14 items-center justify-between border-b border-border px-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <img src={logo.url} className="size-8" alt="LDCE assistant" />
                <span className="absolute bottom-0 right-0 size-2.5 rounded-full bg-online ring-2 ring-card" />
              </div>
              <div>
                <b className="block text-sm">LDCE Enquiry Assistant</b>
                <span className="text-[11px] text-online">Online · replies instantly</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={clear}>
                <Trash2 className="size-4" /> <span className="hidden sm:inline">Clear chat</span>
              </Button>
              <Button
                variant="icon"
                size="icon"
                onClick={() => setPanel(!panel)}
                className="hidden lg:inline-flex"
                aria-label="Toggle quick facts"
              >
                {panel ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
              </Button>
            </div>
          </div>

          <div className="relative flex-1 overflow-y-auto bg-chat px-4 py-6 sm:px-6">
            <img
              src={logo.url}
              aria-hidden
              className="pointer-events-none absolute left-1/2 top-24 size-72 -translate-x-1/2 opacity-[0.025] grayscale"
              alt=""
            />
            <div className="relative space-y-6">
              {messages.map((m, i) =>
                m.role === "bot" ? (
                  <div key={m.id}>
                    <BotMessage message={m} onSend={send} onRetry={retry} onVote={vote} />
                    {i === 0 && (
                      <>
                        <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
                          {categories.map((cat) => {
                            const Icon = getIconComponent(cat.icon);
                            return (
                              <motion.button
                                whileHover={{ y: -2 }}
                                onClick={() => send(cat.question)}
                                key={cat.id || cat.title}
                                className="rounded-xl border border-border bg-background p-3 text-left shadow-sm transition-colors hover:border-primary/30"
                              >
                                <Icon className="mb-2 size-4 text-primary" />
                                <span className="text-xs font-semibold">{cat.title}</span>
                              </motion.button>
                            );
                          })}
                        </div>
                        <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
                          {DEFAULT_PROMPTS.map((x) => (
                            <button
                              key={x}
                              onClick={() => send(x)}
                              className="shrink-0 rounded-full border border-border bg-background px-3 py-2 text-xs hover:border-primary/40"
                            >
                              {x}
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <motion.div
                    key={m.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="ml-auto max-w-[82%]"
                  >
                    <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground shadow-sm">
                      {m.text}
                    </div>
                    <div className="mt-1 text-right text-[10px] text-muted-foreground">
                      {m.time}
                    </div>
                  </motion.div>
                ),
              )}

              <AnimatePresence>
                {typing && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-3"
                  >
                    <img src={logo.url} className="size-9" alt="" />
                    <div className="flex gap-1 rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="size-2 animate-bounce rounded-full bg-muted-foreground"
                          style={{ animationDelay: `${i * 120}ms` }}
                        />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={end} />
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!isOverLimit) send();
            }}
            className="border-t border-border bg-card p-3 sm:p-4"
          >
            <div className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 shadow-inner focus-within:ring-2 focus-within:ring-ring">
              <Button type="button" variant="icon" size="icon" aria-label="Voice input">
                <Mic className="size-5" />
              </Button>
              <div className="flex-1 flex flex-col">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (!isOverLimit) send();
                    }
                  }}
                  rows={1}
                  maxLength={500}
                  placeholder="Ask about admissions, fees, campus life…"
                  className="max-h-28 min-h-10 w-full resize-none bg-transparent px-2 py-2.5 text-sm outline-none placeholder:text-muted-foreground"
                />
                {isNearLimit && (
                  <div
                    className={`px-2 pb-1 text-right text-[10px] ${
                      isOverLimit ? "text-destructive font-bold" : "text-muted-foreground"
                    }`}
                  >
                    {charCount}/500
                  </div>
                )}
              </div>
              <Button
                type="submit"
                size="icon"
                disabled={!input.trim() || typing || isOverLimit}
                aria-label="Send message"
              >
                <Send className="size-4" />
              </Button>
            </div>
            <p className="mt-2 text-center text-[10px] text-muted-foreground">
              For official decisions, please verify details on the LDCE website.
            </p>
          </form>
        </div>

        {panel && (
          <aside className="hidden w-80 shrink-0 border-l border-border bg-surface p-6 lg:block">
            <p className="section-label">At a glance</p>
            <h2 className="mt-2 font-display text-2xl font-bold">Quick Facts</h2>
            <div className="mt-6 space-y-5">
              <div className="fact-row">
                <MapPin className="size-5 text-warm" />
                <div>
                  <b>Campus</b>
                  <p>Opposite Gujarat University, Navrangpura, Ahmedabad</p>
                </div>
              </div>
              <div className="fact-row">
                <Check className="size-5 text-warm" />
                <div>
                  <b>Affiliation</b>
                  <p>Gujarat Technological University (GTU)</p>
                </div>
              </div>
            </div>
            <div className="mt-8 border-t border-border pt-6">
              <div className="flex items-center gap-2">
                <TrendingUp className="size-4 text-warm" />
                <h3 className="font-bold">Popular right now</h3>
              </div>
              <ol className="mt-4 space-y-3">
                {[
                  "ACPC admission timeline",
                  "CSE placement overview",
                  "Hostel availability",
                  "Scholarship eligibility",
                  "Diploma to degree",
                ].map((x, i) => (
                  <li key={x} className="flex gap-3 text-sm">
                    <span className="font-display text-lg text-primary/50">0{i + 1}</span>
                    <span className="pt-1">{x}</span>
                  </li>
                ))}
              </ol>
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}
