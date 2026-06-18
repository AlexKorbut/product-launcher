import { env } from "./env";

export interface EmailMessage {
  to: string;
  subject: string;
  html: string;
  text?: string;
}

/**
 * Send an email via Resend. When no RESEND_API_KEY is configured (local dev),
 * log the message instead of failing — magic links stay usable without email
 * infrastructure.
 */
export async function sendEmail(msg: EmailMessage): Promise<void> {
  if (!env.resendApiKey) {
    console.log(
      `\n[email:dev] to=${msg.to}\n  subject: ${msg.subject}\n  ${msg.text ?? stripHtml(msg.html)}\n`,
    );
    return;
  }
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.resendApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.emailFrom,
      to: msg.to,
      subject: msg.subject,
      html: msg.html,
      text: msg.text ?? stripHtml(msg.html),
    }),
  });
  if (!res.ok) {
    throw new Error(`Resend error ${res.status}: ${await res.text()}`);
  }
}

export function magicLinkEmail(url: string): Pick<EmailMessage, "subject" | "html" | "text"> {
  return {
    subject: "Your PayoutProof sign-in link",
    html: `<p>Click to sign in to PayoutProof:</p><p><a href="${url}">${url}</a></p><p>This link expires in 30 minutes and can be used once.</p>`,
    text: `Sign in to PayoutProof: ${url}\nThis link expires in 30 minutes.`,
  };
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}
