import { useEffect, useRef, useState, useCallback } from "react";
import { api, type SuggestionItem } from "@/lib/api";
import { getSessionId, resetSessionId } from "@/lib/session";

export interface ChatMessage {
  id: number;
  role: "bot" | "user";
  text: string;
  time: string;
  intent?: string;
  department?: string | null;
  topic?: string | null;
  confidence?: number;
  resolved?: boolean;
  suggestions?: SuggestionItem[];
  enquiry_id?: number | null;
  source_url?: string | null;
  is_smalltalk?: boolean;
  is_error?: boolean;
  can_retry?: boolean;
  last_query?: string;
  vote?: "up" | "down" | null;
}

const formatTime = () =>
  new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(new Date());

export const initialWelcomeMessage: ChatMessage = {
  id: 1,
  role: "bot",
  time: "10:30 AM",
  intent: "Welcome · General",
  resolved: true,
  text: "Namaste! I’m the LDCE Smart Enquiry Assistant. I can help you find clear information about admissions, departments, fees, campus life and more. What would you like to know?",
};

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([initialWelcomeMessage]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const isSubmitting = useRef(false);

  const send = useCallback(
    async (text?: string) => {
      const query = (text !== undefined ? text : input).trim();
      if (!query || isSubmitting.current) return;

      const userMsgId = Date.now();
      const userMsg: ChatMessage = {
        id: userMsgId,
        role: "user",
        text: query,
        time: formatTime(),
      };

      setMessages((prev) => [...prev, userMsg]);
      if (text === undefined) {
        setInput("");
      }
      setTyping(true);
      isSubmitting.current = true;

      try {
        const sessionId = getSessionId();
        const res = await api.chat({
          query,
          session_id: sessionId,
        });

        const botMsg: ChatMessage = {
          id: userMsgId + 1,
          role: "bot",
          text: res.answer_markdown,
          time: formatTime(),
          intent: res.intent,
          department: res.department,
          topic: res.topic,
          confidence: res.confidence,
          resolved: res.resolved,
          suggestions: res.suggestions,
          enquiry_id: res.enquiry_id,
          source_url: res.source_url,
          is_smalltalk: res.is_smalltalk,
        };

        setMessages((prev) => [...prev, botMsg]);
      } catch (err: unknown) {
        let errorText =
          "Sorry, something went wrong while connecting to the server. Please try again.";
        if (err && typeof err === "object" && "status" in err) {
          const apiErr = err as { status: number; message: string };
          if (apiErr.status === 429) {
            errorText = "Please wait a moment before sending another message.";
          } else if (apiErr.message) {
            errorText = apiErr.message;
          }
        }

        const errorMsg: ChatMessage = {
          id: userMsgId + 1,
          role: "bot",
          text: errorText,
          time: formatTime(),
          resolved: false,
          is_error: true,
          can_retry: true,
          last_query: query,
        };

        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setTyping(false);
        isSubmitting.current = false;
      }
    },
    [input],
  );

  const retry = useCallback(
    (lastQuery: string) => {
      send(lastQuery);
    },
    [send],
  );

  const clear = useCallback(() => {
    resetSessionId();
    setTyping(false);
    isSubmitting.current = false;
    setMessages([
      {
        ...initialWelcomeMessage,
        id: Date.now(),
        time: formatTime(),
      },
    ]);
  }, []);

  const vote = useCallback(async (enquiryId: number, rating: "up" | "down") => {
    try {
      await api.sendFeedback({ enquiry_id: enquiryId, rating });
      setMessages((prev) =>
        prev.map((msg) => (msg.enquiry_id === enquiryId ? { ...msg, vote: rating } : msg)),
      );
    } catch (err) {
      console.error("Failed to submit feedback", err);
    }
  }, []);

  return {
    messages,
    input,
    setInput,
    typing,
    send,
    retry,
    clear,
    vote,
  };
}
