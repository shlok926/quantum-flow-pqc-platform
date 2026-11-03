import React, { useState } from "react";
import { ShieldCheck, Radar, ArrowRight, Menu, X, Lock } from "lucide-react";
import { useRouter } from "../../router";

export const PublicNavbar: React.FC = () => {
  const { path, navigate } = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const navLinks = [
    { label: "Platform", href: "/platform" },
    { label: "Intelligence", href: "/intelligence" },
    { label: "Resources", href: "/resources" },
    { label: "About", href: "/about" },
  ];

  return (
    <header className="qf-public-header" style={{
      position: "sticky",
      top: 0,
      zIndex: 50,
      backgroundColor: "rgba(250, 249, 245, 0.94)",
      backdropFilter: "blur(8px)",
      borderBottom: "1px solid var(--border-color)",
      padding: "0.85rem 2rem",
    }}>
      <div style={{
        maxWidth: "1280px",
        margin: "0 auto",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        {/* Left: Original Brand Logo */}
        <div
          onClick={() => navigate("/")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "8px",
              backgroundColor: "var(--olive-light)",
              border: "1px solid var(--olive-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--olive-primary)",
              boxShadow: "0 1px 2px rgba(59, 82, 64, 0.08)",
            }}
          >
            <ShieldCheck size={22} />
          </div>
          <div>
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "1.25rem",
                fontWeight: 700,
                letterSpacing: "-0.01em",
                color: "var(--text-primary)",
                lineHeight: 1.1,
              }}
            >
              QUANTUM FLOW
            </div>
            <div
              style={{
                fontSize: "0.7rem",
                color: "var(--text-muted)",
                letterSpacing: "0.03em",
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              PQC Discovery & Risk Intelligence
            </div>
          </div>
        </div>

        {/* Center: Desktop Navigation Links */}
        <nav
          className="qf-desktop-nav"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2rem",
          }}
        >
          {navLinks.map((item) => {
            const isActive = path === item.href;
            return (
              <button
                key={item.href}
                type="button"
                onClick={() => navigate(item.href)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "0.9rem",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? "var(--olive-primary)" : "var(--text-secondary)",
                  padding: "0.4rem 0.2rem",
                  borderBottom: isActive ? "2px solid var(--olive-primary)" : "2px solid transparent",
                  transition: "all 0.15s ease",
                }}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Right: Actions */}
        <div
          className="qf-desktop-actions"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <button
            type="button"
            className="qf-btn-outline"
            onClick={() => navigate("/scan")}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.85rem",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              borderRadius: "6px",
              border: "1px solid var(--olive-border)",
              color: "var(--olive-primary)",
              backgroundColor: "transparent",
              cursor: "pointer",
            }}
          >
            <Radar size={15} />
            <span>Free Scanner</span>
          </button>

          <button
            type="button"
            className="qf-btn-primary"
            onClick={() => navigate("/request-demo")}
            style={{
              padding: "0.5rem 1.1rem",
              fontSize: "0.85rem",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              borderRadius: "6px",
              border: "none",
              color: "#FFFFFF",
              backgroundColor: "var(--olive-primary)",
              cursor: "pointer",
            }}
          >
            <span>Request Demo</span>
            <ArrowRight size={14} />
          </button>

          <button
            type="button"
            onClick={() => navigate("/app")}
            title="Open Enterprise Console"
            style={{
              padding: "0.5rem 0.75rem",
              fontSize: "0.8rem",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
              borderRadius: "6px",
              border: "1px solid var(--border-color)",
              color: "var(--text-secondary)",
              backgroundColor: "var(--bg-tertiary)",
              cursor: "pointer",
            }}
          >
            <Lock size={13} style={{ color: "var(--olive-primary)" }} />
            <span>Console</span>
          </button>
        </div>

        {/* Mobile menu toggle */}
        <button
          type="button"
          className="qf-mobile-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
          style={{
            display: "none",
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--text-primary)",
          }}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          style={{
            marginTop: "0.75rem",
            paddingTop: "1rem",
            borderTop: "1px solid var(--border-color)",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          {navLinks.map((item) => (
            <button
              key={item.href}
              type="button"
              onClick={() => {
                navigate(item.href);
                setMobileMenuOpen(false);
              }}
              style={{
                textAlign: "left",
                background: "none",
                border: "none",
                padding: "0.6rem 0",
                fontSize: "1rem",
                fontWeight: path === item.href ? 600 : 500,
                color: path === item.href ? "var(--olive-primary)" : "var(--text-primary)",
              }}
            >
              {item.label}
            </button>
          ))}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button
              type="button"
              onClick={() => {
                navigate("/scan");
                setMobileMenuOpen(false);
              }}
              style={{
                padding: "0.75rem",
                borderRadius: "6px",
                border: "1px solid var(--olive-primary)",
                backgroundColor: "transparent",
                color: "var(--olive-primary)",
                fontWeight: 600,
              }}
            >
              Free Scanner
            </button>
            <button
              type="button"
              onClick={() => {
                navigate("/request-demo");
                setMobileMenuOpen(false);
              }}
              style={{
                padding: "0.75rem",
                borderRadius: "6px",
                border: "none",
                backgroundColor: "var(--olive-primary)",
                color: "#FFFFFF",
                fontWeight: 600,
              }}
            >
              Request Demo
            </button>
            <button
              type="button"
              onClick={() => {
                navigate("/app");
                setMobileMenuOpen(false);
              }}
              style={{
                padding: "0.75rem",
                borderRadius: "6px",
                border: "1px solid var(--border-color)",
                backgroundColor: "var(--bg-tertiary)",
                color: "var(--text-secondary)",
                fontWeight: 600,
              }}
            >
              Enterprise Console
            </button>
          </div>
        </div>
      )}
    </header>
  );
};

