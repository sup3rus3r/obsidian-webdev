"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { encryptPayload } from "@/lib/crypto";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { Logo } from "@/components/ui/logo";

const STEPS = [
  { n: 1, label: "Sign up your account" },
  { n: 2, label: "Set up your workspace" },
  { n: 3, label: "Start building with AI" },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7412";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const encryptedData = encryptPayload({ username, email, password });

      const res = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ encrypted: encryptedData }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Registration failed");
      }

      toast.success("Account created! Please sign in.");
      router.push("/login");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-black">
      
      <div
        className="relative hidden lg:flex lg:w-1/2 flex-col items-center justify-center p-12 overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 110% 60% at 50% -10%, rgba(139,92,246,0.7) 0%, rgba(91,33,182,0.28) 42%, transparent 70%), #08080c",
        }}
      >
        
        <div className="mb-10">
          <Logo className="h-7 w-auto" />
        </div>

        
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-white tracking-tight">
            Get Started with Us
          </h2>
          <p className="mt-2 text-sm text-white/45">
            Complete these easy steps to register your account.
          </p>
        </div>

        
        <ul className="w-full max-w-xs space-y-3">
          {STEPS.map(({ n, label }, i) => (
            <li
              key={n}
              className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${
                i === 0
                  ? "bg-white text-black"
                  : "bg-white/5 text-white/35"
              }`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  i === 0
                    ? "bg-black/10 text-black"
                    : "bg-white/10 text-white/35"
                }`}
              >
                {n}
              </span>
              {label}
            </li>
          ))}
        </ul>
      </div>

      
      <div className="flex flex-1 flex-col items-center justify-center px-8 py-12 bg-[#0d0d11]">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Sign Up Account
            </h1>
            <p className="mt-1.5 text-sm text-white/45">
              Enter your personal data to create your account.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="username" className="text-sm text-white/60">
                Username
              </Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                placeholder="your_username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="h-11 bg-white/5 border-white/10 text-white placeholder:text-white/20 focus-visible:ring-violet-500/40 focus-visible:border-violet-500/50 rounded-lg"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm text-white/60">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-11 bg-white/5 border-white/10 text-white placeholder:text-white/20 focus-visible:ring-violet-500/40 focus-visible:border-violet-500/50 rounded-lg"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm text-white/60">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Must be at least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className="h-11 bg-white/5 border-white/10 text-white placeholder:text-white/20 focus-visible:ring-violet-500/40 focus-visible:border-violet-500/50 rounded-lg pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              <p className="text-xs text-white/30">Must be at least 8 characters.</p>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="h-11 w-full cursor-pointer bg-white text-black hover:bg-white/90 font-semibold rounded-lg"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account…
                </>
              ) : (
                "Sign Up"
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-white/40">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-medium text-white/75 hover:text-white transition-colors"
            >
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
