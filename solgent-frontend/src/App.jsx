import { useState, useEffect, useRef } from "react";
import { Cpu, HardDrive, Copy, Check, ChevronDown, ChevronUp, ExternalLink, Video, Plus, Send } from "lucide-react";

export default function App() {
  // --- Core Theme & Window State Variables ---
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSignInOpen, setIsSignInOpen] = useState(false);
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);

  // --- Mock Authentication States ---
  const [signinMessage, setSigninMessage] = useState("");
  const [signupMessage, setSignupMessage] = useState("");

  // --- Conversational Engine States ---
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]); 
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [latency, setLatency] = useState(null);
  
  // Persistent Session Management Strategy
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem("solgent_session_id");
    if (saved) return saved;
    const randomUuid = crypto.randomUUID 
      ? crypto.randomUUID() 
      : `solgent-${Math.random().toString(36).substring(2, 11)}`;
    localStorage.setItem("solgent_session_id", randomUuid);
    return randomUuid;
  });

  const outputRef = useRef(null);

  // Sync application background skin directly to document body context
  useEffect(() => {
    if (theme === "dark") {
      document.body.classList.add("dark-theme");
      document.body.classList.remove("light-theme");
    } else {
      document.body.classList.add("light-theme");
      document.body.classList.remove("dark-theme");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Maintain auto-scroll anchoring during multi-turn streaming events
  useEffect(() => {
    outputRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  // Clear tracking array and provision a new session token
  const handleNewChat = () => {
    const newId = crypto.randomUUID 
      ? crypto.randomUUID() 
      : `solgent-${Math.random().toString(36).substring(2, 11)}`;
    localStorage.setItem("solgent_session_id", newId);
    setSessionId(newId);
    setMessages([]);
    setErrorMessage("");
    setLatency(null);
  };

  const handleSignInSubmit = (e) => {
    e.preventDefault();
    setSigninMessage("Sign in attempt successful! (Demo)");
  };

  const handleSignUpSubmit = (e) => {
    e.preventDefault();
    setSignupMessage("Registration successful! (Demo)");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || isLoading) return;

    setErrorMessage("");
    setIsLoading(true);
    setLatency(null);

    const userMessage = { role: "user", text: query };
    setMessages((prev) => [...prev, userMessage]);
    setInput(""); 

    const startTime = performance.now();

    try {
      const response = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: query,
          session_id: sessionId,
          model: "llama-3.3-70b-versatile",
          deep_think: true
        })
      });

      const data = await response.json();

      if (response.ok) {
        const endTime = performance.now();
        setLatency(((endTime - startTime) / 1000).toFixed(2));
        
        setMessages((prev) => [
          ...prev,
          { 
            role: "assistant", 
            text: data.answer, 
            metadata: data.used_metadata 
          }
        ]);
      } else {
        setErrorMessage(data.detail || "Could not process transaction workspace routing.");
      }
    } catch (error) {
      console.error("API Processing Failure:", error);
      setErrorMessage("Could not connect to the SolGent backend service. Please ensure the FastAPI server is running on port 5000.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* NAVIGATION HEADER PLANE */}
      <header className="header">
        <div className="container">
          <nav className="navbar">
            <a href="#" className="logo" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
              <span className="logo-icon">🔧</span>
              <span>SolGent</span>
            </a>
            
            <div className={`nav-links ${isMobileMenuOpen ? "active" : ""}`}>
              <a href="#features" onClick={() => setIsMobileMenuOpen(false)}>Features</a>
              <a href="#demo" onClick={() => setIsMobileMenuOpen(false)}>Workspace</a>
              <a href="#features" onClick={() => setIsMobileMenuOpen(false)}>Testimonials</a>
              <button className="nav-btn" onClick={() => { setIsSignInOpen(true); setIsMobileMenuOpen(false); setSigninMessage(""); }}>Sign In</button>
              <button className="nav-btn" onClick={() => { setIsSignUpOpen(true); setIsMobileMenuOpen(false); setSignupMessage(""); }}>Sign Up</button>
              <button className="theme-btn" onClick={toggleTheme}>
                {theme === "light" ? "🌙" : "💡"}
              </button>
            </div>
            
            <button className="mobile-menu-btn" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
              ☰
            </button>
          </nav>
        </div>
      </header>

      <main>
        {/* HERO SECTION */}
        <section className="hero">
          <div className="container">
            <div className="hero-content">
              <h1>Continuous <span className="highlight">Workspace</span> Intelligence</h1>
              <p>Solve complex tasks using step-by-step contextual loops backed by Supabase vectors.</p>
              <div className="hero-btns">
                <a href="#demo" className="btn primary">Open Active Canvas</a>
                <button onClick={handleNewChat} className="btn secondary" style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
                  <Plus size={16} /> New Chat Session
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* WORKSPACE SOLVER PANEL */}
        <section id="demo" className="demo-section">
          <div className="container">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2>SolGent Continuous Canvas</h2>
              {messages.length > 0 && (
                <button onClick={handleNewChat} style={{ background: "none", border: "1px solid rgba(128,128,128,0.3)", padding: "0.4rem 0.8rem", borderRadius: "6px", cursor: "pointer", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.4rem", color: "inherit" }}>
                  <Plus size={14} /> Clear Stream
                </button>
              )}
            </div>

            <div className="demo-box" style={{ minHeight: "500px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              
              {/* ROLLING CONVERSATIONAL MESSAGES CONTAINER */}
              <div className="solution-output" style={{ flexGrow: 1, overflowY: "auto", padding: "1rem" }}>
                
                {messages.length === 0 && !isLoading && (
                  <div style={{ textAlign: "center", color: "#6b7280", margin: "4rem 0" }}>
                    <p style={{ fontSize: "1.1rem", fontWeight: "600" }}>Welcome to your workspace.</p>
                    <p style={{ fontSize: "0.9rem" }}>Submit a pipeline problem below to trigger step-by-step analysis loops.</p>
                  </div>
                )}

                {messages.map((msg, idx) => (
                  <div 
                    key={idx} 
                    style={{ 
                      marginBottom: "2rem", 
                      padding: "1rem", 
                      borderRadius: "8px", 
                      background: msg.role === "user" ? "rgba(99, 102, 241, 0.05)" : "transparent",
                      borderLeft: msg.role === "user" ? "4px solid #6366f1" : "none"
                    }}
                  >
                    <p style={{ fontSize: "0.8rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: msg.role === "user" ? "#6366f1" : "#0a476f", marginBottom: "0.5rem" }}>
                      {msg.role === "user" ? "👤 User Request" : "🔧 SolGent Engine Output"}
                    </p>

                    {msg.role === "user" ? (
                      <p style={{ fontSize: "1.05rem", margin: 0, paddingLeft: "0.25rem" }}>{msg.text}</p>
                    ) : (
                      <div className="solution-payload animate-fade-in" style={{ padding: 0, border: "none", background: "none" }}>
                        <div style={{ paddingLeft: "0.25rem", lineHeight: "1.7" }}>
                          <ResponseParser text={msg.text} />
                        </div>

                        {/* Marketplace Context Sourcing Visual Catalog Cards */}
                        {msg.metadata?.marketplace_sourcing && msg.metadata.marketplace_sourcing.length > 0 && (
                          <div style={{ marginTop: "1.5rem" }}>
                            <h4 style={{ fontSize: "0.95rem", margin: "0.5rem 0", fontWeight: "700", color: "#0a476f" }}>🛠️ Verified Procurement Matrices</h4>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "1rem", marginTop: "0.5rem" }}>
                              {msg.metadata.marketplace_sourcing.map((item, pIdx) => (
                                <div key={pIdx} style={{ border: "1px solid rgba(128,128,128,0.2)", borderRadius: "8px", padding: "0.75rem", backgroundColor: "rgba(128,128,128,0.02)", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                                  {item.image_url && (
                                    <div style={{ width: "100%", height: "120px", display: "flex", alignItems: "center", justifyContent: "center", background: "#ffffff", borderRadius: "6px", overflow: "hidden", marginBottom: "0.25rem" }}>
                                      <img src={item.image_url} alt={item.title} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }} />
                                    </div>
                                  )}
                                  <span style={{ fontWeight: "700", color: "#6366f1", fontSize: "0.75rem", textTransform: "uppercase" }}>[{item.source}]</span>
                                  <span style={{ fontSize: "0.85rem", fontWeight: "600", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", lineHeight: "1.3", height: "2.6em" }}>{item.title}</span>
                                  <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: "0.2rem", fontSize: "0.8rem", marginTop: "auto", color: "#0284c7", fontWeight: "600", textDecoration: "none" }}>
                                    Procure Component <ExternalLink size={12} />
                                  </a>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Video Reference Context Assets */}
                        {msg.metadata?.youtube && msg.metadata.youtube.length > 0 && (
                          <div style={{ marginTop: "1.5rem" }}>
                            <h4 style={{ fontSize: "0.95rem", margin: "0.5rem 0", fontWeight: "700", color: "#0a476f" }}>📹 Reference Video Feeds</h4>
                            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                              {msg.metadata.youtube.map((video, vIdx) => (
                                <div key={vIdx} style={{ background: "rgba(0,0,0,0.02)", padding: "0.5rem 0.75rem", borderRadius: "6px", borderLeft: "3px solid #ef4444", fontSize: "0.9rem" }}>
                                  <a href={video.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "0.4rem", textDecoration: "none", color: "inherit" }}>
                                    <Video size={14} color="#ef4444" /> {video.title}
                                  </a>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {/* Active Loading Calculations State Display */}
                {isLoading && (
                  <div style={{ padding: "1rem", color: "#6366f1", fontWeight: "600", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Cpu size={16} className="animate-spin" /> SolGent processing context matrices...
                  </div>
                )}

                {/* Error Fallback Notice */}
                {errorMessage && (
                  <p style={{ color: "#ef4444", fontWeight: "600", padding: "1rem" }}>{errorMessage}</p>
                )}

                {/* Active Latency Diagnostic Tracking Panel */}
                {!isLoading && latency && <DiagnosticsBlock latency={latency} provider="groq-serverless-cloud" />}
                
                <div ref={outputRef} />
              </div>

              {/* PERSISTENT CONVERSATIONAL ENTRY BOX */}
              <form onSubmit={handleSubmit} className="input-group" style={{ padding: "1rem", borderTop: "1px solid rgba(128,128,128,0.15)" }}>
                <input 
                  type="text" 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={isLoading}
                  placeholder={isLoading ? "Engine compiling data logs..." : "Ask a follow-up or submit a new problem..."} 
                  style={{ borderRadius: "6px 0 0 6px" }}
                />
                <button type="submit" id="solveBtn" disabled={!input.trim() || isLoading} style={{ borderRadius: "0 6px 6px 0", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Send size={16} /> {isLoading ? "..." : "Send"}
                </button>
              </form>

            </div>
          </div>
        </section>

        {/* FEATURES GRID */}
        <section id="features" className="features">
          <div className="container">
            <h2>Why Choose SolveD</h2>
            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon">🔍</div>
                <h3>AI-Verified</h3>
                <p>Solutions checked against multiple expert sources</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🛠️</div>
                <h3>Verified Source</h3>
                <p>For prioritized solution for your quest</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">📹</div>
                <h3>Video Guides</h3>
                <p>See advanced techniques for making your problem Solved</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER COMPONENTS */}
      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-brand">
              <div className="logo">
                <span className="logo-icon" style={{ color: "white" }}>🔧</span>
                <span style={{ color: "white" }}>SolGent</span>
              </div>
              <p>©AI-powered problem solving</p>
            </div>
            <div className="footer-links">
              <a href="#">Privacy</a>
              <a href="#">Terms</a>
              <a href="#">Contact</a>
            </div>
          </div>
        </div>
      </footer>

      {/* MODALS */}
      {isSignInOpen && (
        <div className="modal" onClick={(e) => e.target.classList.contains("modal") && setIsSignInOpen(false)}>
          <div className="modal-content">
            <span className="close-btn" onClick={() => setIsSignInOpen(false)}>&times;</span>
            <h2>Sign In</h2>
            <form onSubmit={handleSignInSubmit}>
              <label htmlFor="signinUsername">Username:</label>
              <input type="text" id="signinUsername" required />
              <label htmlFor="signinPassword">Password:</label>
              <input type="password" id="signinPassword" required />
              <button type="submit" className="btn primary">Sign In</button>
              {signinMessage && <p className="form-message" style={{ color: "#10b981" }}>{signinMessage}</p>}
            </form>
          </div>
        </div>
      )}

      {isSignUpOpen && (
        <div className="modal" onClick={(e) => e.target.classList.contains("modal") && setIsSignUpOpen(false)}>
          <div className="modal-content">
            <span className="close-btn" onClick={() => setIsSignUpOpen(false)}>&times;</span>
            <h2>Sign Up</h2>
            <form onSubmit={handleSignUpSubmit}>
              <label htmlFor="signupUsername">Username:</label>
              <input type="text" id="signupUsername" required />
              <label htmlFor="signupPassword">Password:</label>
              <input type="password" id="signupPassword" required />
              <button type="submit" className="btn primary">Sign Up</button>
              {signupMessage && <p className="form-message" style={{ color: "#10b981" }}>{signupMessage}</p>}
            </form>
          </div>
        </div>
      )}
    </>
  );
}

// --- SUB-COMPONENT: RUNTIME PIPELINE LOG TRACKER ---
function DiagnosticsBlock({ latency, provider }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="diagnostics-log-box" style={{ width: "100%", boxSizing: "border-box", margin: "0.5rem 0" }}>
      <button 
        type="button" 
        onClick={() => setIsOpen(!isOpen)}
        style={{ width: "100%", background: "none", border: "none", padding: "0.6rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "center", color: "inherit", cursor: "pointer", fontSize: "0.75rem", fontFamily: "inherit" }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: "600" }}>
          <Cpu size={14} color="#6366f1" />
          Core Latency Loop Performance ({latency}s)
        </span>
        {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {isOpen && (
        <div style={{ padding: "0.4rem 1rem 0.6rem", opacity: 0.75, borderTop: "1px dashed rgba(128,128,128,0.2)", lineHeight: "1.6", fontSize: "0.75rem" }}>
          <div>⚡ [Pipeline Node] Data synchronized successfully over local network stream...</div>
          <div>⚡ [Cluster Provider] {provider || "groq-serverless-cloud"} node online.</div>
          <div>⚡ [Persistence Architecture] Conversational arrays logged to Supabase vectors.</div>
        </div>
      )}
    </div>
  );
}

// --- SUB-COMPONENT: MULTIMODAL INLINE MARKDOWN PARSER ---
function parseMarkdownInline(text) {
  if (!text) return "";
  
  // 1. Joint Extraction Regex: Extracts Images and Hyperlinks without conflicts
  const masterRegex = /(!?)\[([^\]]+)\]\(([^)]+)\)/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = masterRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const isImage = match[1] === "!";
    parts.push({
      type: isImage ? "image" : "link",
      text: match[2],
      url: match[3],
      key: match.index
    });
    lastIndex = masterRegex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  // 2. Parse out embedded bold tags: **text**
  return parts.flatMap((part) => {
    if (typeof part !== "string") return part;

    const boldRegex = /\*\*([^*]+)\*\*/g;
    const subParts = [];
    let subLastIndex = 0;
    let bMatch;

    while ((bMatch = boldRegex.exec(part)) !== null) {
      if (bMatch.index > subLastIndex) {
        subParts.push(part.substring(subLastIndex, bMatch.index));
      }
      subParts.push({
        type: "bold",
        text: bMatch[1],
        key: bMatch.index
      });
      subLastIndex = boldRegex.lastIndex;
    }
    if (subLastIndex < part.length) {
      subParts.push(part.substring(subLastIndex));
    }
    return subParts;
  }).map((token, i) => {
    if (typeof token === "string") return token;
    
    if (token.type === "image") {
      return (
        <img 
          key={`img-${token.key}-${i}`} 
          src={token.url} 
          alt={token.text} 
          style={{ 
            maxWidth: "100%", 
            maxHeight: "360px",
            height: "auto", 
            borderRadius: "8px", 
            margin: "0.75rem 0", 
            display: "block",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
            border: "1px solid rgba(128,128,128,0.15)"
          }} 
        />
      );
    }
    if (token.type === "link") {
      return (
        <a 
          key={`link-${token.key}-${i}`} 
          href={token.url} 
          target="_blank" 
          rel="noopener noreferrer" 
          style={{ color: "#0284c7", textDecoration: "underline", fontWeight: "600" }}
        >
          {token.text}
        </a>
      );
    }
    if (token.type === "bold") {
      return <strong key={`bold-${token.key}-${i}`} style={{ fontWeight: "700" }}>{token.text}</strong>;
    }
    return null;
  });
}

// --- SUB-COMPONENT: BLOCK TEXT MARKDOWN SNIP EXTRACTOR ---
function ResponseParser({ text }) {
  if (!text) return null;
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, index) => {
    if (part.startsWith("```")) {
      const match = part.match(/```(\w*)\n([\s\S]*?)```/);
      const lang = match ? match[1] : "source";
      const codeLines = match ? match[2].trim() : part.replace(/```/g, "").trim();
    return <CodeCard block={codeLines} key={index} lang={lang} />;
    }
    
    return part.split("\n").map((line, lIdx) => {
      const trimmedLine = line.trim();
      if (line.startsWith("### ")) {
        return <h4 key={`${index}-${lIdx}`} style={{ margin: "1.2rem 0 0.6rem", fontWeight: "700" }}>{parseMarkdownInline(line.replace("### ", ""))}</h4>;
      }
      if (line.startsWith("## ")) {
        return <h3 key={`${index}-${lIdx}`} style={{ margin: "1.5rem 0 0.8rem", fontWeight: "700" }}>{parseMarkdownInline(line.replace("## ", ""))}</h3>;
      }
      if (line.startsWith("* ") || line.startsWith("- ")) {
        return <li key={`${index}-${lIdx}`} style={{ marginLeft: "1.2rem", marginBottom: "0.4rem", listStyleType: "disc" }}>{parseMarkdownInline(line.substring(2))}</li>;
      }
      
      const numListMatch = line.match(/^(\d+)\.\s(.*)/);
      if (numListMatch) {
        return (
          <li key={`${index}-${lIdx}`} style={{ marginLeft: "1.2rem", marginBottom: "0.4rem", listStyleType: "decimal" }}>
            {parseMarkdownInline(numListMatch[2])}
          </li>
        );
      }
      
      return trimmedLine ? <p key={`${index}-${lIdx}`} style={{ margin: "0.6rem 0", lineHeight: "1.7" }}>{parseMarkdownInline(line)}</p> : null;
    });
  });
}

// --- SUB-COMPONENT: PORTABLE CLIPBOARD UTILITY CONTAINER ---
function CodeCard({ lang, block }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(block);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="code-container-block" style={{ width: "100%", boxSizing: "border-box", margin: "1rem 0" }}>
      <div className="code-header-action" style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 1rem", background: "#1e293b", color: "#94a3b8", fontSize: "0.8rem", borderRadius: "6px 6px 0 0" }}>
        <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <HardDrive color="#3b82f6" size="{12}"/>
          {lang || "source"}
        </span>
        <button type="button" onClick={handleCopy} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem" }}>
          {copied ? <><Check color="#10b981" size="{12}"/> Copied</> : <><Copy size="{12}"/> Copy code</>}
        </button>
      </div>
      <pre style={{ margin: 0, padding: "1rem", overflowX: "auto", fontSize: "0.85rem", background: "#090d16", color: "#e2e8f0", borderRadius: "0 0 6px 6px" }}>
        <code>{block}</code>
      </pre>
    </div>
  );
}