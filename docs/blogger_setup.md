# Blogger job publishing with Mail2Blogger

RecruitO publishes approved job listings through its bundled MCP server. The MCP tool sends an email to Blogger's Mail2Blogger address using the existing SMTP configuration. This path does not use Google Cloud or Blogger API OAuth.

## One-time Blogger setup

1. Sign in to Blogger and open the `recruito.blogspot.com` blog.
2. Go to **Settings → Email → Post using email**.
3. Choose **Save emails as draft posts** while setting this up, so you can review posts before publishing them.
4. Create the special posting address and save it. Treat it like a password: anyone who knows it can post as you.

## Configure RecruitO

Add these values to the root `.env` file. Do not commit `.env` or share the Mail2Blogger address or SMTP password in chat.

```dotenv
PUBLIC_BASE_URL=https://your-public-recruito-domain
BLOGGER_SITE_URL=https://recruito.blogspot.com
BLOGGER_POST_EMAIL=your-private-mail2blogger-address
BLOGGER_MCP_URL=http://blogger-mcp:8001/mcp
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=your-sender-address
```

RecruitO already uses SMTP to send application receipt emails, so configure the same sender settings here. Gmail users typically need an App Password when two-step verification is enabled; regular account passwords may not work. The sender must be allowed to send to Blogger's special posting address.

For real applications, `PUBLIC_BASE_URL` must be RecruitO's publicly reachable HTTPS frontend address. A local URL such as `http://localhost:5500` cannot receive applications from external candidates. To test email delivery before deployment, set `PUBLIC_BASE_URL=http://localhost:5500` and `ALLOW_LOCAL_BLOGGER_URL=true`; leave Blogger set to save posts as drafts. The generated application link then works only on the computer running RecruitO. Set `ALLOW_LOCAL_BLOGGER_URL=false` and replace `PUBLIC_BASE_URL` with the public HTTPS address before publishing a real job.

## Publish

Start or rebuild the application with `docker compose up --build`, sign in as a hiring manager, and approve a job. Click **Email post to Blogger**. Blogger will create the post according to the Mail2Blogger setting. When set to drafts, review and publish it from Blogger. Do not publish a local-test draft for candidates: its application link is not publicly accessible.

Mail2Blogger does not return a post ID or post permalink, and it cannot update a post that has already been emailed. RecruitO links candidates to `https://recruito.blogspot.com`; sending the same job again creates another Blogger post. A successful MCP call confirms the email was accepted by the SMTP server, not that Blogger has finished creating the post.

## Troubleshooting

- If RecruitO reports missing settings, confirm `BLOGGER_POST_EMAIL`, `BLOGGER_SITE_URL`, and SMTP values are set in `.env`.
- If SMTP authentication fails, check the mail provider's SMTP host, port, username, and application-password requirements.
- If the SMTP server accepts the email but Blogger creates no post, check that the Mail2Blogger address is correct and review Blogger's posting-email setting.
- Applying the Blogger publishing change does not require a database migration.
