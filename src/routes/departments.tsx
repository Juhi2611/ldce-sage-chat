import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Bot,
  Braces,
  Building,
  CircuitBoard,
  Cpu,
  Database,
  Factory,
  FlaskConical,
  Radio,
  Ruler,
  Search,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageFooter } from "@/components/PageFooter";
import { Button } from "@/components/ui/button";
import { api, type DepartmentItem } from "@/lib/api";

const DEPT_ICONS: Record<string, LucideIcon> = {
  "Computer Engineering": Braces,
  "Information Technology": Database,
  "Artificial Intelligence and Machine Learning": Cpu,
  "Mechanical Engineering": Factory,
  "Civil Engineering": Building,
  "Electrical Engineering": Zap,
  "Electronics and Communication Engineering": Radio,
  "Instrumentation and Control Engineering": CircuitBoard,
  "Chemical Engineering": FlaskConical,
  "Automobile Engineering": Factory,
  "Biomedical Engineering": Cpu,
  "Environmental Engineering": Building,
  "Plastic Technology": FlaskConical,
  "Rubber Technology": FlaskConical,
  "Textile Technology": Factory,
  "Applied Science & Humanities": Ruler,
};

function getDeptIcon(deptName: string): LucideIcon {
  return DEPT_ICONS[deptName] || Building;
}

export const Route = createFileRoute("/departments")({
  head: () => ({
    meta: [
      { title: "Departments — LDCE Smart Enquiry" },
      {
        name: "description",
        content: "Explore engineering departments at L. D. College of Engineering.",
      },
      { property: "og:title", content: "LDCE Departments" },
      {
        property: "og:description",
        content: "Discover departments and ask the LDCE assistant for programme guidance.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Departments,
});

function Departments() {
  const [search, setSearch] = useState("");

  const { data: departments, isLoading } = useQuery<DepartmentItem[]>({
    queryKey: ["departments"],
    queryFn: () => api.getDepartments(),
    staleTime: 1000 * 60 * 10,
  });

  const filteredDepartments = useMemo(() => {
    if (!departments) return [];
    const q = search.trim().toLowerCase();
    if (!q) return departments;
    return departments.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.canonical_name?.toLowerCase().includes(q) ||
        d.code?.toLowerCase().includes(q) ||
        d.overview?.toLowerCase().includes(q),
    );
  }, [departments, search]);

  return (
    <>
      <section className="heritage-band px-4 py-14">
        <div className="mx-auto max-w-[1400px]">
          <p className="section-label text-warm">Academic pathways</p>
          <h1 className="mt-3 max-w-3xl font-display text-4xl font-bold sm:text-6xl">
            Explore our <span className="text-primary">departments</span>
          </h1>
          <p className="mt-4 max-w-2xl text-muted-foreground">
            Find the discipline that fits your ambitions, then continue the conversation with the
            enquiry assistant.
          </p>

          <div className="mt-6 max-w-md">
            <label className="flex items-center gap-2 rounded-xl border border-border bg-card/80 px-3.5 py-2 shadow-sm backdrop-blur focus-within:ring-2 focus-within:ring-primary/40">
              <Search className="size-4 text-muted-foreground shrink-0" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search departments by name or keyword…"
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
            </label>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-[1400px] grid-cols-1 gap-4 px-4 py-12 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="flex min-h-64 flex-col rounded-2xl border border-border bg-card p-6 shadow-soft animate-pulse"
            >
              <div className="size-11 rounded-xl bg-accent" />
              <div className="mt-7 space-y-2">
                <div className="h-3 w-8 bg-muted rounded" />
                <div className="h-5 w-3/4 bg-muted rounded" />
                <div className="h-12 w-full bg-muted rounded" />
              </div>
              <div className="mt-auto h-9 w-32 bg-muted rounded" />
            </div>
          ))
        ) : filteredDepartments.length === 0 ? (
          <div className="col-span-full py-16 text-center">
            <p className="text-lg font-semibold">No departments found matching "{search}"</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Try searching with a different term.
            </p>
          </div>
        ) : (
          filteredDepartments.map((dept, i) => {
            const Icon = getDeptIcon(dept.name);
            const starterQuestion =
              dept.starter_question || `Tell me about ${dept.name} department at LDCE`;
            return (
              <article
                key={dept.id || dept.name}
                className={`group flex min-h-64 flex-col rounded-2xl border border-border bg-card p-6 shadow-soft transition-all hover:-translate-y-1 hover:shadow-lg ${
                  i === 0 ? "sm:col-span-2" : ""
                }`}
              >
                <div className="flex size-11 items-center justify-center rounded-xl bg-accent text-primary">
                  <Icon className="size-5" />
                </div>
                <div className="mt-7">
                  <span className="font-display text-xs text-warm">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h2 className="mt-1 font-display text-xl font-bold">{dept.name}</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground line-clamp-3">
                    {dept.overview}
                  </p>
                </div>
                <Button asChild variant="secondary" className="mt-auto self-start pt-4">
                  <Link to="/" search={{ ask: starterQuestion }}>
                    <Bot className="size-4" />
                    Ask the chatbot
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </article>
            );
          })
        )}
      </section>
      <PageFooter />
    </>
  );
}
