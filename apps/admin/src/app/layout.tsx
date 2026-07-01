import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'Quanta Aptus Admin', template: '%s | Quanta Aptus Admin' },
  description: 'Quanta Aptus Content Registry Admin',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <a href="/" className="nav-brand">Quanta Aptus</a>
          <a href="/learn" className="nav-link">Learn</a>
          <a href="/learn/practice" className="nav-link">Practice</a>
          <a href="/learn/results" className="nav-link">Results</a>
          <a href="/learn/attempt-review" className="nav-link">Attempt Review</a>
          <a href="/content/active" className="nav-link">Active Content</a>
          <a href="/content" className="nav-link">Content Registry</a>
          <a href="/content/review"     className="nav-link">Teacher Review</a>
          <a href="/login"             className="nav-link">Login</a>
          <a href="/system/auth-roles"  className="nav-link">Auth Roles</a>
          <a href="/system/demo-safety"         className="nav-link">Demo Safety</a>
          <a href="/system/credential-safety"  className="nav-link">Cred Safety</a>
          <a href="/system/ai-authoring"      className="nav-link">AI Authoring</a>
        </nav>
        {children}
      </body>
    </html>
  )
}
