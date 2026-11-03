import React from "react";

export type BadgeVariant =
  | "critical"
  | "high"
  | "elevated"
  | "guarded"
  | "low"
  | "observed"
  | "inferred"
  | "imported"
  | "unknown"
  | "default";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = "default",
  children,
  className = "",
  title,
}) => {
  const getVariantClass = () => {
    switch (variant) {
      case "critical":
        return "qf-badge-critical";
      case "high":
        return "qf-badge-high";
      case "elevated":
        return "qf-badge-elevated";
      case "guarded":
        return "qf-badge-guarded";
      case "low":
        return "qf-badge-low";
      case "observed":
        return "qf-badge-observed";
      case "inferred":
        return "qf-badge-inferred";
      case "imported":
        return "qf-badge-imported";
      case "unknown":
        return "qf-badge-unknown";
      default:
        return "qf-badge-unknown";
    }
  };

  return (
    <span
      className={`qf-badge ${getVariantClass()} ${className}`}
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.3rem",
        padding: "0.2rem 0.55rem",
        borderRadius: "4px",
        fontSize: "0.725rem",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.03em",
      }}
    >
      {children}
    </span>
  );
};

