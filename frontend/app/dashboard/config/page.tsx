"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { getUserDetails, updateProfile, changePassword } from "@/lib/api/user";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Loader2 } from "lucide-react";

export default function ConfigPage() {
  const { data: session, update: updateSession } = useSession();


  const [loadingProfile, setLoadingProfile] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profile, setProfile] = useState({ username: "", email: "" });


  const [savingPassword, setSavingPassword] = useState(false);
  const [pwForm, setPwForm] = useState({ current: "", next: "", confirm: "" });
  const pwMismatch = pwForm.next !== pwForm.confirm && pwForm.confirm.length > 0;


  useEffect(() => {
    if (!session?.accessToken) return;
    getUserDetails(session.accessToken)
      .then((u) => setProfile({ username: u.username, email: u.email }))
      .catch(() => toast.error("Failed to load profile"))
      .finally(() => setLoadingProfile(false));
  }, [session?.accessToken]);


  const handleSaveProfile = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!session?.accessToken) return;
    setSavingProfile(true);
    try {
      const updated = await updateProfile(
        { username: profile.username, email: profile.email },
        session.accessToken,
      );
      await updateSession({ name: updated.username });
      toast.success("Profile updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!session?.accessToken || pwMismatch) return;
    setSavingPassword(true);
    try {
      await changePassword(pwForm.current, pwForm.next, session.accessToken);
      toast.success("Password changed");
      setPwForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setSavingPassword(false);
    }
  };


  return (
    <div className="flex flex-1 flex-col min-h-0">

      <header className="flex h-14 shrink-0 items-center gap-4 border-b px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="h-5" />
        <h1 className="text-sm font-semibold">Settings</h1>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-6">


          <div className="rounded-xl border bg-card">
            <div className="px-6 py-5 border-b">
              <h2 className="text-sm font-semibold">Profile</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Update your display name and email address.
              </p>
            </div>

            <div className="px-6 py-5">
              {loadingProfile ? (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <Skeleton className="h-3.5 w-20 rounded" />
                    <Skeleton className="h-9 rounded-md" />
                  </div>
                  <div className="space-y-1.5">
                    <Skeleton className="h-3.5 w-10 rounded" />
                    <Skeleton className="h-9 rounded-md" />
                  </div>
                  <Skeleton className="h-9 w-28 rounded-md" />
                </div>
              ) : (
                <form onSubmit={handleSaveProfile} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="username" className="text-xs text-muted-foreground">
                        Username
                      </Label>
                      <Input
                        id="username"
                        value={profile.username}
                        onChange={(e) =>
                          setProfile((p) => ({ ...p, username: e.target.value }))
                        }
                        required
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="email" className="text-xs text-muted-foreground">
                        Email
                      </Label>
                      <Input
                        id="email"
                        type="email"
                        value={profile.email}
                        onChange={(e) =>
                          setProfile((p) => ({ ...p, email: e.target.value }))
                        }
                        required
                      />
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <Button
                      type="submit"
                      size="sm"
                      disabled={savingProfile || !profile.username.trim() || !profile.email.trim()}
                      className="gap-1.5"
                    >
                      {savingProfile && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                      Save changes
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>


          <div className="rounded-xl border bg-card">
            <div className="px-6 py-5 border-b">
              <h2 className="text-sm font-semibold">Change password</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Minimum 8 characters. You&apos;ll need your current password to confirm.
              </p>
            </div>

            <div className="px-6 py-5">
              <form onSubmit={handleChangePassword} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="current-pw" className="text-xs text-muted-foreground">
                    Current password
                  </Label>
                  <Input
                    id="current-pw"
                    type="password"
                    autoComplete="current-password"
                    value={pwForm.current}
                    onChange={(e) => setPwForm((f) => ({ ...f, current: e.target.value }))}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="new-pw" className="text-xs text-muted-foreground">
                      New password
                    </Label>
                    <Input
                      id="new-pw"
                      type="password"
                      autoComplete="new-password"
                      minLength={8}
                      value={pwForm.next}
                      onChange={(e) => setPwForm((f) => ({ ...f, next: e.target.value }))}
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="confirm-pw" className="text-xs text-muted-foreground">
                      Confirm new password
                    </Label>
                    <Input
                      id="confirm-pw"
                      type="password"
                      autoComplete="new-password"
                      value={pwForm.confirm}
                      onChange={(e) => setPwForm((f) => ({ ...f, confirm: e.target.value }))}
                      className={pwMismatch ? "border-destructive focus-visible:ring-destructive" : ""}
                      required
                    />
                    {pwMismatch && (
                      <p className="text-[11px] text-destructive">Passwords do not match</p>
                    )}
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button
                    type="submit"
                    size="sm"
                    disabled={
                      savingPassword ||
                      !pwForm.current ||
                      !pwForm.next ||
                      !pwForm.confirm ||
                      pwMismatch
                    }
                    className="gap-1.5"
                  >
                    {savingPassword && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    Change password
                  </Button>
                </div>
              </form>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
