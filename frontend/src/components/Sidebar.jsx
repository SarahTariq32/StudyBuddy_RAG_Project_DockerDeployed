
import { useEffect, useState, useRef } from 'react'
import { listPDFs, uploadPDF } from '../api/documents.js'
import PDFList from './PDFList.jsx'
import UploadButton from './UploadButton.jsx'
import NotificationToast from './NotificationToast.jsx'

const MAX_PDFS = 5

function Sidebar() {
  const [docs, setDocs] = useState([])
  const [notification, setNotification] = useState('')
  const [notificationType, setNotificationType] = useState('error')
  const pollRef = useRef(null)

  async function refreshDocs() {
    const data = await listPDFs()
    setDocs(data)
    return data
  }

  function startPolling() {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      const data = await listPDFs()
      setDocs(data)
      const allReady = data.every(d => d.status === 'ready')
      if (allReady) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }, 3000)
  }

  useEffect(() => {
    refreshDocs().then(data => {
      const hasProcessing = data.some(d => d.status === 'processing')
      if (hasProcessing) startPolling()
    })
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // async function handleUpload(file) {
  //   const newDoc = await uploadPDF(file)
  //   if (newDoc && newDoc.id) {
  //     setDocs(prev => [...prev, newDoc])
  //     startPolling()
  //   }
  // }

    async function handleUpload(file) {
    try {
      const newDoc = await uploadPDF(file)
      if (newDoc && newDoc.id) {
        setDocs(prev => [...prev, newDoc])
        startPolling()
        setNotification(`✓ ${file.name} uploaded successfully`)
        setNotificationType('success')
      }
    } catch (err) {
      setNotification(err.message || 'Upload failed')
      setNotificationType('error')
    }
  }

  return (
    <div style={{
      width: '240px',
      height: '100vh',
      background: 'rgba(0, 5, 20, 0.6)',
      backdropFilter: 'blur(12px)',
      padding: '1.5rem 1rem',
      borderRight: '1px solid rgba(0,180,255,0.15)',
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem',
      overflow: 'hidden',
      position: 'relative',
    }}>

      {/* Top glow accent */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        height: '1px',
        background: 'linear-gradient(90deg, transparent, rgba(0,180,255,0.4), transparent)',
      }} />

      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid rgba(0,180,255,0.1)',
      }}>
        {/* Blinking status dot */}
        <div style={{
          width: '6px', height: '6px',
          borderRadius: '50%',
          background: '#00c8ff',
          boxShadow: '0 0 6px rgba(0,200,255,0.8)',
          animation: 'blink 2s ease-in-out infinite',
          flexShrink: 0,
        }} />
        <h2 style={{
          color: '#e0e8ff',
          fontSize: '0.85rem',
          margin: 0,
          fontWeight: '600',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
        }}>
          Your PDFs
        </h2>
        {/* PDF count badge */}
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.7rem',
          color: 'rgba(0,180,255,0.6)',
          background: 'rgba(0,180,255,0.08)',
          border: '1px solid rgba(0,180,255,0.2)',
          borderRadius: '10px',
          padding: '0.1rem 0.45rem',
          letterSpacing: '0.05em',
        }}>
          {docs.length}/{MAX_PDFS}
        </span>
      </div>

      <UploadButton onUpload={handleUpload} disabled={docs.length >= MAX_PDFS} />
      <PDFList docs={docs} onDocumentsChanged={refreshDocs} />

      {/* Notification Toast */}
      <NotificationToast
        message={notification}
        type={notificationType}
        onClose={() => setNotification('')}
      />

      {/* Bottom fade */}
      <div style={{
        position: 'absolute',
        bottom: 0, left: 0, right: 0,
        height: '60px',
        background: 'linear-gradient(to top, rgba(0,5,20,0.8), transparent)',
        pointerEvents: 'none',
      }} />

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  )
}

export default Sidebar