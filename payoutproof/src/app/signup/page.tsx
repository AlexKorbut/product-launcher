export const metadata = { title: "Start your trial — PayoutProof" };

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ plan?: string }>;
}) {
  const { plan = "growth" } = await searchParams;
  return (
    <main className="container">
      <section className="hero" style={{ paddingBottom: 24 }}>
        <h1>Start your 14-day free trial</h1>
        <p className="lead">
          Enter your email — we&apos;ll send a sign-in link, then take you to checkout for the{" "}
          <strong>{plan}</strong> plan.
        </p>
      </section>

      <div className="panel" style={{ maxWidth: 440, margin: "0 auto" }}>
        <form action="/api/auth/request" method="POST">
          <input type="hidden" name="next" value={`/api/checkout/${plan}`} />
          <label className="muted">Email address</label>
          <input type="email" name="email" required placeholder="you@store.com" autoFocus />
          <button className="btn mt" type="submit" style={{ width: "100%" }}>
            Continue to checkout
          </button>
        </form>
      </div>
    </main>
  );
}
