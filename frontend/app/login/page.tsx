"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { login, register } from "@/lib/api";
import { setToken, useToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const token = useToken();
  const [mode, setMode] = useState<"login" | "register">("login");
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

  return (
    <main>
      <h1>BriefBase</h1>
      <h2>{isLogin ? "Log in" : "Create an account"}</h2>
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          auth.mutate();
        }}
      >
        <input
          type="email"
          placeholder="Email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder={isLogin ? "Password" : "Password (at least 8 characters)"}
          autoComplete={isLogin ? "current-password" : "new-password"}
          required
          minLength={isLogin ? undefined : 8}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={auth.isPending}>
          {auth.isPending ? "Please wait…" : isLogin ? "Log in" : "Register"}
        </button>
        {auth.isError && <p className="error">{auth.error.message}</p>}
      </form>
      <p>
        {isLogin ? "No account yet? " : "Already have an account? "}
        <button
          type="button"
          className="link"
          onClick={() => {
            setMode(isLogin ? "register" : "login");
            auth.reset();
          }}
        >
          {isLogin ? "Register" : "Log in"}
        </button>
      </p>
    </main>
  );
}
