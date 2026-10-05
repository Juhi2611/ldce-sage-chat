import { Link, useRouterState } from "@tanstack/react-router";
import { BarChart3, Building2, MessageCircle, Moon, Sun } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import logo from "@/assets/ldce-logo.png.asset.json";
import { Button } from "@/components/ui/button";
const links = [
  ["/", "Chat", MessageCircle],
  ["/departments", "Departments", Building2],
  ["/admin", "Admin Dashboard", BarChart3],
] as const;
export function SiteShell({ children }: { children: ReactNode }) {
  const [dark, setDark] = useState(false);
  const path = useRouterState({ select: (s) => s.location.pathname });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b border-border/70 bg-background/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1500px] items-center gap-3 px-4 lg:px-8">
          <Link to="/" className="flex min-w-0 items-center gap-3">
            <img src={logo.url} alt="LDCE crest" className="size-10 shrink-0" />
            <div className="min-w-0">
              <div className="truncate font-display text-sm font-bold text-primary sm:text-base">
                LDCE Smart Enquiry
              </div>
              <div className="hidden text-[10px] uppercase text-muted-foreground sm:block">
                L. D. College of Engineering
              </div>
            </div>
          </Link>
          <nav className="ml-auto hidden items-center gap-1 md:flex">
            {links.map(([to, label, Icon]) => (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${path === to ? "bg-accent text-primary" : "text-muted-foreground hover:bg-accent"}`}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            ))}
          </nav>
          <Button
            variant="icon"
            size="icon"
            onClick={() => setDark((v) => !v)}
            aria-label={dark ? "Use light mode" : "Use dark mode"}
          >
            {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </Button>
        </div>
      </header>
      <main>{children}</main>
      <nav className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-3 border-t border-border bg-background/95 px-2 py-1 backdrop-blur md:hidden">
        {links.map(([to, label, Icon]) => (
          <Link
            key={to}
            to={to}
            className={`flex flex-col items-center gap-1 rounded-lg py-2 text-[11px] ${path === to ? "text-primary" : "text-muted-foreground"}`}
          >
            <Icon className="size-5" />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
