import React, { useMemo, useState } from 'react'

type Requirement = {
  id: string
  title: string
  description: string
  min_area_sqm?: number | null
  max_area_sqm?: number | null
  min_seats?: number | null
  max_seats?: number | null
  requires_gas?: boolean | null
  serves_meat?: boolean | null
  offers_delivery?: boolean | null
  category?: string | null
}

type BusinessInput = {
  area_sqm: number
  seats: number
  uses_gas: boolean
  serves_meat: boolean
  offers_delivery: boolean
}

type SectionNode = {
  id: string
  level: number
  title: string
  text: string
  context?: string | null
  group_level?: string | null
  min_area_sqm?: number | null
  max_area_sqm?: number | null
  min_seats?: number | null
  max_seats?: number | null
  requires_gas?: boolean | null
  serves_meat?: boolean | null
  offers_delivery?: boolean | null
  children: SectionNode[]
}

const API_URL = (import.meta as any).env.VITE_API_URL || 'http://127.0.0.1:8000'

export const App: React.FC = () => {
  const [form, setForm] = useState<BusinessInput>({
    area_sqm: 80,
    seats: 40,
    uses_gas: false,
    serves_meat: true,
    offers_delivery: true,
  })
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [matched, setMatched] = useState<Requirement[]>([])
  const [report, setReport] = useState<string>('')
  const [tree, setTree] = useState<SectionNode[]>([])
  const [matchedTree, setMatchedTree] = useState<SectionNode[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, type } = e.target
    const value = type === 'checkbox' ? (e.target as HTMLInputElement).checked : e.target.value
    setForm(prev => ({ ...prev, [name]: type === 'number' ? Number(value) : value }))
  }

  const fetchRequirements = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/requirements`)
      const data = await res.json()
      setRequirements(data)
    } catch (e: any) {
      setError(e?.message || 'שגיאה בטעינת דרישות')
    } finally { setLoading(false) }
  }

  const runMatch = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/match`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      const data = await res.json()
      setMatched(data.matched)
    } catch (e: any) {
      setError(e?.message || 'שגיאה בהתאמה')
    } finally { setLoading(false) }
  }

  const runReport = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/ai-report`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ business: form, matched, language: 'he' }) })
      const data = await res.json()
      setReport(data.report)
    } catch (e: any) {
      setError(e?.message || 'שגיאה ביצירת דוח')
    } finally { setLoading(false) }
  }

  const loadStructure = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/structure`)
      const data = await res.json()
      setTree(data.nodes || [])
    } catch (e: any) {
      setError(e?.message || 'שגיאה בטעינת מבנה')
    } finally { setLoading(false) }
  }

  const matchStructure = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/structure-match`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      const data = await res.json()
      setMatchedTree(data.nodes || [])
    } catch (e: any) {
      setError(e?.message || 'שגיאה בסינון מבנה')
    } finally { setLoading(false) }
  }

  const reportFromStructure = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API_URL}/ai-report-structure`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ business: form, nodes: matchedTree, language: 'he' }) })
      const data = await res.json()
      setReport(data.report)
    } catch (e: any) {
      setError(e?.message || 'שגיאה ביצירת דוח מסעיפים')
    } finally { setLoading(false) }
  }

  const NodeView: React.FC<{ node: SectionNode }> = ({ node }) => {
    const [open, setOpen] = useState<boolean>(true)
    const hasKids = node.children && node.children.length > 0
    return (
      <li>
        <div style={{ cursor: hasKids ? 'pointer' : 'default' }} onClick={() => hasKids && setOpen(!open)}>
          <b>[{node.id}] {node.title}</b> — {node.text}
        </div>
        {hasKids && open && (
          <ul>
            {node.children.map(c => <NodeView key={c.id} node={c} />)}
          </ul>
        )}
      </li>
    )
  }

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 900, margin: '2rem auto', lineHeight: 1.5 }}>
      <h1>מערכת הערכת רישוי עסקים</h1>
      <section style={{ display: 'grid', gap: 12, border: '1px solid #ccc', padding: 16, borderRadius: 8 }}>
        <h2>שאלון</h2>
        <label>שטח (מ"ר): <input type="number" name="area_sqm" value={form.area_sqm} onChange={onChange} /></label>
        <label>מקומות ישיבה: <input type="number" name="seats" value={form.seats} onChange={onChange} /></label>
        <label><input type="checkbox" name="uses_gas" checked={form.uses_gas} onChange={onChange} /> שימוש בגז</label>
        <label><input type="checkbox" name="serves_meat" checked={form.serves_meat} onChange={onChange} /> הגשת בשר</label>
        <label><input type="checkbox" name="offers_delivery" checked={form.offers_delivery} onChange={onChange} /> משלוחים</label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={matchStructure}>מצא דרישות</button>
          <button onClick={reportFromStructure}>דוח AI</button>
        </div>
        {loading && <div>טוען…</div>}
        {error && <div style={{ color: 'red' }}>{error}</div>}
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>דרישות רלוונטיות</h2>
        <ul>
          {matchedTree.map(n => <NodeView key={n.id} node={n} />)}
        </ul>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>דוח AI</h2>
        <pre style={{ whiteSpace: 'pre-wrap', background: '#f7f7f7', padding: 16, borderRadius: 8 }}>{report}</pre>
      </section>
    </div>
  )
}



