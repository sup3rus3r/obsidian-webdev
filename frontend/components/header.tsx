"use client";

import { useScroll } from "@/hooks/use-scroll";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { LogOut, Menu, X } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useState } from "react";

export function Header() {
  const router = useRouter();
  const { data: session } = useSession();
  const scrolled = useScroll(10);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full border-b border-transparent transition-all duration-300",
        scrolled && "border-border/50 bg-background/80 backdrop-blur-xl"
      )}
    >
      <nav className="mx-auto flex h-16 max-w-screen-2xl items-center justify-between px-8">
        
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="flex items-center gap-2.5 cursor-pointer"
        >
          <Logo className="h-5 w-auto" />
        </button>

        
        <div className="hidden items-center gap-3 md:flex">
          {session ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full h-8 w-8">
                  <div className="h-8 w-8 rounded-full bg-violet-500/15 flex items-center justify-center text-sm font-semibold text-violet-400">
                    {(session.user?.name ?? session.user?.email ?? "U")[0].toUpperCase()}
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="flex flex-col gap-1 px-2 py-1.5">
                  <p className="text-xs text-muted-foreground">Signed in as</p>
                  <p className="text-sm font-medium truncate">
                    {session.user?.name ?? session.user?.email}
                  </p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => router.push("/dashboard")}
                  className="cursor-pointer"
                >
                  Go to Dashboard
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => signOut({ callbackUrl: "/login" })}
                  className="cursor-pointer text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Button
                variant="ghost"
                className="cursor-pointer text-sm"
                onClick={() => router.push("/login")}
              >
                Sign In
              </Button>
              <Button
                className="cursor-pointer text-sm bg-violet-600 hover:bg-violet-700 text-white"
                onClick={() => router.push("/register")}
              >
                Get Started
              </Button>
            </>
          )}
        </div>

        
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </nav>

      
      {mobileOpen && (
        <div className="border-t border-border/50 bg-background/95 backdrop-blur-xl md:hidden">
          <div className="flex flex-col gap-2 p-4">
            {session ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => { router.push("/dashboard"); setMobileOpen(false); }}
                  className="w-full"
                >
                  Dashboard
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => signOut({ callbackUrl: "/login" })}
                  className="w-full text-destructive"
                >
                  Sign Out
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() => { router.push("/login"); setMobileOpen(false); }}
                  className="w-full"
                >
                  Sign In
                </Button>
                <Button
                  onClick={() => { router.push("/register"); setMobileOpen(false); }}
                  className="w-full bg-violet-600 hover:bg-violet-700 text-white"
                >
                  Get Started
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
