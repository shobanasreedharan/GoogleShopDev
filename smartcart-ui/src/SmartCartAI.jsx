import { useState, useRef, useEffect, useCallback } from "react";
import { auth, provider } from "./firebase";
import { signInWithPopup, signOut, onAuthStateChanged } from "firebase/auth";

const API_URL   = process.env.REACT_APP_API_URL   || "http://127.0.0.1:8000/generate";
const AGENT_URL = process.env.REACT_APP_AGENT_URL || "https://smartcart-agent-505176174078.us-central1.run.app/chat";
const BASE_URL  = (process.env.REACT_APP_API_URL  || "http://127.0.0.1:8000/generate").replace("/generate", "");

const T = {
  bg:"#F7F5F0", surface:"#FFFFFF", surfaceAlt:"#F2EFE9",
  border:"#E0DDD6", borderDark:"#C8C4BC",
  ink:"#1A1814", inkSec:"#6B6760", inkTer:"#9E9B96",
  green:"#2D6A4F", greenLight:"#D8EDDF", greenMid:"#52B788",
  amber:"#B5600A", amberLight:"#FDEFD3",
  red:"#C0392B", redLight:"#FDECEA",
  blue:"#1B4F8A", blueLight:"#DDEAF8",
};

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=DM+Mono:wght@400;500&family=Lato:wght@300;400;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: ${T.bg}; color: ${T.ink}; font-family: 'Futura', 'Trebuchet MS', sans-serif; line-height: 1.6; }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: ${T.bg}; }
  ::-webkit-scrollbar-thumb { background: ${T.borderDark}; border-radius: 3px; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes slideIn { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:translateX(0); } }
  @keyframes slideInLeft { from { opacity:0; transform:translateX(-20px); } to { opacity:1; transform:translateX(0); } }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
  @keyframes micPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(192,57,43,0.4); } 70% { box-shadow: 0 0 0 10px rgba(192,57,43,0); } }
  .fu  { animation: fadeUp 0.5s ease both; }
  .fu1 { animation: fadeUp 0.5s 0.05s ease both; }
  .fu2 { animation: fadeUp 0.5s 0.10s ease both; }
  .fu3 { animation: fadeUp 0.5s 0.15s ease both; }
  .chat-panel { animation: slideIn 0.25s ease both; }
  .nav-panel  { animation: slideInLeft 0.25s ease both; }
  .chat-msg-user { animation: fadeUp 0.2s ease both; }
  .chat-msg-agent { animation: fadeUp 0.2s ease both; }
  .mic-active { animation: micPulse 1.2s ease infinite; }
`;

// ── Shared UI ────────────────────────────────────────────────────────────────

function Label({ children }) {
  return <span style={{ display:"block", fontSize:11, fontWeight:700, letterSpacing:"0.06em", textTransform:"uppercase", color:T.inkSec, marginBottom:5 }}>{children}</span>;
}

function Input({ label, value, onChange, placeholder, type="text" }) {
  const [f, setF] = useState(false);
  return (
    <label style={{ display:"flex", flexDirection:"column", gap:4 }}>
      {label && <Label>{label}</Label>}
      <input type={type} value={value} onChange={onChange} placeholder={placeholder}
        onFocus={()=>setF(true)} onBlur={()=>setF(false)}
        style={{ background:T.surfaceAlt, border:`1px solid ${f?T.ink:T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", width:"100%", transition:"border-color 0.15s" }} />
    </label>
  );
}

function Textarea({ label, value, onChange, placeholder, rows=3 }) {
  const [f, setF] = useState(false);
  return (
    <label style={{ display:"flex", flexDirection:"column", gap:4 }}>
      {label && <Label>{label}</Label>}
      <textarea value={value} onChange={onChange} placeholder={placeholder} rows={rows}
        onFocus={()=>setF(true)} onBlur={()=>setF(false)}
        style={{ background:T.surfaceAlt, border:`1px solid ${f?T.ink:T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", width:"100%", resize:"vertical", transition:"border-color 0.15s" }} />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label style={{ display:"flex", flexDirection:"column", gap:4 }}>
      {label && <Label>{label}</Label>}
      <select value={value} onChange={onChange}
        style={{ background:T.surfaceAlt, border:`1px solid ${T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", width:"100%" }}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

function Card({ children, style, className="" }) {
  return <div className={className} style={{ background:T.surface, border:`1px solid ${T.border}`, borderRadius:8, padding:"1.5rem", ...style }}>{children}</div>;
}

function SectionHead({ label, sub, delay="" }) {
  return (
    <div className={delay ? `fu${delay}` : ""} style={{ marginBottom:"1.25rem" }}>
      <h2 style={{ fontFamily:"'Playfair Display',serif", fontSize:22, fontWeight:600, letterSpacing:"-0.02em", marginBottom:2 }}>{label}</h2>
      {sub && <p style={{ fontSize:13, color:T.inkSec }}>{sub}</p>}
      <div style={{ width:40, height:2, background:T.green, marginTop:8 }} />
    </div>
  );
}

function ScoreBar({ label, value, max=10, color=T.green }) {
  return (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
        <span style={{ fontSize:13 }}>{label}</span>
        <span style={{ fontFamily:"'DM Mono',monospace", fontSize:13, color }}>{value}/{max}</span>
      </div>
      <div style={{ height:6, background:T.surfaceAlt, borderRadius:3, overflow:"hidden" }}>
        <div style={{ height:"100%", borderRadius:3, width:`${(value/max)*100}%`, background:color, transition:"width 1s ease" }} />
      </div>
    </div>
  );
}

function ModeBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{ padding:"7px 16px", borderRadius:4, border:`1px solid ${active?T.ink:T.border}`, background:active?T.ink:"transparent", color:active?"#FFF":T.inkSec, fontSize:12, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:"pointer", fontFamily:"'Lato',sans-serif", transition:"all 0.15s" }}>
      {children}
    </button>
  );
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.2045c0-.638-.0573-1.252-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.6150z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.4673-.8059 5.9564-2.1805l-2.9087-2.2581c-.8059.54-1.8368.8582-3.0477.8582-2.3446 0-4.3282-1.5836-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z" fill="#34A853"/>
      <path d="M3.964 10.71c-.18-.54-.2823-1.1168-.2823-1.71s.1023-1.17.2823-1.71V4.9582H.9574C.3477 6.1732 0 7.5477 0 9s.3477 2.8268.9574 4.0418L3.964 10.71z" fill="#FBBC05"/>
      <path d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5813C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.9574 4.9582L3.964 7.29C4.6718 5.1632 6.6554 3.5795 9 3.5795z" fill="#EA4335"/>
    </svg>
  );
}

function TabBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{ padding:"8px 18px", borderRadius:4, whiteSpace:"nowrap", border:`1px solid ${active?T.ink:T.border}`, background:active?T.ink:"transparent", color:active?"#FFF":T.inkSec, fontSize:12, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:"pointer", fontFamily:"'Lato',sans-serif", transition:"all 0.15s" }}>
      {children}
    </button>
  );
}

const DAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
const DIETS = ["None","Vegetarian","Vegan","Keto","High Protein","Low Carb"];
const TABS  = [
  { id:"list",      label:"Shopping List" },
  { id:"stores",    label:"Store Prices"  },
  { id:"route",     label:"Route"         },
  { id:"nutrition", label:"Nutrition"     },
  { id:"subs",      label:"Substitutions" },
  { id:"budget",    label:"Budget"        },
];

const CHAT_SUGGESTIONS = [
  "What's in my pantry?",
  "Suggest a vegetarian meal",
  "What can I cook with rice and oil?",
  "Save my current meal plan",
];

const headerBtnStyle = {
  display:"flex", alignItems:"center", gap:8,
  padding:"8px 16px", borderRadius:6,
  border:"1px solid rgba(255,255,255,0.2)",
  background:"rgba(255,255,255,0.1)",
  color:"#FFF", fontSize:12, fontWeight:700,
  letterSpacing:"0.04em", textTransform:"uppercase",
  cursor:"pointer", fontFamily:"'Lato',sans-serif",
  transition:"all 0.15s",
};

// ── Price matrix ─────────────────────────────────────────────────────────────
function buildMatrix(stores) {
  const allItems = new Set();
  stores.forEach(s => (s.items||[]).forEach(i => allItems.add(i.item)));
  const items = [...allItems].sort();
  const matrix = {}, totals = {}, currencies = {};
  stores.forEach(s => {
    const n = s.store_name; totals[n]=0; matrix[n]={};
    (s.items||[]).forEach(i => {
      matrix[n][i.item]=i.price;
      totals[n]+=i.price;
      if (!currencies[n]) currencies[n] = i.currency || "USD";
    });
  });
  const wCounts={}, wTotals={};
  items.forEach(item => {
    let minP=Infinity, minS=null;
    stores.forEach(s => { const p=matrix[s.store_name]?.[item]; if(p!==undefined&&p<minP){minP=p;minS=s.store_name;} });
    if(minS){ wCounts[minS]=(wCounts[minS]||0)+1; wTotals[minS]=(wTotals[minS]||0)+minP; }
  });
  return { items, matrix, totals, currencies, wCounts, wTotals, overallCheapest:Object.values(wTotals).reduce((a,b)=>a+b,0) };
}

const CURRENCY_SYMBOLS = { USD:"$", INR:"₹", GBP:"£", CAD:"CA$", AUD:"A$", SGD:"S$", AED:"AED " };
function formatPrice(amount, currency="USD") {
  return `${CURRENCY_SYMBOLS[currency] || ""}${amount.toFixed(2)}`;
}

// ── Chat Panel ───────────────────────────────────────────────────────────────
function ChatPanel({ onClose, user, getToken }) {
  const [messages, setMessages] = useState([
    { role:"agent", text:"Hi! I'm your SmartCart AI assistant. I can check your pantry, suggest meals, and help plan your groceries. What would you like to know?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setChatLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const messagesEndRef = useRef(null);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages]);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg) return;
    setMessages(prev => [...prev, { role:"user", text:msg }]);
    setInput(""); setChatLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(AGENT_URL, {
        method:"POST",
        headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
        body: JSON.stringify({ message:msg, user_id:user?.uid??"anonymous", session_id:sessionId }),
      });
      const json = await res.json();
      setMessages(prev => [...prev, { role:"agent", text:json.response||"Sorry, I didn't get a response." }]);
    } catch {
      setMessages(prev => [...prev, { role:"agent", text:"⚠ Connection error. Please try again.", isError:true }]);
    } finally { setChatLoading(false); }
  };

  return (
    <div className="chat-panel" style={{ position:"fixed", top:0, right:0, width:380, height:"100vh", background:T.surface, borderLeft:`1px solid ${T.border}`, display:"flex", flexDirection:"column", zIndex:1000, boxShadow:"-4px 0 24px rgba(0,0,0,0.08)" }}>
      <div style={{ padding:"1rem 1.25rem", borderBottom:`1px solid ${T.border}`, display:"flex", alignItems:"center", justifyContent:"space-between", background:T.ink, color:"#FFF", flexShrink:0 }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <span style={{ fontSize:20 }}>🤖</span>
          <div>
            <div style={{ fontFamily:"'Playfair Display',serif", fontSize:15 }}>SmartCart <em style={{ fontWeight:400, color:T.greenMid }}>Agent</em></div>
            <div style={{ fontSize:10, opacity:0.5, letterSpacing:"0.08em", textTransform:"uppercase" }}>Powered by Gemini + ADK</div>
          </div>
        </div>
        <button onClick={onClose} style={{ background:"transparent", border:"none", color:"#FFF", fontSize:20, cursor:"pointer", opacity:0.7, padding:"4px 8px", borderRadius:4 }}>✕</button>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:"1rem", display:"flex", flexDirection:"column", gap:12 }}>
        {messages.map((msg,i) => (
          <div key={i} className={msg.role==="user"?"chat-msg-user":"chat-msg-agent"} style={{ display:"flex", justifyContent:msg.role==="user"?"flex-end":"flex-start" }}>
            <div style={{ maxWidth:"85%", padding:"10px 14px", borderRadius:msg.role==="user"?"12px 12px 2px 12px":"12px 12px 12px 2px", background:msg.role==="user"?T.ink:msg.isError?T.redLight:T.surfaceAlt, color:msg.role==="user"?"#FFF":msg.isError?T.red:T.ink, fontSize:13, lineHeight:1.6, border:`1px solid ${msg.role==="user"?"transparent":msg.isError?T.red+"33":T.border}` }}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && <div style={{ display:"flex", justifyContent:"flex-start" }}><div style={{ padding:"10px 14px", borderRadius:"12px 12px 12px 2px", background:T.surfaceAlt, border:`1px solid ${T.border}`, display:"flex", gap:5, alignItems:"center" }}>{[0,1,2].map(i=><div key={i} style={{ width:6, height:6, borderRadius:"50%", background:T.inkTer, animation:`pulse 1.2s ${i*0.2}s ease infinite` }}/>)}</div></div>}
        <div ref={messagesEndRef}/>
      </div>
      {messages.length===1 && (
        <div style={{ padding:"0 1rem 0.75rem", display:"flex", flexWrap:"wrap", gap:6, flexShrink:0 }}>
          {CHAT_SUGGESTIONS.map((s,i) => <button key={i} onClick={()=>sendMessage(s)} style={{ fontSize:11, padding:"4px 10px", borderRadius:20, border:`1px solid ${T.border}`, background:T.surfaceAlt, color:T.inkSec, cursor:"pointer", fontFamily:"'Lato',sans-serif", fontWeight:700 }}>{s}</button>)}
        </div>
      )}
      <div style={{ padding:"0.75rem 1rem", borderTop:`1px solid ${T.border}`, display:"flex", gap:8, flexShrink:0, background:T.surface }}>
        <textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage();}}} placeholder="Ask about your pantry, meals, or grocery list…" rows={2} style={{ flex:1, background:T.surfaceAlt, border:`1px solid ${T.border}`, borderRadius:6, padding:"8px 12px", fontSize:13, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", resize:"none", lineHeight:1.5 }}/>
        <button onClick={()=>sendMessage()} disabled={loading||!input.trim()} style={{ width:40, height:40, alignSelf:"flex-end", borderRadius:6, background:loading||!input.trim()?T.borderDark:T.green, border:"none", color:"#FFF", fontSize:16, cursor:loading||!input.trim()?"not-allowed":"pointer", display:"flex", alignItems:"center", justifyContent:"center", transition:"background 0.15s", flexShrink:0 }}>↑</button>
      </div>
    </div>
  );
}

// ── Pantry Page ──────────────────────────────────────────────────────────────
function PantryPage({ getToken }) {
  const [items, setItems]       = useState([]);
  const [input, setInput]       = useState("");
  const [mergeMode, setMerge]   = useState(true);
  const [saving, setSaving]     = useState(false);
  const [msg, setMsg]           = useState(null);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const fileRef = useRef(null);
  const hasSpeech = typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  // Load pantry on mount
  useEffect(() => {
    getToken().then(token =>
      fetch(`${BASE_URL}/debug/pantry/me`, {
        headers: token ? { Authorization:`Bearer ${token}` } : {}
      }).then(r=>r.json()).then(json => {
        const raw = json?.result?.items ?? [];
        setItems(Array.isArray(raw) ? raw : []);
      }).catch(()=>{})
    );
  }, [getToken]);

  const startListening = () => {
    if (!hasSpeech) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setInput(transcript);
      setListening(false);
    };
    rec.onerror = () => setListening(false);
    rec.onend   = () => setListening(false);
    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    setListening(false);
  };

  const addItem = () => {
    const v = input.trim();
    if (!v) return;
    if (!items.includes(v.toLowerCase())) {
      setItems(prev => [...prev, v.toLowerCase()]);
    }
    setInput("");
  };

  const removeItem = (item) => setItems(prev => prev.filter(i => i !== item));

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target.result;
      const parsed = text.split(/[\n,]+/).map(s=>s.trim().toLowerCase()).filter(Boolean);
      setItems(prev => {
        const merged = mergeMode ? [...new Set([...prev, ...parsed])] : [...new Set(parsed)];
        return merged;
      });
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const savePantry = async () => {
    setSaving(true); setMsg(null);
    try {
      const token = await getToken();
      const res = await fetch(`${BASE_URL}/pantry`, {
        method:"PUT",
        headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
        body: JSON.stringify({ items }),
      });
      if (!res.ok) throw new Error("Save failed");
      setMsg({ type:"success", text:`✓ Pantry saved — ${items.length} items` });
    } catch (e) {
      setMsg({ type:"error", text:`⚠ ${e.message}` });
    } finally { setSaving(false); }
  };

  return (
    <div style={{ maxWidth:700, margin:"0 auto", padding:"2rem 1.5rem" }}>
      <SectionHead label="My Pantry" sub="Manage items you already have at home" />

      <Card style={{ marginBottom:"1.5rem" }}>
        <Label>Add Items</Label>
        <div style={{ display:"flex", gap:8, marginBottom:12 }}>
          <input
            value={input}
            onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{ if(e.key==="Enter") addItem(); }}
            placeholder="Type an item and press Enter…"
            style={{ flex:1, background:T.surfaceAlt, border:`1px solid ${T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none" }}
          />
          {hasSpeech && (
            <button
              onClick={listening ? stopListening : startListening}
              className={listening ? "mic-active" : ""}
              title={listening ? "Stop listening" : "Speak to add item"}
              style={{ width:44, height:44, borderRadius:6, border:"none", background:listening?T.red:T.surfaceAlt, color:listening?"#FFF":T.inkSec, fontSize:18, cursor:"pointer", flexShrink:0, transition:"background 0.15s" }}
            >🎤</button>
          )}
          <button onClick={addItem} style={{ padding:"10px 18px", borderRadius:4, border:"none", background:T.green, color:"#FFF", fontSize:13, fontWeight:700, cursor:"pointer", fontFamily:"'Lato',sans-serif", flexShrink:0 }}>Add</button>
        </div>

        {!hasSpeech && (
          <p style={{ fontSize:11, color:T.inkSec, marginBottom:12 }}>💡 Use Chrome or Edge for voice input support.</p>
        )}

        <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:8 }}>
          <button onClick={()=>fileRef.current?.click()} style={{ fontSize:12, padding:"7px 14px", borderRadius:4, border:`1px solid ${T.border}`, background:T.surfaceAlt, color:T.inkSec, cursor:"pointer", fontFamily:"'Lato',sans-serif", fontWeight:700 }}>
            📁 Upload CSV / TXT
          </button>
          <input ref={fileRef} type="file" accept=".csv,.txt" onChange={handleFileUpload} style={{ display:"none" }}/>
          <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, color:T.inkSec, cursor:"pointer" }}>
            <input type="checkbox" checked={mergeMode} onChange={e=>setMerge(e.target.checked)} />
            Merge with existing (uncheck to replace)
          </label>
        </div>
      </Card>

      <Card style={{ marginBottom:"1.5rem" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1rem" }}>
          <Label>Current Pantry ({items.length} items)</Label>
          {items.length > 0 && (
            <button onClick={()=>setItems([])} style={{ fontSize:11, color:T.red, background:"none", border:"none", cursor:"pointer", fontWeight:700 }}>Clear all</button>
          )}
        </div>
        {!items.length ? (
          <p style={{ color:T.inkSec, fontSize:13 }}>No pantry items yet. Add some above.</p>
        ) : (
          <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
            {items.map(item => (
              <div key={item} style={{ display:"flex", alignItems:"center", gap:6, padding:"5px 12px", borderRadius:20, background:T.greenLight, border:`1px solid ${T.green}33`, fontSize:13 }}>
                <span style={{ textTransform:"capitalize" }}>{item}</span>
                <button onClick={()=>removeItem(item)} style={{ background:"none", border:"none", color:T.green, cursor:"pointer", fontSize:14, lineHeight:1, padding:0, fontWeight:700 }}>×</button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <button onClick={savePantry} disabled={saving} style={{ width:"100%", padding:"14px", background:saving?T.borderDark:T.ink, color:"#FFF", border:"none", borderRadius:4, fontSize:14, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:saving?"not-allowed":"pointer", fontFamily:"'Lato',sans-serif", transition:"background 0.15s" }}>
        {saving ? "Saving…" : "💾 Save Pantry to Profile"}
      </button>

      {msg && (
        <div style={{ marginTop:12, padding:"10px 14px", borderRadius:6, fontSize:13, fontWeight:500, background:msg.type==="success"?T.greenLight:T.redLight, color:msg.type==="success"?T.green:T.red, border:`1px solid ${msg.type==="success"?T.green+"33":T.red+"33"}` }}>
          {msg.text}
        </div>
      )}
    </div>
  );
}

// ── Feedback Page ────────────────────────────────────────────────────────────
function FeedbackPage({ getToken }) {
  const [email,   setEmail]   = useState("");
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [msg,     setMsg]     = useState(null);

  const submitFeedback = async () => {
    if (!comment.trim()) {
      setMsg({ type:"error", text:"⚠ Please enter your feedback before submitting." });
      return;
    }
    setSending(true); setMsg(null);
    try {
      const token = await getToken();
      const res = await fetch(`${BASE_URL}/feedback`, {
        method:"POST",
        headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
        body: JSON.stringify({ email, comment }),
      });
      const json = await res.json();
      if (!res.ok || !json.success) throw new Error(json.error || "Failed to send feedback");
      setMsg({ type:"success", text:"✓ Thank you! Your feedback has been sent." });
      setComment("");
    } catch (e) {
      setMsg({ type:"error", text:`⚠ ${e.message}` });
    } finally { setSending(false); }
  };

  return (
    <div style={{ maxWidth:700, margin:"0 auto", padding:"2rem 1.5rem" }}>
      <SectionHead label="Feedback" sub="Share ideas, report issues, or tell us what's working" />

      <Card style={{ marginBottom:"1.5rem" }}>
        <Label>Your Email (so we can follow up)</Label>
        <input
          type="email"
          value={email}
          onChange={e=>setEmail(e.target.value)}
          placeholder="you@example.com"
          style={{ width:"100%", background:T.surfaceAlt, border:`1px solid ${T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", marginBottom:16, boxSizing:"border-box" }}
        />

        <Label>Your Feedback</Label>
        <textarea
          value={comment}
          onChange={e=>setComment(e.target.value)}
          placeholder="What would you improve? Did something not work as expected during testing? Let us know…"
          rows={6}
          style={{ width:"100%", background:T.surfaceAlt, border:`1px solid ${T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", resize:"vertical", boxSizing:"border-box" }}
        />
      </Card>

      <button onClick={submitFeedback} disabled={sending} style={{ width:"100%", padding:"14px", background:sending?T.borderDark:T.ink, color:"#FFF", border:"none", borderRadius:4, fontSize:14, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:sending?"not-allowed":"pointer", fontFamily:"'Lato',sans-serif", transition:"background 0.15s" }}>
        {sending ? "Sending…" : "📩 Send Feedback"}
      </button>

      {msg && (
        <div style={{ marginTop:12, padding:"10px 14px", borderRadius:6, fontSize:13, fontWeight:500, background:msg.type==="success"?T.greenLight:T.redLight, color:msg.type==="success"?T.green:T.red, border:`1px solid ${msg.type==="success"?T.green+"33":T.red+"33"}` }}>
          {msg.text}
        </div>
      )}
    </div>
  );
}


// ── Recipe Page ──────────────────────────────────────────────────────────────
const MAX_INGREDIENTS = 20;
const MAX_ING_LEN     = 50;
const MAX_INSTRUCTIONS = 8;
const MAX_INST_LEN     = 100;

function RecipePage({ getToken }) {
  const [recipes, setRecipes]           = useState([]);
  const [selected, setSelected]         = useState(null);
  const [ingredients, setIngredients]   = useState([]);
  const [instructions, setInstructions] = useState([]);
  const [saving, setSaving]             = useState(false);
  const [msg, setMsg]                   = useState(null);
  const [loading, setLoading]           = useState(true);

  useEffect(() => {
    getToken().then(token =>
      fetch(`${BASE_URL}/recipes/me`, {
        headers: token ? { Authorization:`Bearer ${token}` } : {}
      }).then(r=>r.json()).then(json => {
        setRecipes(json.recipes || []);
        setLoading(false);
      }).catch(()=>setLoading(false))
    );
  }, [getToken]);

  const selectRecipe = (meal) => {
    const r = recipes.find(r => r.meal === meal);
    if (!r) return;
    setSelected(r);
    setIngredients(r.ingredients || []);
    setInstructions(r.instructions || []);
    setMsg(null);
  };

  const updateIngredient = (i, val) => {
    const next = [...ingredients];
    next[i] = val.slice(0, MAX_ING_LEN);
    setIngredients(next);
  };

  const removeIngredient = (i) => setIngredients(prev => prev.filter((_,idx)=>idx!==i));
  const addIngredient = () => {
    if (ingredients.length >= MAX_INGREDIENTS) return;
    setIngredients(prev => [...prev, ""]);
  };

  const updateInstruction = (i, val) => {
    const next = [...instructions];
    next[i] = val.slice(0, MAX_INST_LEN);
    setInstructions(next);
  };

  const removeInstruction = (i) => setInstructions(prev => prev.filter((_,idx)=>idx!==i));
  const addInstruction = () => {
    if (instructions.length >= MAX_INSTRUCTIONS) return;
    setInstructions(prev => [...prev, ""]);
  };

  const ingValid  = ingredients.every(i => i.trim().length > 0 && i.length <= MAX_ING_LEN);
  const instValid = instructions.every(s => s.trim().length > 0 && s.length <= MAX_INST_LEN);
  const canSave   = selected && ingValid && instValid && ingredients.length > 0;

  const saveRecipe = async () => {
    if (!canSave) return;
    setSaving(true); setMsg(null);
    try {
      const token = await getToken();
      const res = await fetch(`${BASE_URL}/recipes`, {
        method:"PUT",
        headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
        body: JSON.stringify({ meal:selected.meal, ingredients, instructions }),
      });
      if (!res.ok) throw new Error("Save failed");
      setMsg({ type:"success", text:"✓ Recipe saved successfully" });
      // Update local list
      setRecipes(prev => prev.map(r => r.meal===selected.meal ? {...r, ingredients, instructions} : r));
    } catch(e) {
      setMsg({ type:"error", text:`⚠ ${e.message}` });
    } finally { setSaving(false); }
  };

  if (loading) return (
    <div style={{ display:"flex", justifyContent:"center", padding:"4rem" }}>
      <div style={{ width:36, height:36, border:`3px solid ${T.border}`, borderTop:`3px solid ${T.green}`, borderRadius:"50%", animation:"spin 0.8s linear infinite" }}/>
    </div>
  );

  return (
    <div style={{ maxWidth:800, margin:"0 auto", padding:"2rem 1.5rem" }}>
      <SectionHead label="My Recipes" sub="View, edit, and save your meal recipes" />

      {!recipes.length ? (
        <Card>
          <p style={{ color:T.inkSec, fontSize:14 }}>No recipes saved yet. Generate a meal plan to get started.</p>
        </Card>
      ) : (
        <>
          <Card style={{ marginBottom:"1.5rem" }}>
            <Label>Select a Recipe</Label>
            <select
              value={selected?.meal || ""}
              onChange={e=>selectRecipe(e.target.value)}
              style={{ width:"100%", background:T.surfaceAlt, border:`1px solid ${T.border}`, borderRadius:4, padding:"10px 12px", fontSize:14, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none" }}
            >
              <option value="">— Choose a recipe —</option>
              {recipes.map(r => (
                <option key={r.meal} value={r.meal} style={{ textTransform:"capitalize" }}>
                  {r.meal.split("|")[0].replace(/\b\w/g,c=>c.toUpperCase())}
                </option>
              ))}
            </select>
          </Card>

          {selected && (
            <div className="fu">
              {/* Ingredients */}
              <Card style={{ marginBottom:"1.5rem" }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1rem" }}>
                  <div>
                    <Label>Ingredients</Label>
                    <p style={{ fontSize:11, color:T.inkSec }}>Max {MAX_INGREDIENTS} items · {MAX_ING_LEN} chars each</p>
                  </div>
                  <span style={{ fontSize:12, color:ingredients.length>=MAX_INGREDIENTS?T.red:T.inkSec, fontWeight:700 }}>{ingredients.length}/{MAX_INGREDIENTS}</span>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {ingredients.map((ing, i) => (
                    <div key={i} style={{ display:"flex", gap:8, alignItems:"center" }}>
                      <div style={{ flex:1, position:"relative" }}>
                        <input
                          value={ing}
                          onChange={e=>updateIngredient(i, e.target.value)}
                          placeholder={`Ingredient ${i+1}`}
                          style={{ width:"100%", background:T.surfaceAlt, border:`1px solid ${ing.length>=MAX_ING_LEN?T.red:T.border}`, borderRadius:4, padding:"8px 12px", fontSize:13, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none" }}
                        />
                        <span style={{ position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", fontSize:10, color:ing.length>=MAX_ING_LEN?T.red:T.inkTer, fontFamily:"'DM Mono',monospace" }}>{ing.length}/{MAX_ING_LEN}</span>
                      </div>
                      <button onClick={()=>removeIngredient(i)} style={{ background:"none", border:"none", color:T.red, cursor:"pointer", fontSize:18, padding:"0 4px", flexShrink:0 }}>×</button>
                    </div>
                  ))}
                </div>
                {ingredients.length < MAX_INGREDIENTS && (
                  <button onClick={addIngredient} style={{ marginTop:10, fontSize:12, padding:"6px 14px", borderRadius:4, border:`1px dashed ${T.border}`, background:"transparent", color:T.inkSec, cursor:"pointer", fontFamily:"'Lato',sans-serif", width:"100%" }}>
                    + Add Ingredient
                  </button>
                )}
              </Card>

              {/* Instructions */}
              <Card style={{ marginBottom:"1.5rem" }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1rem" }}>
                  <div>
                    <Label>Instructions</Label>
                    <p style={{ fontSize:11, color:T.inkSec }}>Max {MAX_INSTRUCTIONS} steps · {MAX_INST_LEN} chars each</p>
                  </div>
                  <span style={{ fontSize:12, color:instructions.length>=MAX_INSTRUCTIONS?T.red:T.inkSec, fontWeight:700 }}>{instructions.length}/{MAX_INSTRUCTIONS}</span>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {instructions.map((inst, i) => (
                    <div key={i} style={{ display:"flex", gap:8, alignItems:"flex-start" }}>
                      <span style={{ fontSize:12, fontWeight:700, color:T.inkSec, fontFamily:"'DM Mono',monospace", minWidth:24, paddingTop:10 }}>{i+1}.</span>
                      <div style={{ flex:1, position:"relative" }}>
                        <textarea
                          value={inst}
                          onChange={e=>updateInstruction(i, e.target.value)}
                          placeholder={`Step ${i+1}: Action verb + details…`}
                          rows={2}
                          style={{ width:"100%", background:T.surfaceAlt, border:`1px solid ${inst.length>=MAX_INST_LEN?T.red:T.border}`, borderRadius:4, padding:"8px 12px", fontSize:13, color:T.ink, fontFamily:"'Lato',sans-serif", outline:"none", resize:"none" }}
                        />
                        <span style={{ position:"absolute", right:8, bottom:6, fontSize:10, color:inst.length>=MAX_INST_LEN?T.red:T.inkTer, fontFamily:"'DM Mono',monospace" }}>{inst.length}/{MAX_INST_LEN}</span>
                      </div>
                      <button onClick={()=>removeInstruction(i)} style={{ background:"none", border:"none", color:T.red, cursor:"pointer", fontSize:18, padding:"0 4px", flexShrink:0, paddingTop:8 }}>×</button>
                    </div>
                  ))}
                </div>
                {instructions.length < MAX_INSTRUCTIONS && (
                  <button onClick={addInstruction} style={{ marginTop:10, fontSize:12, padding:"6px 14px", borderRadius:4, border:`1px dashed ${T.border}`, background:"transparent", color:T.inkSec, cursor:"pointer", fontFamily:"'Lato',sans-serif", width:"100%" }}>
                    + Add Step
                  </button>
                )}
              </Card>

              <button onClick={saveRecipe} disabled={!canSave||saving} style={{ width:"100%", padding:"14px", background:!canSave||saving?T.borderDark:T.ink, color:"#FFF", border:"none", borderRadius:4, fontSize:14, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:!canSave||saving?"not-allowed":"pointer", fontFamily:"'Lato',sans-serif", transition:"background 0.15s" }}>
                {saving ? "Saving…" : "💾 Save Recipe"}
              </button>

              {msg && (
                <div style={{ marginTop:12, padding:"10px 14px", borderRadius:6, fontSize:13, fontWeight:500, background:msg.type==="success"?T.greenLight:T.redLight, color:msg.type==="success"?T.green:T.red, border:`1px solid ${msg.type==="success"?T.green+"33":T.red+"33"}` }}>
                  {msg.text}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Login Page ───────────────────────────────────────────────────────────────
function LoginPage({ onSignIn }) {
  return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center", background:T.bg, padding:"2rem" }}>
      <div style={{ width:"100%", maxWidth:1200, display:"grid", gridTemplateColumns:"1fr 1fr", gap:32, alignItems:"stretch" }}>
        <div style={{ background:T.surface, border:`1px solid ${T.border}`, borderRadius:24, boxShadow:"0 32px 80px rgba(0,0,0,0.08)", padding:"3rem", display:"flex", flexDirection:"column", justifyContent:"center" }}>
          <div style={{ marginBottom:28, maxWidth:520 }}>
            <div style={{ textTransform:"uppercase", letterSpacing:"0.24em", fontSize:12, fontWeight:700, color:T.greenMid, marginBottom:14 }}>SmartCart AI</div>
            <h1 style={{ fontFamily:"'Playfair Display',serif", fontSize:42, lineHeight:1.05, marginBottom:18, color:T.ink }}>Secure Google sign-in for your shopping intelligence.</h1>
            <p style={{ fontSize:16, color:T.inkSec, lineHeight:1.8 }}>Access your meal plans, pantry data, store comparisons, and AI shopping assistant with a single Google login.</p>
          </div>
          <button onClick={onSignIn} style={{ display:"inline-flex", alignItems:"center", justifyContent:"center", gap:12, width:"100%", padding:"14px 18px", borderRadius:14, border:"none", background:T.green, color:"#FFF", fontSize:15, fontWeight:700, cursor:"pointer", boxShadow:"0 14px 30px rgba(45,106,79,0.18)", transition:"transform 0.15s ease" }}>
            <GoogleIcon /> Sign in with Google
          </button>
        </div>
        <div style={{ borderRadius:24, overflow:"hidden", position:"relative", minHeight:420, display:"flex", alignItems:"center", justifyContent:"center", background:`linear-gradient(135deg, ${T.greenLight} 0%, ${T.blueLight} 100%)` }}>
          <div style={{ position:"relative", padding:"3rem", color:T.ink, textAlign:"center", maxWidth:420 }}>
            <div style={{ fontSize:72, marginBottom:18 }}>🛒</div>
            <h2 style={{ fontFamily:"'Playfair Display',serif", fontSize:34, marginBottom:16, letterSpacing:"-0.04em" }}>Welcome back.</h2>
            <p style={{ fontSize:16, color:T.inkSec, lineHeight:1.8 }}>Your personal grocery planner is ready. Sign in to continue building smarter meals and a healthier kitchen.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Receipt Page ───────────────────────────────────────────────────────────────

function ReceiptPage({ getToken }) {
  const [file,         setFile]         = useState(null);
  const [preview,      setPreview]      = useState(null);
  const [storeName,    setStoreName]    = useState("");
  const [address,      setAddress]      = useState("");
  const [city,         setCity]         = useState("");
  const [state,        setState]        = useState("");
  const [country,      setCountry]      = useState("US");
  const [uploading,    setUploading]    = useState(false);
  const [result,       setResult]       = useState(null);
  const [error,        setError]        = useState(null);
  const fileRef = useRef(null);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);

    // Preview for images only
    if (f.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (ev) => setPreview(ev.target.result);
      reader.readAsDataURL(f);
    } else {
      setPreview(null);
    }
    e.target.value = "";
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setResult(null); setError(null);

    try {
      // Convert file to base64
      const base64 = await new Promise((res, rej) => {
        const reader = new FileReader();
        reader.onload  = (e) => res(e.target.result.split(",")[1]);
        reader.onerror = () => rej(new Error("File read failed"));
        reader.readAsDataURL(file);
      });

      const token = await getToken();
      const res = await fetch(`${BASE_URL}/receipt/upload`, {
        method: "POST",
        headers: {
          "Content-Type":  "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          image_base64: base64,
          media_type:   file.type,
          store_name:   storeName,
          address,
          city,
          state,
          country,
        }),
      });

      const json = await res.json();
      if (json.success) {
        setResult(json);
        // Auto-fill store name if Gemini extracted it
        if (json.store_name && !storeName) setStoreName(json.store_name);
      } else if (json.error === "Could not determine store location. Please enter city and state.") {
        // Gemini got items but no location — show partial result and ask for location
        setError("Receipt parsed but location is missing. Please enter City and State below and upload again.");
        if (json.store_name && !storeName) setStoreName(json.store_name);
      } else {
        setError(json.error || "Upload failed");
      }
    } catch (e) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ maxWidth:700, margin:"0 auto", padding:"2rem 1.5rem" }}>
      <SectionHead label="Upload Receipt" sub="Extract real store prices from your grocery receipt" />

      {/* File Upload */}
      <Card style={{ marginBottom:"1.5rem" }}>
        <Label>Receipt Photo or PDF</Label>
        <div
          onClick={() => fileRef.current?.click()}
          style={{
            border: `2px dashed ${file ? T.green : T.border}`,
            borderRadius: 8, padding: "2rem", textAlign: "center",
            cursor: "pointer", background: file ? T.greenLight : T.surfaceAlt,
            transition: "all 0.15s", marginBottom: 12,
          }}
        >
          {preview ? (
            <img src={preview} alt="Receipt preview"
              style={{ maxHeight: 300, maxWidth: "100%", borderRadius: 4, objectFit: "contain" }} />
          ) : (
            <div>
              <div style={{ fontSize: 40, marginBottom: 8 }}>📄</div>
              <div style={{ fontSize: 14, color: T.inkSec }}>
                {file ? file.name : "Click to upload receipt photo or PDF"}
              </div>
              <div style={{ fontSize: 11, color: T.inkTer, marginTop: 4 }}>
                JPG, PNG, or PDF • Max 10MB
              </div>
            </div>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,application/pdf"
          onChange={handleFile} style={{ display: "none" }} />
        {file && (
          <div style={{ fontSize: 12, color: T.green, fontWeight: 700 }}>
            ✓ {file.name} ({(file.size / 1024).toFixed(0)} KB)
          </div>
        )}
      </Card>

      {/* Store Details */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <Label>Store Details</Label>
          <p style={{ fontSize: 11, color: T.inkSec }}>
            Optional if visible on receipt — Gemini will try to extract these automatically.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ gridColumn: "1 / -1" }}>
            <Input label="Store Name" value={storeName} onChange={e => setStoreName(e.target.value)} placeholder="e.g. Walmart, Whole Foods" />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <Input label="Address (optional)" value={address} onChange={e => setAddress(e.target.value)} placeholder="123 Main St" />
          </div>
          <Input label="City *" value={city} onChange={e => setCity(e.target.value)} placeholder="Maryland Heights" />
          <Input label="State *" value={state} onChange={e => setState(e.target.value)} placeholder="Missouri" />
          <Input label="Country" value={country} onChange={e => setCountry(e.target.value)} placeholder="US" />
        </div>
        <p style={{ fontSize: 11, color: T.red, marginTop: 8 }}>* City and State are required for price lookup</p>
      </Card>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        style={{
          width: "100%", padding: "14px",
          background: !file || uploading ? T.borderDark : T.ink,
          color: "#FFF", border: "none", borderRadius: 4,
          fontSize: 14, fontWeight: 700, letterSpacing: "0.04em",
          textTransform: "uppercase", cursor: !file || uploading ? "not-allowed" : "pointer",
          fontFamily: "'Lato',sans-serif", transition: "background 0.15s",
          marginBottom: "1rem",
        }}
      >
        {uploading ? (
          <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <span style={{ width: 16, height: 16, border: "2px solid rgba(255,255,255,0.3)", borderTop: "2px solid #FFF", borderRadius: "50%", display: "inline-block", animation: "spin 0.8s linear infinite" }} />
            Analyzing Receipt…
          </span>
        ) : "📤 Upload & Extract Prices"}
      </button>

      {/* Error */}
      {error && (
        <div style={{ padding: "12px 16px", borderRadius: 6, background: T.redLight, border: `1px solid ${T.red}33`, color: T.red, fontSize: 13, marginBottom: "1rem" }}>
          ⚠ {error}
        </div>
      )}

      {/* Success Result */}
      {result && (
        <Card className="fu" style={{ borderColor: T.green }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "1rem" }}>
            <span style={{ fontSize: 24 }}>✅</span>
            <div>
              <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 16, fontWeight: 600 }}>
                {result.store_name}
              </div>
              <div style={{ fontSize: 12, color: T.inkSec }}>
                {result.city}, {result.state} · {result.item_count} items saved
              </div>
            </div>
          </div>

          <div style={{ marginBottom: "0.75rem" }}>
            <Label>Preview (first 5 items extracted)</Label>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {Object.entries(result.items_preview || {}).map(([item, data]) => (
                <div key={item} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "8px 12px", background: T.surfaceAlt, borderRadius: 6,
                  border: `1px solid ${T.border}`, fontSize: 13,
                }}>
                  <span style={{ textTransform: "capitalize" }}>{item}</span>
                  <span style={{ fontFamily: "'DM Mono',monospace", color: T.green, fontWeight: 700 }}>
                    {formatPrice(typeof data === "object" ? (data.price ?? 0) : Number(data), typeof data === "object" ? (data.currency || "USD") : "USD")}
                    {typeof data === "object" && data.unit ? ` / ${data.unit}` : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ padding: "10px 14px", borderRadius: 6, background: T.greenLight, fontSize: 12, color: T.green, fontWeight: 600 }}>
            ✓ Real prices saved! When you generate a meal plan in {result.city}, these prices will be used instead of estimates.
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────────────────
export default function SmartCartAI() {
  const [user,        setUser]        = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [page,        setPage]        = useState("home"); // home | pantry | recipes
  const [navOpen,     setNavOpen]     = useState(false);

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => { setUser(u); setAuthLoading(false); });
  }, []);

  const getToken = useCallback(async () => {
    if (!user) return null;
    try { return await user.getIdToken(); } catch { return null; }
  }, [user]);

  const handleSignIn  = () => signInWithPopup(auth, provider).catch(console.error);
  const handleSignOut = () => signOut(auth).catch(console.error);

  // ── Home page state ───────────────────────────────────────────────────────
  const [mode,         setMode]         = useState("meal");
  const [planType,     setPlanType]     = useState("single");
  const [dish,         setDish]         = useState("");
  const [weeklyMeals,  setWeeklyMeals]  = useState({});
  const [manualText,   setManualText]   = useState("");
  const [pantryText,   setPantryText]   = useState("");
  const [dietary,      setDietary]      = useState("None");
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [data,         setData]         = useState(null);
  const [activeTab,    setActiveTab]    = useState("list");
  const [selectedSubs, setSelectedSubs] = useState({});
  const [regenLoading, setRegenLoading] = useState(false);
  const [regenMsg,     setRegenMsg]     = useState(null);
  const [chatOpen,     setChatOpen]     = useState(false);
  const [userLatLng,   setUserLatLng]   = useState(null);
  const resultsRef     = useRef(null);
  const lastPayloadRef = useRef(null);
  const [showLocationModal, setShowLocationModal] = useState(false);
  const [manualCity, setManualCity] = useState("");
  const [manualState, setManualState] = useState("");
  const [manualPostalCode, setManualPostalCode] = useState("");
  const [manualLocationSet, setManualLocationSet] = useState(false);

  useEffect(() => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => setUserLatLng({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setShowLocationModal(true)   // GPS denied/unavailable — ask manually instead
    );
  } else {
    setShowLocationModal(true);          // browser has no geolocation support at all
  }
}, []);

  // Load pantry on sign-in
  useEffect(() => {
    if (authLoading || !user) return;
    getToken().then(token =>
      fetch(`${BASE_URL}/debug/pantry/me`, {
        headers: token ? { Authorization:`Bearer ${token}` } : {}
      }).then(r=>r.json()).then(json => {
        const raw = json?.result?.items ?? [];
        const items = Array.isArray(raw)
          ? raw.map(i=>(typeof i==="string"?i:i?.name||i?.item||"")).filter(Boolean)
          : [];
        if (items.length) setPantryText(items.join(", "));
      }).catch(()=>{})
    );
  }, [user, authLoading, getToken]);

  const syncPantry = async (items) => {
    if (!items?.length || !user) return;
    const token = await getToken();
    fetch(`${BASE_URL}/pantry`, {
      method:"PUT",
      headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
      body: JSON.stringify({ items }),
    }).catch(()=>{});
  };

  const handleRegenerate = async () => {
    if (!data) return;
    setRegenLoading(true); setRegenMsg(null);
    const normalizedSubs = Object.fromEntries(
      Object.entries(selectedSubs).filter(([,v])=>v&&v!=="Keep original").map(([k,v])=>[k.toLowerCase().trim(),v])
    );
    const updatedList = (data.shopping_list||[]).map(item => {
      const itemLower = item.toLowerCase().trim();
      const matchedKey = Object.keys(normalizedSubs).find(key=>itemLower===key||itemLower.includes(key)||key.includes(itemLower));
      return matchedKey ? normalizedSubs[matchedKey] : item;
    });
    const pantryItems = pantryText.split(",").map(x=>x.trim().toLowerCase()).filter(Boolean);
    try {
      const regenPayload = {
        ...lastPayloadRef.current,
        manual_items: updatedList,
        pantry_items: pantryItems,
        selected_substitutions: Object.fromEntries(Object.entries(selectedSubs).filter(([,v])=>v&&v!=="Keep original")),
        force_refresh: true,
      };
      const token = await getToken();
      const res = await fetch(API_URL, {
        method:"POST",
        headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
        body: JSON.stringify(regenPayload),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const savedCount = activeSubCount;
      setData(json); setSelectedSubs({}); setActiveTab("list");
      setRegenMsg(`✓ Plan regenerated! ${savedCount} substitution(s) saved.`);
      resultsRef.current?.scrollIntoView({ behavior:"smooth" });
    } catch(e) {
      setRegenMsg(`⚠ Regeneration failed: ${e.message}`);
    } finally { setRegenLoading(false); }
  };

  const activeSubCount = Object.values(selectedSubs).filter(v=>v&&v!=="Keep original").length;

  const handleGenerate = async () => {
    setError(null); setData(null); setLoading(true);
    const manualItems = manualText.split(",").map(x=>x.trim().toLowerCase()).filter(Boolean);
    const pantryItems = pantryText.split(",").map(x=>x.trim().toLowerCase()).filter(Boolean);
    let weekly = {};
    if (mode !== "list") {
      if (planType==="single"&&dish.trim()) weekly = { meal_1:dish.trim() };
      else weekly = Object.fromEntries(Object.entries(weeklyMeals).filter(([,v])=>v.trim()));
    }
    if (!Object.keys(weekly).length&&!manualItems.length) {
      setError("Please enter a meal or shopping items."); setLoading(false); return;
    }
    try {
      const modeStr = mode==="meal"?"🍽️ Single Meal":mode==="weekly"?"📅 Weekly Meals":mode==="list"?"🛍️ Shopping List Only":"🍽️ + 🛍️ Meal & Shopping List";
      const payload = {
        weekly_meals: weekly, manual_items: manualItems, budget:100,
        pantry_items: pantryItems, dietary_instruction: dietary, mode: modeStr,
        ...(userLatLng?{user_lat:userLatLng.lat,user_lng:userLatLng.lng}:{}),
        ...(manualLocationSet?{manual_city:manualCity,manual_state:manualState,manual_postal_code:manualPostalCode}:{}),
      };
      lastPayloadRef.current = payload;
      const token = await getToken();
      const res = await fetch(API_URL, {
        method:"POST",
        headers:{ "Content-Type":"application/json", ...(token?{Authorization:`Bearer ${token}`}:{}) },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      await new Promise(r=>setTimeout(r,100));
      setData(json); setActiveTab("list");
      syncPantry(pantryItems);
      setTimeout(()=>resultsRef.current?.scrollIntoView({behavior:"smooth"}),100);
    } catch(e) {
      setError(e.message||"Something went wrong.");
    } finally { setLoading(false); }
  };

  const submitManualLocation = () => {
    const hasCityState = manualCity.trim() && manualState.trim();
    const hasPostalCode = manualPostalCode.trim();
    if (!hasCityState && !hasPostalCode) return;
    setManualLocationSet(true);
    setShowLocationModal(false);
  };

  const stores   = data?.recommended_stores ?? [];
  const route    = data?.optimized_route    ?? [];
  const list     = data?.shopping_list      ?? [];
  const subs     = data?.substitutions      ?? {};
  const loc      = data?.user_location      ?? {};
  const nutr     = data?.nutrition_report   ?? {};
  const scores   = nutr.nutrition_scores    ?? {};
  const feedback = nutr.ai_feedback         ?? {};
  const budgetOpt = data?.budget_summary?.optimization ?? {};
  const pm = stores.length ? buildMatrix(stores) : null;
  const pmExpensiveStore = pm ? Object.entries(pm.totals).sort((a,b)=>b[1]-a[1])[0]?.[0] : null;
  const pmCheapestStore  = pm ? Object.entries(pm.totals).sort((a,b)=>a[1]-b[1])[0]?.[0] : null;
  const pmOriginalCost   = pm&&pmExpensiveStore ? pm.totals[pmExpensiveStore].toFixed(2) : (budgetOpt.original_cost??0);
  const pmOptimizedCost  = pm ? pm.overallCheapest.toFixed(2) : (budgetOpt.optimized_cost??0);
  const pmMoneySaved     = Math.max(0,parseFloat(pmOriginalCost)-parseFloat(pmOptimizedCost)).toFixed(2);
  const pmCurrency       = pm ? (Object.values(pm.currencies)[0]||"USD") : (budgetOpt.currency||"USD");

  if (authLoading) return (
    <><style>{css}</style>
    <div style={{ display:"flex", alignItems:"center", justifyContent:"center", height:"100vh", background:T.bg }}>
      <div style={{ width:36, height:36, border:`3px solid ${T.border}`, borderTop:`3px solid ${T.green}`, borderRadius:"50%", animation:"spin 0.8s linear infinite" }}/>
    </div></>
  );

  if (!user) return (<><style>{css}</style><LoginPage onSignIn={handleSignIn}/></>);

  return (
    <>
      <style>{css}</style>

      {/* Nav overlay */}
      {navOpen && <div onClick={()=>setNavOpen(false)} style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.3)", zIndex:200 }}/>}

      {/* Left slide-out nav */}
      {navOpen && (
        <div className="nav-panel" style={{ position:"fixed", top:0, left:0, width:260, height:"100vh", background:T.surface, borderRight:`1px solid ${T.border}`, zIndex:300, display:"flex", flexDirection:"column", boxShadow:"4px 0 24px rgba(0,0,0,0.1)" }}>
          <div style={{ padding:"1.25rem 1.5rem", borderBottom:`1px solid ${T.border}`, display:"flex", alignItems:"center", justifyContent:"space-between", background:T.ink, color:"#FFF" }}>
            <div style={{ fontFamily:"'Playfair Display',serif", fontSize:16 }}>SmartCart <em style={{ fontWeight:400, color:T.greenMid }}>AI</em></div>
            <button onClick={()=>setNavOpen(false)} style={{ background:"transparent", border:"none", color:"#FFF", fontSize:20, cursor:"pointer", opacity:0.7 }}>✕</button>
          </div>
          <nav style={{ padding:"1rem 0", flex:1 }}>
            {[
              { id:"home",    icon:"🏠", label:"Home"    },
              { id:"pantry",  icon:"🥦", label:"Pantry"  },
              { id:"recipes", icon:"📖", label:"Recipes" },
              { id:"receipt", icon:"📄", label:"Upload Receipt" },
              { id:"feedback", icon:"💬", label:"Feedback" },
            ].map(item => (
              <button key={item.id} onClick={()=>{ setPage(item.id); setNavOpen(false); }}
                style={{ width:"100%", display:"flex", alignItems:"center", gap:12, padding:"14px 1.5rem", background:page===item.id?T.greenLight:"transparent", color:page===item.id?T.green:T.ink, border:"none", borderLeft:`3px solid ${page===item.id?T.green:"transparent"}`, fontSize:14, fontWeight:page===item.id?700:400, cursor:"pointer", fontFamily:"'Lato',sans-serif", textAlign:"left", transition:"all 0.15s" }}>
                <span style={{ fontSize:18 }}>{item.icon}</span>{item.label}
              </button>
            ))}
          </nav>
          {user && (
            <div style={{ padding:"1rem 1.5rem", borderTop:`1px solid ${T.border}` }}>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
                {user.photoURL && <img src={user.photoURL} alt="" referrerPolicy="no-referrer" style={{ width:32, height:32, borderRadius:"50%" }}/>}
                <span style={{ fontSize:12, color:T.inkSec, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{user.displayName??user.email}</span>
              </div>
              <button onClick={handleSignOut} style={{ width:"100%", padding:"8px", borderRadius:4, border:`1px solid ${T.border}`, background:"transparent", color:T.inkSec, fontSize:12, fontWeight:700, cursor:"pointer", fontFamily:"'Lato',sans-serif" }}>Sign Out</button>
            </div>
          )}
        </div>
      )}

      {/* Header */}
      <header style={{ background:T.ink, color:"#FFF", padding:"1rem 2rem", display:"flex", alignItems:"center", justifyContent:"space-between", position:"sticky", top:0, zIndex:100 }}>
        <div style={{ display:"flex", alignItems:"center", gap:14 }}>
          <button onClick={()=>setNavOpen(o=>!o)} style={{ background:"transparent", border:"none", color:"#FFF", fontSize:22, cursor:"pointer", padding:"4px 6px", borderRadius:4, lineHeight:1, opacity:0.85 }} title="Menu">☰</button>
          <span style={{ fontSize:24 }}>🛒</span>
          <div>
            <div style={{ fontFamily:"'Playfair Display',serif", fontSize:20, letterSpacing:"-0.01em" }}>SmartCart <em style={{ fontWeight:400, color:T.greenMid }}>AI</em></div>
            <div style={{ fontSize:10, letterSpacing:"0.12em", opacity:0.5, textTransform:"uppercase" }}>Grocery Intelligence</div>
          </div>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          {loc.city && page==="home" && <div style={{ fontSize:12, opacity:0.7 }}>📍 {loc.city}, {loc.region}</div>}
          {user && (
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              {user.photoURL && <img src={user.photoURL} alt="" referrerPolicy="no-referrer" style={{ width:28, height:28, borderRadius:"50%", border:"2px solid rgba(255,255,255,0.3)" }}/>}
              <span style={{ fontSize:12, opacity:0.8, maxWidth:140, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{user.displayName??user.email}</span>
            </div>
          )}
          {page==="home" && (
            <button onClick={()=>setChatOpen(o=>!o)} style={{ ...headerBtnStyle, background:chatOpen?T.greenMid:"rgba(255,255,255,0.1)", border:`1px solid ${chatOpen?T.greenMid:"rgba(255,255,255,0.2)"}` }}>
              <span style={{ fontSize:16 }}>🤖</span> AI Agent
            </button>
          )}
        </div>
      </header>

      {/* Page routing */}
      {page === "pantry"  && <PantryPage  getToken={getToken} />}
      {page === "recipes" && <RecipePage  getToken={getToken} />}
      {page === "receipt" && <ReceiptPage getToken={getToken} />}
      {page === "feedback" && <FeedbackPage getToken={getToken} />}

      {/* Home page */}
      {page === "home" && (
        <div style={{ marginRight:chatOpen?380:0, transition:"margin-right 0.25s ease", maxWidth:chatOpen?"none":1080, margin:chatOpen?"0":"0 auto", padding:"2rem 1.5rem" }}>
          <div style={{ maxWidth:chatOpen?800:"none", margin:"0 auto" }}>

            <Card className="fu" style={{ marginBottom:"2rem" }}>
              <SectionHead label="Plan Your Groceries" sub="AI builds your optimized shopping plan" />
              <div style={{ display:"flex", gap:8, marginBottom:"1.5rem", flexWrap:"wrap" }}>
                <ModeBtn active={mode==="meal"}   onClick={()=>setMode("meal")}>🍽️ Single Meal</ModeBtn>
                <ModeBtn active={mode==="weekly"} onClick={()=>setMode("weekly")}>📅 Weekly Plan</ModeBtn>
                <ModeBtn active={mode==="list"}   onClick={()=>setMode("list")}>🛍️ Shopping List</ModeBtn>
                <ModeBtn active={mode==="both"}   onClick={()=>setMode("both")}>🍽️ + 🛍️ Both</ModeBtn>
              </div>
              {mode==="meal" && <div style={{ marginBottom:"1.25rem" }}><Input label="Enter one meal" value={dish} onChange={e=>setDish(e.target.value)} placeholder="e.g. Tomato Veg Pasta"/></div>}
              {mode==="weekly" && (
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))", gap:10, marginBottom:"1.25rem" }}>
                  {DAYS.map(day=><Input key={day} label={day} value={weeklyMeals[day]??""} onChange={e=>setWeeklyMeals(p=>({...p,[day]:e.target.value}))} placeholder="Enter meal..."/>)}
                </div>
              )}
              {mode==="both" && (
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"1rem", marginBottom:"1.25rem" }}>
                  <Input label="Enter meal" value={dish} onChange={e=>setDish(e.target.value)} placeholder="e.g. Lentil Curry"/>
                  <Textarea label="Extra items (comma separated)" value={manualText} onChange={e=>setManualText(e.target.value)} placeholder="bread, yogurt, juice..." rows={2}/>
                </div>
              )}
              {mode==="list" && <div style={{ marginBottom:"1.25rem" }}><Textarea label="Shopping items (comma separated)" value={manualText} onChange={e=>setManualText(e.target.value)} placeholder="tomatoes, olive oil, pasta..." rows={3}/></div>}
              <div style={{ height:1, background:T.border, margin:"1.25rem 0" }}/>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"1rem", marginBottom:"1.25rem" }}>
                <Textarea label="Pantry items — already at home (comma separated)" value={pantryText} onChange={e=>setPantryText(e.target.value)} placeholder="salt, oil, garlic..." rows={2}/>
                <Select label="Dietary Preference" value={dietary} onChange={e=>setDietary(e.target.value)} options={DIETS}/>
              </div>
              <button onClick={handleGenerate} disabled={loading} style={{ width:"100%", padding:"14px", background:loading?T.borderDark:T.ink, color:"#FFF", border:"none", borderRadius:4, fontSize:14, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:loading?"not-allowed":"pointer", fontFamily:"'Lato',sans-serif", transition:"background 0.15s", opacity:loading?0.7:1 }}>
                {loading?"Generating Plan…":"✦ Generate Smart Plan"}
              </button>
              {error && <div style={{ marginTop:"1rem", padding:"12px 16px", borderRadius:6, background:T.redLight, border:"1px solid #f5c6c3", color:T.red, fontSize:13 }}>⚠ {error}</div>}
            </Card>

            {loading && (
              <Card style={{ textAlign:"center", padding:"3rem" }}>
                <div style={{ width:40, height:40, margin:"0 auto 1rem", border:`3px solid ${T.border}`, borderTop:`3px solid ${T.green}`, borderRadius:"50%", animation:"spin 0.8s linear infinite" }}/>
                <p style={{ color:T.inkSec, fontFamily:"'Playfair Display',serif", fontStyle:"italic" }}>Building your grocery plan…</p>
              </Card>
            )}

            {data && !loading && (
              <div ref={resultsRef}>
                <div style={{ display:"flex", gap:4, marginBottom:"1.25rem", overflowX:"auto", paddingBottom:2 }}>
                  {TABS.map(t=><TabBtn key={t.id} active={activeTab===t.id} onClick={()=>setActiveTab(t.id)}>{t.label}</TabBtn>)}
                </div>

                {activeTab==="list" && (
                  <Card className="fu1">
                    <SectionHead label="Compiled Shopping List" sub={`${list.length} items`} delay="1"/>
                    {!list.length ? <p style={{ color:T.inkSec }}>No items generated.</p> : (
                      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:8 }}>
                        {list.map((item,i)=>(
                          <div key={i} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 14px", borderRadius:6, background:T.surfaceAlt, border:`1px solid ${T.border}` }}>
                            <span style={{ color:T.green, fontWeight:700 }}>✓</span>
                            <span style={{ fontSize:13, textTransform:"capitalize" }}>{item}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                )}

                {activeTab==="stores" && (
                  <div className="fu1">
                    {!stores.length ? <Card><p style={{ color:T.inkSec }}>No stores found.</p></Card> : pm && (
                      <>
                        {(()=>{
                          const sortedStores=[...stores].sort((a,b)=>(pm.totals[a.store_name]||Infinity)-(pm.totals[b.store_name]||Infinity));
                          const cheapestTotal=pm.totals[sortedStores[0]?.store_name]||0;
                          return (
                            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:12, marginBottom:"1.25rem" }}>
                              {sortedStores.map((store,i)=>{
                                const name=store.store_name, total=pm.totals[name]||0, isCheapest=i===0;
                                const currency=pm.currencies[name]||"USD";
                                const itemsWon=pm.wCounts[name]||0, rank=i===0?"🥇 Cheapest Basket":i===1?"🥈 Runner Up":"🥉 Option 3";
                                const savings=total-cheapestTotal;
                                return (
                                  <Card key={name} style={{ borderColor:isCheapest?T.green:T.border }}>
                                    <span style={{ display:"inline-block", marginBottom:8, fontSize:11, fontWeight:700, letterSpacing:"0.06em", textTransform:"uppercase", padding:"2px 8px", borderRadius:3, background:isCheapest?T.greenLight:T.surfaceAlt, color:isCheapest?T.green:T.inkSec }}>{rank}</span>
                                    <div style={{ fontFamily:"'Playfair Display',serif", fontSize:16, marginBottom:4 }}>{name}</div>
                                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:22, fontWeight:500, color:isCheapest?T.green:T.ink, marginBottom:2 }}>{formatPrice(total,currency)}</div>
                                    {!isCheapest&&savings>0&&<div style={{ fontSize:12, color:T.red, marginBottom:4 }}>+{formatPrice(savings,currency)} vs cheapest</div>}
                                    <span style={{ fontSize:12, color:T.inkSec }}>{itemsWon>0?`${itemsWon} cheapest items`:"No cheapest items"}</span>
                                  </Card>
                                );
                              })}
                            </div>
                          );
                        })()}
                        {(()=>{
                          const minStoreTotal=Math.min(...stores.map(s=>pm.totals[s.store_name]||Infinity));
                          const savings=minStoreTotal-pm.overallCheapest;
                          const currency=Object.values(pm.currencies)[0]||"USD";
                          return (
                            <div style={{ background:T.greenLight, border:`1px solid ${T.green}33`, borderRadius:8, padding:"1rem 1.25rem", marginBottom:"1.25rem", display:"flex", alignItems:"center", gap:12 }}>
                              <span style={{ fontSize:22 }}>🏆</span>
                              <div>
                                <div style={{ fontSize:11, fontWeight:700, color:T.green, letterSpacing:"0.06em", textTransform:"uppercase" }}>Cheapest Possible Basket (Multi-Store)</div>
                                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:24, fontWeight:500, color:T.green }}>{formatPrice(pm.overallCheapest,currency)}</div>
                                <div style={{ fontSize:12, color:T.green }}>{savings>0.01?`Saves ${formatPrice(savings,currency)} vs single store`:"Best value across stores"}</div>
                              </div>
                            </div>
                          );
                        })()}
                        <Card>
                          <SectionHead label="Price Comparison Table" sub="Green = cheapest for that item" delay="1"/>
                          <div style={{ overflowX:"auto" }}>
                            <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                              <thead>
                                <tr>
                                  <th style={{ textAlign:"left", padding:"8px 12px", borderBottom:`2px solid ${T.border}`, fontSize:11, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", color:T.inkSec }}>Item</th>
                                  {stores.map(s=><th key={s.store_name} style={{ textAlign:"right", padding:"8px 12px", borderBottom:`2px solid ${T.border}`, fontSize:11, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", color:T.inkSec, whiteSpace:"nowrap" }}>{s.store_name}</th>)}
                                </tr>
                              </thead>
                              <tbody>
                                {pm.items.map((item,ri)=>{
                                  const rowPrices=stores.map(s=>pm.matrix[s.store_name]?.[item]);
                                  const minP=Math.min(...rowPrices.filter(p=>p!==undefined));
                                  return (
                                    <tr key={item} style={{ background:ri%2===0?T.surfaceAlt:T.surface }}>
                                      <td style={{ padding:"8px 12px", textTransform:"capitalize", fontWeight:500 }}>{item}</td>
                                      {stores.map(s=>{ const p=pm.matrix[s.store_name]?.[item], isMin=p===minP, curr=pm.currencies[s.store_name]||"USD"; return <td key={s.store_name} style={{ padding:"8px 12px", textAlign:"right", fontFamily:"'DM Mono',monospace", background:isMin?T.greenLight:p===undefined?"#fff5f5":"transparent", color:isMin?T.green:p===undefined?T.red:T.ink, fontWeight:isMin?700:400 }}>{p!==undefined?formatPrice(p,curr):<span title="Not available">N/A</span>}</td>; })}
                                    </tr>
                                  );
                                })}
                                <tr style={{ borderTop:`2px solid ${T.border}` }}>
                                  <td style={{ padding:"10px 12px", fontWeight:700, fontFamily:"'Playfair Display',serif" }}>🛒 Total Basket</td>
                                  {(()=>{ const minTotal=Math.min(...stores.map(st=>pm.totals[st.store_name]||Infinity)); return stores.map(s=>{ const total=pm.totals[s.store_name]||0, isMin=Math.abs(total-minTotal)<0.001, curr=pm.currencies[s.store_name]||"USD"; return <td key={s.store_name} style={{ padding:"10px 12px", textAlign:"right", fontFamily:"'DM Mono',monospace", fontWeight:700, background:isMin?T.greenLight:"transparent", color:isMin?T.green:T.ink }}>{formatPrice(total,curr)}{isMin&&<span style={{ fontSize:10, marginLeft:4 }}>✓ CHEAPEST</span>}</td>; }); })()}
                                </tr>
                              </tbody>
                            </table>
                            <p style={{ fontSize:11, color:T.inkSec, marginTop:8, fontStyle:"italic" }}>* <span style={{ color:T.red }}>N/A</span> = item not carried at this store.</p>
                          </div>
                        </Card>
                      </>
                    )}
                  </div>
                )}

                {activeTab==="route" && (
                  <Card className="fu1">
                    <SectionHead label="Optimized Shopping Route" sub="Nearest-neighbor route optimization" delay="1"/>
                    {!route.length ? <p style={{ color:T.inkSec }}>No route available.</p> : (
                      <>
                        <div style={{ marginBottom:"1.5rem" }}>
                          {[{stop:0,store_name:`📍 ${loc.city||"Your Location"}`,isStart:true},...route].map((stop,i)=>(
                            <div key={i} style={{ display:"flex", gap:16, alignItems:"flex-start" }}>
                              <div style={{ display:"flex", flexDirection:"column", alignItems:"center" }}>
                                <div style={{ width:32, height:32, borderRadius:"50%", background:stop.isStart?T.greenLight:T.surfaceAlt, border:`2px solid ${stop.isStart?T.green:T.border}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, fontFamily:"'DM Mono',monospace", color:stop.isStart?T.green:T.inkSec, flexShrink:0 }}>{stop.isStart?"★":stop.stop}</div>
                                {i<route.length&&<div style={{ width:2, height:28, background:T.border }}/>}
                              </div>
                              <div style={{ paddingBottom:12, paddingTop:5 }}>
                                <div style={{ fontSize:15, fontWeight:600, fontFamily:"'Playfair Display',serif", color:stop.isStart?T.green:T.ink }}>{stop.store_name}</div>
                                {!stop.isStart&&<div style={{ fontSize:12, color:T.inkSec, marginTop:2 }}>{stop.distance_km} km away</div>}
                              </div>
                            </div>
                          ))}
                        </div>
                        {loc.lat&&route.length>0&&(
                          <a href={`https://www.google.com/maps/dir/${loc.lat},${loc.lng}/${route.map(s=>`${s.lat},${s.lng}`).join("/")}`} target="_blank" rel="noopener noreferrer" style={{ display:"inline-block", padding:"10px 20px", background:T.ink, color:"#FFF", borderRadius:4, fontSize:12, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", textDecoration:"none", fontFamily:"'Lato',sans-serif" }}>
                            Open in Google Maps ↗
                          </a>
                        )}
                      </>
                    )}
                  </Card>
                )}

                {activeTab==="nutrition" && (
                  <div className="fu1" style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"1.25rem" }}>
                    <Card>
                      <SectionHead label="Nutrition Report" delay="1"/>
                      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:8, marginBottom:"1.25rem" }}>
                        {[
                          {label:"Calories",value:scores.calories??0,unit:"kcal",color:T.amber},
                          {label:"Protein",value:scores.protein_g??0,unit:"g",color:T.green},
                          {label:"Carbs",value:scores.carbs_g??0,unit:"g",color:T.blue},
                          {label:"Fat",value:scores.fat_g??0,unit:"g",color:T.red},
                          {label:"Fiber",value:scores.fiber_g??0,unit:"g",color:T.greenMid},
                        ].map(m=>(
                          <div key={m.label} style={{ padding:"10px 8px", background:T.surfaceAlt, borderRadius:6, textAlign:"center", border:`1px solid ${T.border}` }}>
                            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:18, fontWeight:500, color:m.color }}>{m.value}</div>
                            <div style={{ fontSize:10, color:T.inkSec, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase" }}>{m.unit}</div>
                            <div style={{ fontSize:11, color:T.inkSec, marginTop:2 }}>{m.label}</div>
                          </div>
                        ))}
                      </div>
                      <ScoreBar label="Protein Score"   value={scores.protein_score??0}   color={T.green}/>
                      <ScoreBar label="Vegetable Score" value={scores.vegetable_score??0} color={T.greenMid}/>
                      <ScoreBar label="Carb Score"      value={scores.carb_score??0}      color={T.amber}/>
                      <ScoreBar label="Fat Score"       value={scores.fat_score??0}       color={T.blue}/>
                      <div style={{ marginTop:"1rem", padding:"12px 16px", background:T.surfaceAlt, borderRadius:6, textAlign:"center" }}>
                        <div style={{ fontSize:11, fontWeight:700, color:T.inkSec, letterSpacing:"0.06em", textTransform:"uppercase", marginBottom:4 }}>Health Rating</div>
                        <div style={{ fontFamily:"'Playfair Display',serif", fontSize:20, color:T.green }}>{scores.health_rating||"—"}</div>
                      </div>
                    </Card>
                    <Card>
                      <SectionHead label="AI Feedback" delay="2"/>
                      {feedback.summary&&<p style={{ fontSize:13, color:T.inkSec, lineHeight:1.7, marginBottom:"1rem" }}>{feedback.summary}</p>}
                      {feedback.strengths?.length>0&&(
                        <div style={{ marginBottom:"1rem" }}>
                          <div style={{ fontSize:11, fontWeight:700, color:T.green, letterSpacing:"0.06em", textTransform:"uppercase", marginBottom:6 }}>Strengths</div>
                          {feedback.strengths.map((s,i)=><div key={i} style={{ fontSize:13, padding:"5px 0", borderBottom:`1px solid ${T.border}`, display:"flex", gap:8 }}><span style={{ color:T.green }}>+</span>{s}</div>)}
                        </div>
                      )}
                      {feedback.weaknesses?.length>0&&(
                        <div style={{ marginBottom:"1rem" }}>
                          <div style={{ fontSize:11, fontWeight:700, color:T.red, letterSpacing:"0.06em", textTransform:"uppercase", marginBottom:6 }}>Weaknesses</div>
                          {feedback.weaknesses.map((w,i)=><div key={i} style={{ fontSize:13, padding:"5px 0", borderBottom:`1px solid ${T.border}`, display:"flex", gap:8 }}><span style={{ color:T.red }}>−</span>{w}</div>)}
                        </div>
                      )}
                      {feedback.recommendations?.length>0&&(
                        <div>
                          <div style={{ fontSize:11, fontWeight:700, color:T.blue, letterSpacing:"0.06em", textTransform:"uppercase", marginBottom:6 }}>Recommendations</div>
                          {feedback.recommendations.map((r,i)=><div key={i} style={{ fontSize:13, padding:"5px 0", borderBottom:`1px solid ${T.border}`, display:"flex", gap:8 }}><span style={{ color:T.blue }}>→</span>{r}</div>)}
                        </div>
                      )}
                    </Card>
                  </div>
                )}

                {activeTab==="subs" && (
                  <Card className="fu1">
                    <SectionHead label="Smart Substitutions" sub="Choose your preferred alternative, then regenerate" delay="1"/>
                    {!Object.keys(subs).length ? <p style={{ color:T.inkSec }}>No substitutions generated.</p> : (
                      <>
                        <div style={{ display:"flex", flexDirection:"column", gap:16, marginBottom:"1.5rem" }}>
                          {Object.entries(subs).map(([item,options])=>(
                            <div key={item} style={{ padding:"1rem 1.25rem", borderRadius:6, background:T.surfaceAlt, border:`1px solid ${T.border}` }}>
                              <div style={{ fontFamily:"'Playfair Display',serif", fontWeight:600, textTransform:"capitalize", marginBottom:10 }}>{item}</div>
                              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                                {["Keep original",...(Array.isArray(options)?options:[])].map(opt=>(
                                  <button key={opt} onClick={()=>setSelectedSubs(p=>({...p,[item]:opt}))}
                                    style={{ fontSize:12, padding:"5px 12px", borderRadius:20, border:`1px solid ${selectedSubs[item]===opt||(!selectedSubs[item]&&opt==="Keep original")?T.green:T.border}`, background:selectedSubs[item]===opt||(!selectedSubs[item]&&opt==="Keep original")?T.greenLight:"transparent", color:selectedSubs[item]===opt||(!selectedSubs[item]&&opt==="Keep original")?T.green:T.inkSec, cursor:"pointer", fontFamily:"'Lato',sans-serif", fontWeight:700, textTransform:"capitalize", transition:"all 0.15s" }}>
                                    {opt==="Keep original"?"✓ Keep original":`↳ ${opt}`}
                                  </button>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                        <div style={{ borderTop:`1px solid ${T.border}`, paddingTop:"1.25rem" }}>
                          {activeSubCount>0&&<div style={{ marginBottom:10, fontSize:13, color:T.green, fontWeight:600 }}>✓ {activeSubCount} substitution{activeSubCount>1?"s":""} selected</div>}
                          <button onClick={handleRegenerate} disabled={regenLoading} style={{ padding:"12px 28px", background:activeSubCount>0?T.green:T.borderDark, color:"#FFF", border:"none", borderRadius:4, fontSize:13, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", cursor:activeSubCount>0?"pointer":"not-allowed", fontFamily:"'Lato',sans-serif", transition:"background 0.15s", opacity:regenLoading?0.7:1 }}>
                            {regenLoading?"Regenerating…":"↺ Regenerate Plan with Substitutions"}
                          </button>
                          <p style={{ fontSize:12, color:T.inkSec, marginTop:8 }}>{activeSubCount===0?"Select at least one substitution above to regenerate":"This will rebuild your shopping list with the new items"}</p>
                          {regenMsg&&<div style={{ marginTop:10, padding:"10px 14px", borderRadius:6, fontSize:13, fontWeight:500, background:regenMsg.startsWith("✓")?T.greenLight:T.redLight, color:regenMsg.startsWith("✓")?T.green:T.red, border:`1px solid ${regenMsg.startsWith("✓")?T.green+"33":T.red+"33"}` }}>{regenMsg}</div>}
                        </div>
                      </>
                    )}
                  </Card>
                )}

                {activeTab==="budget" && (
                  <Card className="fu1">
                    <SectionHead label="Budget Optimization" delay="1"/>
                    {(pmExpensiveStore||pmCheapestStore)&&(
                      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:"1.25rem", padding:"10px 14px", background:T.surfaceAlt, borderRadius:6, border:`1px solid ${T.border}`, fontSize:12 }}>
                        <div><span style={{ color:T.inkSec }}>Most expensive: </span><span style={{ fontWeight:700, color:T.red }}>{pmExpensiveStore||"—"}</span></div>
                        <div><span style={{ color:T.inkSec }}>Cheapest: </span><span style={{ fontWeight:700, color:T.green }}>{pmCheapestStore||"—"}</span></div>
                      </div>
                    )}
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:"1.25rem" }}>
                      {[
                        {label:"Without Optimization",sublabel:pmExpensiveStore?`Single store: ${pmExpensiveStore}`:"Most expensive store",value:formatPrice(parseFloat(pmOriginalCost),pmCurrency),color:T.red},
                        {label:"With Optimization",sublabel:"Multi-store cheapest basket",value:formatPrice(parseFloat(pmOptimizedCost),pmCurrency),color:T.green},
                        {label:"You Save",sublabel:"vs worst single store",value:formatPrice(parseFloat(pmMoneySaved),pmCurrency),color:T.blue},
                      ].map((m,i)=>(
                        <div key={i} style={{ padding:"1.25rem", borderRadius:6, textAlign:"center", background:T.surfaceAlt, border:`1px solid ${T.border}` }}>
                          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:26, fontWeight:500, color:m.color }}>{m.value}</div>
                          <div style={{ fontSize:11, color:T.ink, fontWeight:700, letterSpacing:"0.04em", textTransform:"uppercase", marginTop:4 }}>{m.label}</div>
                          <div style={{ fontSize:11, color:T.inkSec, marginTop:2 }}>{m.sublabel}</div>
                        </div>
                      ))}
                    </div>
                    {budgetOpt.substitutions?.length>0&&(
                      <div>
                        <div style={{ fontSize:11, fontWeight:700, color:T.inkSec, letterSpacing:"0.06em", textTransform:"uppercase", marginBottom:10 }}>Budget Swaps Applied</div>
                        {budgetOpt.substitutions.map((s,i)=>(
                          <div key={i} style={{ display:"flex", alignItems:"center", gap:10, padding:"8px 0", borderBottom:`1px solid ${T.border}`, fontSize:13 }}>
                            <span style={{ color:T.red, flex:1, textTransform:"capitalize" }}>{s.original}</span>
                            <span style={{ color:T.inkTer }}>→</span>
                            <span style={{ color:T.green, flex:1, textTransform:"capitalize" }}>{s.replacement}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating chat button */}
      {page==="home" && !chatOpen && (
        <button onClick={()=>setChatOpen(true)} style={{ position:"fixed", bottom:28, right:28, zIndex:999, width:60, height:60, borderRadius:"50%", background:T.green, border:"none", color:"#FFF", fontSize:24, cursor:"pointer", boxShadow:"0 4px 20px rgba(45,106,79,0.4)", display:"flex", alignItems:"center", justifyContent:"center", transition:"transform 0.15s, box-shadow 0.15s" }}
          onMouseEnter={e=>{e.currentTarget.style.transform="scale(1.1)";e.currentTarget.style.boxShadow="0 6px 28px rgba(45,106,79,0.5)";}}
          onMouseLeave={e=>{e.currentTarget.style.transform="scale(1)";e.currentTarget.style.boxShadow="0 4px 20px rgba(45,106,79,0.4)";}}>
          🤖
        </button>
      )}

      {page==="home" && chatOpen && <ChatPanel onClose={()=>setChatOpen(false)} user={user} getToken={getToken}/>}

      {showLocationModal && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000
        }}>
          <div style={{
            background: T.surface, borderRadius: 8, padding: "2rem",
            maxWidth: 400, width: "90%", boxShadow: "0 8px 32px rgba(0,0,0,0.2)"
          }}>
            <h3 style={{ margin: "0 0 8px", fontSize: 18, fontFamily: "'Lato',sans-serif" }}>
              📍 Where are you shopping from?
            </h3>
            <p style={{ margin: "0 0 20px", fontSize: 13, color: T.subtext }}>
              We couldn't detect your location automatically. Enter your city, state,
              and ZIP/postal code to find nearby stores and prices more accurately.
            </p>

              <Label>City</Label>
              <input
                type="text"
                value={manualCity}
                onChange={e => setManualCity(e.target.value)}
                placeholder="e.g. Austin or Hyderabad"
                style={{ width: "100%", background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 4, padding: "10px 12px", fontSize: 14, marginBottom: 12, boxSizing: "border-box", fontFamily: "'Lato',sans-serif" }}
              />
    
              <Label>ZIP / Postal / PIN Code (recommended for accuracy)</Label>
              <input
                type="text"
                value={manualPostalCode}
                onChange={e => setManualPostalCode(e.target.value)}
                placeholder="e.g. 78701 or 500001"
                style={{ width: "100%", background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 4, padding: "10px 12px", fontSize: 14, marginBottom: 12, boxSizing: "border-box", fontFamily: "'Lato',sans-serif" }}
              />
              <p style={{ margin: "-8px 0 12px", fontSize: 12, color: T.subtext }}>
                Adding this helps us find stores much closer to you than city alone.
              </p>
    
              <Label>State / Province / Region</Label>
              <input
                type="text"
                value={manualState}
                onChange={e => setManualState(e.target.value)}
                placeholder="e.g. Texas or Telangana"
                style={{ width: "100%", background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 4, padding: "10px 12px", fontSize: 14, marginBottom: 20, boxSizing: "border-box", fontFamily: "'Lato',sans-serif" }}
              />

            <button
              onClick={submitManualLocation}
              disabled={!(manualCity.trim() && manualState.trim()) && !manualPostalCode.trim()}
              style={{
                width: "100%", padding: "12px", background: T.ink, color: "#FFF",
                border: "none", borderRadius: 4, fontSize: 14, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: "0.04em",
                cursor: (!(manualCity.trim() && manualState.trim()) && !manualPostalCode.trim()) ? "not-allowed" : "pointer",
                opacity: (!(manualCity.trim() && manualState.trim()) && !manualPostalCode.trim()) ? 0.5 : 1,
                fontFamily: "'Lato',sans-serif"
              }}
            >
              Continue
            </button>
          </div>
        </div>
      )}
    </>
  );
}
