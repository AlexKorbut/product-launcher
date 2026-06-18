export const metadata = { title: "Sign in — PayoutProof" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ sent?: string; error?: string; next?: string }>;
}) {
  const params = await searchParams;
  return (
    <main className="container">
      <section className="hero" style={{ paddingBottom: 24 }}>
        <h1>Sign in to PayoutProof</h1>
        <p className="lead">
          Enter your email and we&apos;ll send you a one-click sign-in link. No password.
        </p>
      </section>

      <div className="panel" style={{ maxWidth: 440, margin: "0 auto" }}>
        {params.sent ? (
          <p className="center">
            Check your inbox — we sent a sign-in link. It expires in 30 minutes.
          </p>
        ) : (
          <form action="/api/auth/request" method="POST">
            <input type="hidden" name="next" value={params.next ?? "/app"} />
            <label className="muted">Email address</label>
            <input type="email" name="email" required placeholder="you@store.com" autoFocus />
            {params.error && (
              <p style={{ color: "var(--danger)" }}>
                {params.error === "expired"
                  ? "That link expired — request a new one."
                  : "Please enter a valid email."}
              </p>
            )}
            <button className="btn mt" type="submit" style={{ width: "100%" }}>
              Send sign-in link
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
