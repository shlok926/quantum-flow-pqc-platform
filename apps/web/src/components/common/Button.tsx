import React from "react";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "outline" | "danger" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  isLoading = false,
  icon,
  children,
  className = "",
  disabled,
  ...props
}) => {
  const getVariantClass = () => {
    switch (variant) {
      case "primary":
        return "qf-btn-primary";
      case "secondary":
        return "qf-btn-secondary";
      case "outline":
        return "qf-btn-outline";
      case "danger":
        return "qf-btn-danger";
      case "ghost":
        return "qf-btn-secondary";
      default:
        return "qf-btn-primary";
    }
  };

  const getSizeStyle = () => {
    switch (size) {
      case "sm":
        return { padding: "0.35rem 0.75rem", fontSize: "0.775rem" };
      case "lg":
        return { padding: "0.75rem 1.5rem", fontSize: "1rem" };
      default:
        return {};
    }
  };

  return (
    <button
      className={`${getVariantClass()} ${className}`}
      style={getSizeStyle()}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="qf-spin" size={size === "sm" ? 14 : 16} />
      ) : (
        icon && <span style={{ display: "inline-flex" }}>{icon}</span>
      )}
      <span>{children}</span>
    </button>
  );
};

