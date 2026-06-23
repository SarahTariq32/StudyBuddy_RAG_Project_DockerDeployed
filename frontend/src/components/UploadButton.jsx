
import { useState } from 'react'

function UploadButton({ onUpload, disabled }) {
  const [uploading, setUploading] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  // async function handleFileChange(e) {
  //   const file = e.target.files[0]
  //   if (!file) return
  //   setUploading(true)
  //   await onUpload(file)
  //   setUploading(false)
  //   e.target.value = ''
  // }
    async function handleFileChange(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      await onUpload(file)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  
  const isDisabled = disabled || uploading

  return (
    <label
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        padding: '0.75rem 1rem',
        background: isDisabled
          ? 'rgba(100,150,255,0.05)'
          : isHovered
            ? 'linear-gradient(135deg, rgba(0,180,255,0.25) 0%, rgba(0,200,255,0.15) 100%)'
            : 'linear-gradient(135deg, rgba(0,180,255,0.15) 0%, rgba(0,200,255,0.1) 100%)',
        color: isDisabled ? 'rgba(100,150,255,0.3)' : '#00c8ff',
        border: `1.5px solid ${isDisabled
          ? 'rgba(0,180,255,0.1)'
          : isHovered
            ? 'rgba(0,200,255,0.5)'
            : 'rgba(0,180,255,0.3)'}`,
        borderRadius: '8px',
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        textAlign: 'center',
        fontSize: '0.85rem',
        fontWeight: '600',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        transition: 'all 0.3s ease',
        boxShadow: isDisabled
          ? 'none'
          : isHovered
            ? '0 0 20px rgba(0,180,255,0.2)'
            : '0 0 10px rgba(0,180,255,0.1)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Shimmer effect on hover */}
      {!isDisabled && isHovered && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(90deg, transparent, rgba(0,200,255,0.08), transparent)',
          animation: 'shimmer 1.5s ease-in-out infinite',
          pointerEvents: 'none',
        }} />
      )}

      {/* Icon */}
      <span style={{ fontSize: '1rem', lineHeight: 1 }}>
        {uploading ? '⟳' : disabled ? '✕' : '+'}
      </span>

      {/* Label */}
      <span>
        {uploading ? 'Uploading...' : disabled ? 'Limit Reached' : 'Upload PDF'}
      </span>

      <input
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        disabled={isDisabled}
        style={{ display: 'none' }}
      />

      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </label>
  )
}

export default UploadButton