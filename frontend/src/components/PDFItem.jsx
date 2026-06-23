// function PDFItem({ doc, onDelete }) {
//   const isProcessing = doc.status === 'processing'

//   return (
//     <div
//       title={doc.filename}
//       style={{
//         display: 'flex',
//         justifyContent: 'space-between',
//         alignItems: 'center',
//         padding: '0.5rem 0.75rem',
//         background: '#1e1e1e',
//         borderRadius: '6px',
//         marginBottom: '0.5rem',
//         fontSize: '0.85rem',
//         opacity: isProcessing ? 0.6 : 1
//       }}
//     >
//       <div style={{ overflow: 'hidden' }}>
//         <span style={{
//           color: '#ccc',
//           overflow: 'hidden',
//           textOverflow: 'ellipsis',
//           whiteSpace: 'nowrap',
//           display: 'block',
//           maxWidth: '140px'
//         }}>
//           {doc.filename}
//         </span>
//         {isProcessing && (
//           <span style={{ color: '#888', fontSize: '0.75rem' }}>indexing...</span>
//         )}
//       </div>
//       <button
//         onClick={() => !isProcessing && onDelete(doc.id)}
//         style={{
//           background: 'none',
//           border: 'none',
//           color: isProcessing ? '#555' : '#ff6b6b',
//           cursor: isProcessing ? 'not-allowed' : 'pointer',
//           fontSize: '1rem',
//           flexShrink: 0
//         }}
//       >
//         ✕
//       </button>
//     </div>
//   )
// }

// export default PDFItem



import { useEffect, useState } from 'react'
import { deletePDF, renamePDF } from '../api/documents.js'

function PDFItem({ doc, onDocumentsChanged }) {
  const isProcessing = doc.status === 'processing'
  const [isEditing, setIsEditing] = useState(false)
  const [draftName, setDraftName] = useState(doc.filename)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteProgress, setDeleteProgress] = useState(0)

  useEffect(() => {
    setDraftName(doc.filename)
  }, [doc.filename])

  async function handleDelete() {
    if (!isDeleting) {
      setIsDeleting(true)
      setDeleteProgress(0)
      
      // Animate progress bar
      const interval = setInterval(() => {
        setDeleteProgress(prev => Math.min(prev + Math.random() * 40, 90))
      }, 100)
      
      try {
        await deletePDF(doc.id)
        setDeleteProgress(100)
        clearInterval(interval)
        
        // Wait for animation to complete before refreshing
        setTimeout(() => {
          onDocumentsChanged()
        }, 400)
      } catch (err) {
        clearInterval(interval)
        setIsDeleting(false)
        setDeleteProgress(0)
      }
    }
  }

  async function handleRename() {
    const trimmedName = draftName.trim()
    if (!trimmedName || trimmedName === doc.filename) {
      setIsEditing(false)
      setDraftName(doc.filename)
      return
    }

    setIsSaving(true)
    try {
      await renamePDF(doc.id, trimmedName)
      setIsEditing(false)
      onDocumentsChanged()
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div
      title={doc.filename}
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 0.875rem',
        background: 'rgba(0, 20, 40, 0.4)',
        border: `1.5px solid rgba(0,180,255,${isProcessing ? '0.15' : '0.2'})`,
        borderRadius: '8px',
        marginBottom: '0.625rem',
        fontSize: '0.85rem',
        opacity: isProcessing ? 0.7 : 1,
        transition: 'all 0.3s ease',
        boxShadow: '0 0 10px rgba(0,150,255,0.05)',
      }}
      onMouseEnter={(e) => {
        if (!isProcessing) {
          e.currentTarget.style.background = 'rgba(0, 25, 50, 0.5)'
          e.currentTarget.style.boxShadow = '0 0 15px rgba(0,180,255,0.1)'
          e.currentTarget.style.borderColor = 'rgba(0,180,255,0.3)'
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(0, 20, 40, 0.4)'
        e.currentTarget.style.boxShadow = '0 0 10px rgba(0,150,255,0.05)'
        e.currentTarget.style.borderColor = `rgba(0,180,255,${isProcessing ? '0.15' : '0.2'})`
      }}
    >
      <div style={{ overflow: 'hidden', flex: 1 }}>
        {isEditing ? (
          <input
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRename()
              if (e.key === 'Escape') {
                setIsEditing(false)
                setDraftName(doc.filename)
              }
            }}
            disabled={isSaving}
            autoFocus
            style={{
              width: '100%',
              background: 'rgba(0, 20, 40, 0.7)',
              border: '1px solid rgba(0,180,255,0.35)',
              color: '#d9e8ff',
              borderRadius: '4px',
              padding: '0.2rem 0.35rem',
              fontSize: '0.78rem',
              outline: 'none',
            }}
          />
        ) : (
          <span style={{
            color: '#c0d0ff',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            display: 'block',
            maxWidth: '140px',
            fontWeight: '500',
          }}>
            {doc.filename}
          </span>
        )}
        {isProcessing && (
          <div style={{ marginTop: '0.2rem', maxWidth: '120px' }}>
            <div style={{
              color: 'rgba(0,180,255,0.65)',
              fontSize: '0.68rem',
              letterSpacing: '0.06em',
              marginBottom: '0.2rem',
            }}>
              INDEXING...
            </div>
            <div style={{
              width: '100%',
              height: '3px',
              background: 'rgba(0,140,220,0.22)',
              borderRadius: '999px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: '38%',
                height: '100%',
                borderRadius: '999px',
                background: 'linear-gradient(90deg, rgba(0,180,255,0), rgba(0,220,255,0.95), rgba(0,180,255,0))',
                animation: 'indexingSweep 1.2s linear infinite',
              }} />
            </div>
          </div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
        {isEditing ? (
          <>
            <button
              onClick={handleRename}
              disabled={isSaving}
              style={{
                background: 'none',
                border: 'none',
                color: 'rgba(0, 220, 160, 0.9)',
                cursor: isSaving ? 'wait' : 'pointer',
                fontSize: '0.9rem',
                flexShrink: 0,
                padding: '0.2rem 0.35rem',
              }}
              title='Save name'
            >
              ✓
            </button>
            <button
              onClick={() => {
                setIsEditing(false)
                setDraftName(doc.filename)
              }}
              disabled={isSaving}
              style={{
                background: 'none',
                border: 'none',
                color: 'rgba(255, 180, 100, 0.9)',
                cursor: isSaving ? 'wait' : 'pointer',
                fontSize: '0.9rem',
                flexShrink: 0,
                padding: '0.2rem 0.35rem',
              }}
              title='Cancel rename'
            >
              ↺
            </button>
          </>
        ) : (
          <button
            onClick={() => setIsEditing(true)}
            disabled={isProcessing}
            style={{
              background: 'none',
              border: 'none',
              color: isProcessing ? 'rgba(100,150,255,0.3)' : 'rgba(120, 220, 255, 0.8)',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              fontSize: '0.9rem',
              flexShrink: 0,
              padding: '0.2rem 0.35rem',
            }}
            title='Rename file'
          >
            ✎
          </button>
        )}

        {isDeleting ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.3rem',
            padding: '0.25rem 0.35rem',
            minWidth: '32px',
          }}>
            <div style={{
              width: '24px',
              height: '3px',
              background: 'rgba(255, 100, 120, 0.2)',
              borderRadius: '2px',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                background: 'linear-gradient(90deg, rgba(255, 100, 120, 0.8), rgba(255, 150, 170, 0.8))',
                width: `${deleteProgress}%`,
                transition: 'width 0.1s ease-out',
                borderRadius: '2px',
              }} />
            </div>
          </div>
        ) : (
          <button
            onClick={handleDelete}
            disabled={isDeleting || isSaving}
            style={{
              background: 'none',
              border: 'none',
              color: isDeleting ? 'rgba(100,150,255,0.3)' : 'rgba(255, 100, 120, 0.7)',
              cursor: isDeleting ? 'not-allowed' : 'pointer',
              fontSize: '1.1rem',
              flexShrink: 0,
              padding: '0.25rem 0.35rem',
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={(e) => {
              if (!isDeleting) {
                e.target.style.color = 'rgba(255, 80, 100, 1)'
                e.target.style.textShadow = '0 0 10px rgba(255, 100, 120, 0.4)'
              }
            }}
            onMouseLeave={(e) => {
              e.target.style.color = 'rgba(255, 100, 120, 0.7)'
              e.target.style.textShadow = 'none'
            }}
          >
            ✕
          </button>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
        @keyframes indexingSweep {
          0% { transform: translateX(-120%); }
          100% { transform: translateX(260%); }
        }
      `}</style>
    </div>
  )
}

export default PDFItem

