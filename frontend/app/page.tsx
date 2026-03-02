import { Header } from "@/components/header";
import { Hero } from "@/components/landing/hero";

export default function Landing() {
  return (
    <div className="min-h-screen overflow-y-auto">
      <Header />
      <main>
        <Hero />
      </main>
      <footer className="border-t border-border/20 py-6 text-center text-[11px] text-muted-foreground/40">
        &copy; {new Date().getFullYear()} Obsidian WebDev &mdash; AI-powered full-stack platform builder
      </footer>
    </div>
  );
}
