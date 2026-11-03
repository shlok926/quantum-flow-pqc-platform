import React, { createContext, useContext, useEffect, useState, useMemo } from "react";

interface RouterContextType {
  path: string;
  navigate: (to: string) => void;
  params: Record<string, string>;
}

const RouterContext = createContext<RouterContextType>({
  path: "/",
  navigate: () => {},
  params: {},
});

// eslint-disable-next-line react-refresh/only-export-components
export const useRouter = (): RouterContextType => useContext(RouterContext);

interface RouterProviderProps {
  children: React.ReactNode;
  initialPath?: string;
}

const normalizePath = (raw: string): string => {
  if (!raw) return "/";
  const [pathname] = raw.split("?");
  const clean = pathname.split("#")[0].replace(/\/+$/, "");
  return clean || "/";
};

export const RouterProvider: React.FC<RouterProviderProps> = ({ children, initialPath }) => {
  const [path, setPath] = useState<string>(() => {
    if (initialPath) return normalizePath(initialPath);
    if (typeof window !== "undefined" && window.location) {
      return normalizePath(window.location.pathname);
    }
    return "/";
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handlePopState = () => {
      setPath(normalizePath(window.location.pathname));
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (to: string) => {
    if (typeof window !== "undefined" && window.history) {
      window.history.pushState({}, "", to);
    }
    setPath(normalizePath(to));
    if (typeof window !== "undefined") {
      window.scrollTo(0, 0);
    }
  };

  // Extract route parameters
  const params = useMemo(() => {
    const result: Record<string, string> = {};
    const parts = path.split("/").filter(Boolean);

    // /scan/results/:scanId
    if (parts[0] === "scan" && parts[1] === "results" && parts[2]) {
      result.scanId = parts[2];
    }

    // /app/assessments/:id
    if (parts[0] === "app" && parts[1] === "assessments" && parts[2] && parts[2] !== "new") {
      result.assessmentId = parts[2];
      if (parts[3] === "progress") {
        result.subview = "progress";
      }
    }

    return result;
  }, [path]);

  const value = useMemo(() => ({ path, navigate, params }), [path, params]);

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
};

interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  to: string;
  children: React.ReactNode;
  className?: string;
  activeClassName?: string;
}

export const Link: React.FC<LinkProps> = ({
  to,
  children,
  className = "",
  activeClassName = "",
  onClick,
  ...rest
}) => {
  const { path, navigate } = useRouter();
  const isActive = path === to || (to !== "/" && path.startsWith(to));

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (onClick) onClick(e);
    if (!e.defaultPrevented && e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
      e.preventDefault();
      navigate(to);
    }
  };

  return (
    <a
      href={to}
      onClick={handleClick}
      className={`${className} ${isActive && activeClassName ? activeClassName : ""}`.trim()}
      {...rest}
    >
      {children}
    </a>
  );
};
