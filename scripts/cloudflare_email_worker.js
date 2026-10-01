/**
 * Cloudflare Email Routing Worker for TITAN Autonomous Data Cleaner
 * 
 * Instructions:
 * 1. Go to Cloudflare Dashboard -> Workers & Pages -> Create Application -> Create Worker
 * 2. Paste this code into your Worker editor and Deploy.
 * 3. Go to your Domain -> Email -> Email Routing -> Routing Rules.
 * 4. Add a Custom Address:
 *    - Example: clean@yourdomain.com
 *    - Action: "Send to a Worker"
 *    - Select: this Worker
 * 5. Set Environment Variable in Worker Settings:
 *    - TITAN_WEBHOOK_URL: "https://<your-tunnel-or-domain>/api/automation/email-webhook"
 *    - DESTINATION_EMAIL: "recipient@example.com" (where cleaned data should be sent)
 */

import PostalMime from 'postal-mime';

export default {
  async email(message, env, ctx) {
    const rawEmail = await new Response(message.raw).arrayBuffer();
    const parser = new PostalMime();
    const parsedEmail = await parser.parse(rawEmail);

    const subject = parsedEmail.subject || '';
    const textBody = parsedEmail.text || parsedEmail.html || '';
    const sender = message.from;
    const recipient = env.DESTINATION_EMAIL || message.to;
    const webhookUrl = env.TITAN_WEBHOOK_URL || 'https://YOUR_TUNNEL_URL/api/automation/email-webhook';

    // 1. Check for trigger phrase
    const combinedContent = `${subject} ${textBody}`.toLowerCase();
    if (!combinedContent.includes('clean data')) {
      console.log(`[TITAN] Ignored email from ${sender}: missing trigger phrase 'clean data'.`);
      return;
    }

    // 2. Extract attachment
    if (!parsedEmail.attachments || parsedEmail.attachments.length === 0) {
      console.log(`[TITAN] No attachment found in email from ${sender}.`);
      return;
    }

    const attachment = parsedEmail.attachments[0];
    console.log(`[TITAN] Processing attachment: ${attachment.filename} (${attachment.content.byteLength} bytes)`);

    // 3. Prepare Multipart Form Data to forward to TITAN Backend
    const formData = new FormData();
    formData.append('subject', subject);
    formData.append('text', textBody);
    formData.append('from', sender);
    formData.append('destination_email', recipient);

    const blob = new Blob([attachment.content], { type: attachment.mimeType || 'application/octet-stream' });
    formData.append('file', blob, attachment.filename || 'dataset.csv');

    // 4. Dispatch to TITAN Backend
    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        body: formData,
      });

      const result = await response.text();
      console.log(`[TITAN] Webhook response (${response.status}):`, result);
    } catch (err) {
      console.error('[TITAN] Failed to forward email to TITAN webhook:', err);
    }
  },
};
