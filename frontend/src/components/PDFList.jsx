// import PDFItem from './PDFItem.jsx'

// function PDFList({ docs, onDelete }) {
//   if (docs.length === 0) {
//     return <p style={{ color: '#555', fontSize: '0.85rem' }}>No PDFs uploaded yet.</p>
//   }

//   return (
//     <div>
//       {docs.map(doc => (
//         <PDFItem key={doc.id} doc={doc} onDelete={onDelete} />
//       ))}
//     </div>
//   )
// }

// export default PDFList


import PDFItem from './PDFItem.jsx'

function PDFList({ docs, isLoading, onDocumentsChanged }) {
  if (isLoading) {
    return null
  }

  if (docs.length === 0) {
    return (
      <p style={{
        color: 'rgba(100,150,255,0.35)',
        fontSize: '0.8rem',
        letterSpacing: '0.05em',
        textAlign: 'center',
        marginTop: '0.5rem',
        fontStyle: 'italic',
      }}>
        No PDFs uploaded yet.
      </p>
    )
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '0.25rem',
    }}>
      {docs.map(doc => (
        <PDFItem key={doc.id} doc={doc} onDocumentsChanged={onDocumentsChanged} />
      ))}
    </div>
  )
}

export default PDFList