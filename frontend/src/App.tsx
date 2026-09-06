import { useEffect, useState } from 'react'
import { ArrowUpRight, Building2, CheckCircle2, CircleUserRound, Gauge, Landmark, LogIn, Menu, ShieldCheck, UsersRound, X } from 'lucide-react'

type Organization = { organization_id: string; name: string; organization_type: string; district?: string; state?: string; verification_status: string }
type User = { user_id: string; name: string; email: string; role: string; status: string }

const api = async <T,>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) }, ...options })
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  return response.json()
}

function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [active, setActive] = useState('Overview')
  const [health, setHealth] = useState<'checking' | 'connected' | 'offline'>('checking')
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api<{ database: string }>('/api/health/db'),
      api<Organization[]>('/api/organizations'),
      api<User[]>('/api/users'),
    ]).then(([db, orgs, people]) => {
      setHealth(db.database === 'connected' ? 'connected' : 'offline')
      setOrganizations(orgs)
      setUsers(people)
    }).catch(() => {
      setHealth('offline')
      setError('The API is running, but dashboard data could not be loaded. Check authentication for protected endpoints.')
    })
  }, [])

  const nav = [
    { label: 'Overview', icon: Gauge },
    { label: 'Organizations', icon: Building2 },
    { label: 'People', icon: UsersRound },
    { label: 'Government Profiles', icon: Landmark },
  ]

  return (
    <div className="app-shell">
      <aside className={menuOpen ? 'sidebar open' : 'sidebar'}>
        <div className="brand"><span className="brand-mark">IA</span><span>Impact Atlas</span><button className="mobile-close" onClick={() => setMenuOpen(false)}><X size={18} /></button></div>
        <div className="workspace-label">PLATFORM CONTROL ROOM</div>
        <nav>{nav.map(({ label, icon: Icon }) => <button key={label} className={active === label ? 'nav-item active' : 'nav-item'} onClick={() => { setActive(label); setMenuOpen(false) }}><Icon size={18} />{label}{label === 'Government Profiles' && <span className="nav-count">{organizations.filter(org => ['Government', 'PRI', 'ULB'].includes(org.organization_type)).length}</span>}</button>)}</nav>
        <div className="sidebar-bottom"><div className="connection"><span className={health === 'connected' ? 'status-dot' : 'status-dot offline'} /> <span>{health === 'connected' ? 'Supabase connected' : 'Connection unavailable'}</span></div><div className="profile"><div className="avatar">SA</div><div><strong>System Admin</strong><small>Platform operations</small></div><ArrowUpRight size={15} /></div></div>
      </aside>
      {menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
      <main className="main-content">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMenuOpen(true)}><Menu size={21} /></button><div><p className="eyebrow">SMART AI PROBLEM-TO-IMPACT</p><h1>{active}</h1></div><div className="top-actions"><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="docs-link"><ShieldCheck size={16} /> API Docs</a><button className="login-button"><LogIn size={16} /> Sign in</button></div></header>
        {error && <div className="notice"><ShieldCheck size={17} />{error}</div>}
        {active === 'Overview' ? <Overview organizations={organizations} users={users} health={health} /> : <DataView title={active} organizations={organizations} users={users} />}
      </main>
    </div>
  )
}

function Overview({ organizations, users, health }: { organizations: Organization[]; users: User[]; health: string }) {
  const government = organizations.filter(org => ['Government', 'PRI', 'ULB'].includes(org.organization_type)).length
  return <section className="content"><div className="hero"><div><span className="hero-kicker">FIELD OPERATIONS / 01</span><h2>Turn local signals<br />into <em>lasting impact.</em></h2><p>One operating view for the institutions, people and public capabilities moving ideas from evidence to action.</p></div><div className="hero-seal"><CheckCircle2 size={24} /><span>Live system<br /><strong>Operational</strong></span></div></div><div className="section-heading"><div><p className="eyebrow">SYSTEM PULSE</p><h3>Platform at a glance</h3></div><span className="last-sync">Updated just now</span></div><div className="metric-grid"><Metric icon={Building2} label="Organizations" value={organizations.length} detail="Across the collaboration network" tint="mint" /><Metric icon={UsersRound} label="Registered people" value={users.length} detail="Connected to organizations" tint="peach" /><Metric icon={Landmark} label="Public institutions" value={government} detail="Government, PRI and ULB" tint="lavender" /><Metric icon={ShieldCheck} label="Database health" value={health === 'connected' ? 'Good' : 'Check'} detail="Supabase PostgreSQL" tint="yellow" /></div><div className="lower-grid"><div className="panel activity"><div className="panel-heading"><div><p className="eyebrow">NETWORK MAP</p><h3>Organizations by type</h3></div><ArrowUpRight size={18} /></div>{organizations.length === 0 ? <div className="empty">No organization records loaded yet.</div> : <div className="bars">{Object.entries(organizations.reduce<Record<string, number>>((acc, org) => { acc[org.organization_type] = (acc[org.organization_type] || 0) + 1; return acc }, {})).map(([type, count]) => <div className="bar-row" key={type}><span>{type}</span><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(14, count / organizations.length * 100)}%` }} /></div><b>{count}</b></div>)}</div>}</div><div className="panel quick"><p className="eyebrow">NEXT ACTIONS</p><h3>Keep the network moving</h3><div className="action"><span className="action-icon"><CircleUserRound size={18} /></span><div><strong>Invite a collaborator</strong><small>Expand your organization roster</small></div><ArrowUpRight size={16} /></div><div className="action"><span className="action-icon"><Landmark size={18} /></span><div><strong>Review public profiles</strong><small>Keep government details current</small></div><ArrowUpRight size={16} /></div></div></div></section>
}

function Metric({ icon: Icon, label, value, detail, tint }: { icon: typeof Building2; label: string; value: number | string; detail: string; tint: string }) { return <div className={`metric ${tint}`}><span className="metric-icon"><Icon size={19} /></span><p>{label}</p><strong>{value}</strong><small>{detail}</small></div> }
function DataView({ title, organizations, users }: { title: string; organizations: Organization[]; users: User[] }) { const rows = title === 'People' ? users : organizations; return <section className="content"><div className="section-heading"><div><p className="eyebrow">DIRECTORY</p><h3>{title}</h3></div><button className="primary-button">+ Add record</button></div><div className="panel table-panel">{rows.length === 0 ? <div className="empty">No records available.</div> : <div className="table-wrap"><table><thead><tr>{title === 'People' ? <><th>Name</th><th>Email</th><th>Role</th><th>Status</th></> : <><th>Name</th><th>Type</th><th>Location</th><th>Verification</th></>}</tr></thead><tbody>{rows.map((row) => title === 'People' ? <tr key={(row as User).user_id}><td><strong>{(row as User).name}</strong></td><td>{(row as User).email}</td><td>{(row as User).role}</td><td><span className="pill green">{(row as User).status}</span></td></tr> : <tr key={(row as Organization).organization_id}><td><strong>{(row as Organization).name}</strong></td><td>{(row as Organization).organization_type}</td><td>{(row as Organization).district || '-'}, {(row as Organization).state || '-'}</td><td><span className="pill">{(row as Organization).verification_status}</span></td></tr>)}</tbody></table></div>}</div></section> }

export default App
