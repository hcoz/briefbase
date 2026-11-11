"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { login, register } from "@/lib/api";
import { setToken, useToken } from "@/lib/auth";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const token = useToken();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Already logged in (or just logged in): go to the notes page.
  useEffect(() => {
    if (token) router.replace("/");
  }, [token, router]);

  const auth = useMutation({
    mutationFn: () => (mode === "login" ? login(email, password) : register(email, password)),
    onSuccess: ({ access_token }) => {
      queryClient.clear(); // never show a previous user's cached data
      setToken(access_token); // useToken picks this up and the effect redirects
    },
  });

  const isLogin = mode === "login";

  function switchMode(next: Mode) {
    setMode(next);
    auth.reset();
  }

  return (
    <main className="center-screen">
      <div className="auth">
        <div className="auth-intro">
          <span className="brand">
            <span className="brand-mark" aria-hidden="true">
              B
            </span>
            BriefBase
          </span>
          <p className="muted">Paste a note, get an AI summary and tags.</p>
        </div>

        <form
          className="card stack"
          onSubmit={(e) => {
            e.preventDefault();
            auth.mutate();
          }}
        >
          <div className="segmented" role="group" aria-label="Choose login or registration">
            <button type="button" aria-pressed={isLogin} onClick={() => switchMode("login")}>
              Log in
            </button>
            <button type="button" aria-pressed={!isLogin} onClick={() => switchMode("register")}>
              Register
            </button>
          </div>

          <label className="field">
            <span className="field-label">Email</span>
            <input
              className="input"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <input
              className="input"
              type="password"
              placeholder={isLogin ? "Your password" : "At least 8 characters"}
              autoComplete={isLogin ? "current-password" : "new-password"}
              required
              minLength={isLogin ? undefined : 8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          {auth.isError && <p className="alert">{auth.error.message}</p>}

          <button type="submit" className="btn btn-primary btn-block" disabled={auth.isPending}>
            {auth.isPending && <span className="spinner" aria-hidden="true" />}
            {auth.isPending ? "Please wait…" : isLogin ? "Log in" : "Create account"}
          </button>
        </form>
      </div>
    </main>
  );
}
