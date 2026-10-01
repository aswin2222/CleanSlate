/**
 * Cloudflare Email Routing Worker for TITAN Autonomous Data Engine
 * 
 * Flow:
 * 1. An incoming email is received at your Cloudflare domain (e.g., clean@yourdomain.com).
 * 2. This worker intercepts the email, parses the headers, subject, body, and attachment.
 * 3. It checks for the trigger phrase "clean data" (case-insensitive in subject or body).
 * 4. It extracts the dataset attachment and converts it to base64.
 * 5. It dispatches a webhook to TITAN (https://titancoho.netlify.app/api/automation/email-webhook).
 * 6. TITAN's headless cleaning engine autonomously standardizes the data and emails the
 *    cleaned file + interactive audit report back to the sender via Resend API.
 */

import PostalMime from 'postal-mime';

// Utility to convert ArrayBuffer/Uint8Array to Base64 in Cloudflare Worker runtime
function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  const chunkSize = 8192;
  for (let i = 0; i < len; i += chunkSize) {
    const chunk = bytes.subarray(i, Math.min(i + chunkSize, len));
    binary += String.fromCharCode.apply(null, chunk);
  }
  return btoa(binary);
}

export default {
  async email(message, env, ctx) {
    const sender = message.from;
    const recipient = env.DESTINATION_EMAIL || sender;
    const webhookUrl = env.TITAN_WEBHOOK_URL || 'https://titancoho.netlify.app/api/automation/email-webhook';

    console.log(`[TITAN] Inbound email from '${sender}' to '${message.to}'`);

    // 1. Read raw email stream
    const rawEmail = await new Response(message.raw).arrayBuffer();
    const parser = new PostalMime();
    const parsedEmail = await parser.parse(rawEmail);

    const subject = parsedEmail.subject || '';
    const textBody = parsedEmail.text || parsedEmail.html || '';

    // 2. Validate trigger phrase
    const combinedContent = `${subject} ${textBody}`.toLowerCase();
    if (!combinedContent.includes('clean data')) {
      console.log(`[TITAN] Ignored email from ${sender}: missing trigger phrase 'clean data'.`);
      return;
    }

    // 3. Validate attachments
    if (!parsedEmail.attachments || parsedEmail.attachments.length === 0) {
      console.log(`[TITAN] Warning: 'clean data' found, but no attachment was attached by ${sender}.`);
      return;
    }

    const attachment = parsedEmail.attachments[0];
    const filename = attachment.filename || 'dataset.csv';
    console.log(`[TITAN] Extracted attachment '${filename}' (${attachment.content.byteLength} bytes)`);

    // 4. Encode attachment to Base64
    const base64Content = arrayBufferToBase64(attachment.content);

    // 5. Construct payload for TITAN webhook
    const payload = {
      subject: subject,
      text: textBody,
      from: sender,
      destination_email: recipient,
      filename: filename,
      file_base64: base64Content,
    };

    // 6. Post to TITAN Backend Webhook
    try {
      console.log(`[TITAN] Forwarding to webhook: ${webhookUrl}`);
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'TITAN-Cloudflare-Email-Worker/1.0',
        },
        body: JSON.stringify(payload),
      });

      const responseText = await response.text();
      console.log(`[TITAN] Webhook responded (${response.status}):`, responseText);
    } catch (err) {
      console.error(`[TITAN] Failed to forward email to TITAN webhook:`, err);
    }
  },
};
