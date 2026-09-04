import { useState } from "react";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("brendan.allen@senus.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim()) {
      setError("Enter an email address to continue.");
      return;
    }
    const name = email.split("@")[0].split(".").map(
      (s) => s.charAt(0).toUpperCase() + s.slice(1)
    ).join(" ");
    onLogin({ name, email });
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-mark" />
          <span className="brand-name">Senus</span>
        </div>
        <div className="login-title">Board Report</div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@senus.com"
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          {error && (
            <div style={{ color: "#d98267", fontSize: "0.82rem", marginBottom: 12 }}>
              {error}
            </div>
          )}
          <button type="submit" className="btn-primary">Sign in</button>
        </form>

        <div className="login-note">
          Demo authentication for this assessment build — any email/password
          combination signs you in as that user. A production deployment would
          replace this with SSO or the Company's identity provider.
        </div>
      </div>
    </div>
  );
}
