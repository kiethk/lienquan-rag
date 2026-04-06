"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Send, Bot, User, Sword } from "lucide-react"; // Dùng Lucide icon từ Vega preset

export default function ChatPage() {
    const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Tự động cuộn xuống khi có tin nhắn mới
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg = { role: "user", content: input };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setIsLoading(true);

        try {
            const response = await fetch("http://127.0.0.1:8000/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: input }),
            });

            const data = await response.json();
            setMessages((prev) => [...prev, { role: "ai", content: data.reply }]);
        } catch {
            setMessages((prev) => [...prev, { role: "ai", content: "Mất kết nối với máy chủ Backend rồi ông giáo!" }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-[#0f172a] p-4 font-sans text-slate-200">
            <Card className="w-full max-w-3xl h-[85vh] min-h-0 flex flex-col bg-[#1e293b] border-slate-700 shadow-2xl">
                <CardHeader className="border-b border-slate-700 bg-[#1e293b]/50 backdrop-blur-sm sticky top-0 z-10">
                    <CardTitle className="text-yellow-500 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Sword className="w-6 h-6" />
                            <span>CHIẾN THẦN LIÊN QUÂN AI</span>
                        </div>
                        <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-1 rounded">
                            v3.0 Flash Preview
                        </span>
                    </CardTitle>
                </CardHeader>

                <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto p-6">
                    {messages.length === 0 && (
                        <div className="text-center mt-20 text-slate-500 italic">
                            Nhập tên tướng hoặc đội hình địch để bắt đầu...
                        </div>
                    )}

                    {messages.map((msg, index) => (
                        <div
                            key={index}
                            className={`mb-6 flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                            <div
                                className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                            >
                                <div
                                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                                        msg.role === "user" ? "bg-yellow-600" : "bg-blue-600"
                                    }`}
                                >
                                    {msg.role === "user" ? <User size={18} /> : <Bot size={18} />}
                                </div>
                                <div
                                    className={`p-4 rounded-2xl text-sm leading-relaxed ${
                                        msg.role === "user"
                                            ? "bg-yellow-600/20 border border-yellow-600/30 text-yellow-50"
                                            : "bg-slate-800 border border-slate-700 text-slate-200"
                                    }`}
                                >
                                    <article
                                        className="prose prose-invert prose-sm max-w-none 
                                                    prose-strong:text-yellow-500 prose-headings:text-yellow-500 
                                                    prose-p:my-1 prose-p:leading-relaxed 
                                                    prose-ul:my-1 prose-li:my-0.5 prose-ul:list-disc prose-li:ml-4"
                                    >
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                    </article>
                                </div>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex gap-2 items-center text-slate-500 text-xs animate-pulse ml-12">
                            <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></span>
                            <span>Đang phân tích trận đấu...</span>
                        </div>
                    )}
                </div>

                <CardContent className="p-4 border-t border-slate-700 bg-[#1e293b]/80">
                    <div className="flex gap-2 relative">
                        <Input
                            placeholder="Ví dụ: Team địch có Florentino và Nakroth..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSend()}
                            className="bg-slate-900 border-slate-700 focus:ring-yellow-600 text-slate-100 pr-12 h-12"
                        />
                        <Button
                            onClick={handleSend}
                            disabled={isLoading}
                            className="absolute right-1 top-1 bottom-1 bg-yellow-600 hover:bg-yellow-700 text-white w-10 h-10 p-0"
                        >
                            <Send size={18} />
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
