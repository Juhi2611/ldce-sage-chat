import { createFileRoute } from "@tanstack/react-router";
import { ChatExperience } from "@/components/ChatExperience";
import { PageFooter } from "@/components/PageFooter";
export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "LDCE Smart Enquiry Assistant" },
      {
        name: "description",
        content:
          "Ask about LDCE admissions, fees, hostels, placements, academics and campus facilities.",
      },
      { property: "og:title", content: "LDCE Smart Enquiry Assistant" },
      {
        property: "og:description",
        content: "Fast, helpful answers for prospective and current LDCE students.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Home,
});
function Home() {
  return (
    <>
      <section className="heritage-band px-4 pb-14 pt-12 text-center sm:pb-16 sm:pt-16">
        <p className="section-label text-warm">L. D. College of Engineering · Ahmedabad</p>
        <h1 className="mx-auto mt-3 max-w-3xl font-display text-4xl font-bold leading-tight sm:text-6xl">
          Ask anything about <span className="text-primary">LDCE</span>
        </h1>
        <p className="mt-4 font-devanagari text-lg text-primary">सा विद्या या विमुक्तये</p>
        <p className="mt-1 text-xs font-semibold uppercase text-muted-foreground">
          Envisioning future, celebrating legacy
        </p>
        <p className="mx-auto mt-5 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
          Get helpful guidance on admissions, fees, hostel, placements, academics and life on
          campus.
        </p>
      </section>
      <div className="-mt-7">
        <ChatExperience />
      </div>
      <PageFooter />
    </>
  );
}
