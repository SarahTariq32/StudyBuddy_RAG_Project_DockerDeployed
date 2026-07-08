
// import { useEffect, useRef, useState } from 'react'
// import { askQuestion } from '../api/chat.js'
// import { getSessionId } from '../utils/session.js'
// import Message from './Message.jsx'
// import InputBox from './InputBox.jsx'

// function ChatWindow() {
//   const [messages, setMessages] = useState([])
//   const [loading, setLoading] = useState(false)
//   const bottomRef = useRef(null)

//   useEffect(() => {
//     bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
//   }, [messages])

//   async function handleSend(question) {
//     setMessages(prev => [...prev, { role: 'user', text: question }])
//     setLoading(true)

//     const data = await askQuestion(question, getSessionId())
//     const answer = data.answer ?? 'Something went wrong.'

//     setMessages(prev => [...prev, { role: 'assistant', text: answer }])
//     setLoading(false)
//   }

//   return (
//     <div style={{
//       flex: 1,
//       display: 'flex',
//       flexDirection: 'column',
//       height: '100vh',
//       overflow: 'hidden',
//       background: '#0f0f0f'
//     }}>
//       <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
//         {messages.length === 0 && (
//           <p style={{ color: '#444', textAlign: 'center', marginTop: '3rem' }}>
//             Upload a PDF and ask anything about it.
//           </p>
//         )}
//         {messages.map((msg, i) => (
//           <Message key={i} role={msg.role} text={msg.text} />
//         ))}
//         {loading && (
//           <div style={{ color: '#555', fontSize: '0.9rem', paddingLeft: '0.5rem' }}>
//             Thinking...
//           </div>
//         )}
//         <div ref={bottomRef} />
//       </div>
//       <InputBox onSend={handleSend} disabled={loading} />
//     </div>
//   )
// }

// export default ChatWindow

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { askQuestion } from '../api/chat.js'
import { getSessionId } from '../utils/session.js'
import Message from './Message.jsx'
import InputBox from './InputBox.jsx'

function getChatCacheKey(sessionId) {
  return `chat_messages_${sessionId}`
}

function readChatCache(sessionId) {
  try {
    const raw = sessionStorage.getItem(getChatCacheKey(sessionId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (_) {
    return []
  }
}

function writeChatCache(sessionId, messages) {
  try {
    sessionStorage.setItem(getChatCacheKey(sessionId), JSON.stringify(messages))
  } catch (_) {
    // Ignore storage errors.
  }
}

function ChatWindow({ topInset = 0 }) {
  const navigate = useNavigate()
  const sessionId = getSessionId()
  const [messages, setMessages] = useState(() => readChatCache(sessionId))
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    writeChatCache(sessionId, messages)
  }, [messages, sessionId])

  async function handleSend(question) {
    setMessages(prev => [...prev, { role: 'user', text: question }])
    setLoading(true)

    try {
      const data = await askQuestion(question, sessionId)
      const answer = data.answer ?? 'Something went wrong.'
      setMessages(prev => [...prev, { role: 'assistant', text: answer }])
    } catch (err) {
      console.error('Error asking question:', err)
      const errorMsg = err?.message || 'Failed to get a response from backend. Please check if your LLM provider keys are configured properly.'
      setMessages(prev => [...prev, { role: 'assistant', text: `⚠️ Error: ${errorMsg}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      height: '100dvh',
      overflow: 'hidden',
      background: 'transparent',
      position: 'relative',
      paddingTop: topInset ? `${topInset}px` : 0,
    }}>
      {/* Semi-transparent content background */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'rgba(0, 5, 20, 0.5)',
        backdropFilter: 'blur(2px)',
        zIndex: -1,
      }} />

      <button
        className="chat-ops-btn"
        onClick={() => navigate('/ops')}
        style={{
          position: 'absolute',
          top: topInset ? '0.7rem' : '1rem',
          right: '1rem',
          zIndex: 3,
          border: '1px solid rgba(0,180,255,0.34)',
          background: 'linear-gradient(135deg, rgba(0,70,155,0.66), rgba(0,150,255,0.36))',
          color: '#dff6ff',
          borderRadius: '10px',
          padding: '0.42rem 0.72rem',
          fontSize: '0.73rem',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'all 0.22s ease',
          boxShadow: '0 0 16px rgba(0,130,255,0.2)',
          backdropFilter: 'blur(5px)',
        }}
      >
        Operations Dashboard
      </button>

      {/* Messages container */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: topInset ? '1rem 0.85rem' : '1.5rem',
        zIndex: 1,
      }}>
        {messages.length === 0 && (
          <p style={{
            color: 'rgba(100,150,255,0.4)',
            textAlign: 'center',
            marginTop: topInset ? '1.5rem' : '3rem',
            fontSize: '0.95rem',
            letterSpacing: '0.05em',
          }}>
            Upload a PDF and ask anything about it.
          </p>
        )}
        {messages.map((msg, i) => (
          <Message key={i} role={msg.role} text={msg.text} />
        ))}
        {loading && (
          <div style={{
            color: 'rgba(0,180,255,0.6)',
            fontSize: '0.9rem',
            paddingLeft: '0.5rem',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}>
            Thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <InputBox onSend={handleSend} disabled={loading} compact={Boolean(topInset)} />

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }

        .chat-ops-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 0 22px rgba(0,180,255,0.34);
          border-color: rgba(0,210,255,0.58);
          background: linear-gradient(135deg, rgba(0,95,185,0.74), rgba(0,170,255,0.42));
        }

        .chat-ops-btn:active {
          transform: translateY(0);
        }
      `}</style>
    </div>
  )
}

export default ChatWindow