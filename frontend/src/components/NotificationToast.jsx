import { useEffect } from 'react'

function NotificationToast({ message, type = 'error', onClose, duration = 4000 }) {
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [message, duration, onClose])

  if (!message) return null

  const isError = type === 'error'
  const isSuccess = type === 'success'

  return (
    <div
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        zIndex: 10000,
        animation: 'slideIn 0.3s ease-out',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '14px 18px',
          background: isError
            ? 'linear-gradient(135deg, rgba(255,80,100,0.85) 0%, rgba(255,100,120,0.8) 100%)'
            : 'linear-gradient(135deg, rgba(0,220,160,0.85) 0%, rgba(0,200,140,0.8) 100%)',
          border: `1.5px solid ${
            isError
              ? 'rgba(255,150,170,0.8)'
              : 'rgba(0,240,180,0.8)'
          }`,
          borderRadius: '10px',
          boxShadow: isError
            ? '0 8px 32px rgba(255,100,120,0.4)'
            : '0 8px 32px rgba(0,220,160,0.4)',
          maxWidth: '420px',
          backdropFilter: 'blur(12px)',
        }}
      >
        {/* Icon */}
        <div
          style={{
            fontSize: '20px',
            flexShrink: 0,
            animation: isError ? 'pulse 1.5s ease-in-out infinite' : 'none',
          }}
        >
          {isError ? '⚠' : '✓'}
        </div>

        {/* Message */}
        <div
          style={{
            color: isError
              ? '#ffffff'
              : '#ffffff',
            fontSize: '0.9rem',
            fontWeight: '600',
            lineHeight: '1.4',
            wordBreak: 'break-word',
            textShadow: isError
              ? '0 1px 2px rgba(0,0,0,0.2)'
              : '0 1px 2px rgba(0,0,0,0.15)',
          }}
        >
          {message}
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'rgba(255,255,255,0.9)',
            cursor: 'pointer',
            fontSize: '18px',
            padding: '0 4px',
            flexShrink: 0,
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.target.style.color = 'rgba(255,255,255,1)'
            e.target.style.textShadow = '0 0 8px rgba(255,255,255,0.4)'
          }}
          onMouseLeave={(e) => {
            e.target.style.color = 'rgba(255,255,255,0.9)'
            e.target.style.textShadow = 'none'
          }}
          title="Close"
        >
          ✕
        </button>
      </div>

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(400px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>
    </div>
  )
}

export default NotificationToast
