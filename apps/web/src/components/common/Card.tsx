import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export const Card: React.FC<CardProps> = ({ children, className = "", style = {}, onClick }) => {
  return (
    <div
      className={`qf-card ${className}`}
      onClick={onClick}
      style={{
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border-color)",
        borderRadius: "10px",
        padding: "1.5rem",
        boxShadow: "0 1px 3px rgba(15, 23, 42, 0.03)",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ title, subtitle, icon, action }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "1rem",
        marginBottom: "1rem",
        borderBottom: subtitle ? "1px solid var(--border-light)" : "none",
        paddingBottom: subtitle ? "0.75rem" : "0",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
        {icon && <span style={{ color: "var(--olive-primary)" }}>{icon}</span>}
        <div>
          <h3
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "1.1rem",
              fontWeight: 600,
              color: "var(--text-primary)",
              margin: 0,
            }}
          >
            {title}
          </h3>
          {subtitle && (
            <p
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                margin: "0.25rem 0 0 0",
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};
