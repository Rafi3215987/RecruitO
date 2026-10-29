

import os
import smtplib
import ssl
import json
from email.message import EmailMessage
from html import escape
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "RecruitO Blogger Publisher",
    host="0.0.0.0",
    port=8001,
    stateless_http=True,
    json_response=True,
)


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


@mcp.tool()
def publish_job(
    title: str,
    seniority: str,
    description_html: str,
    application_url: str,
) -> str:
    """Email a job post to Blogger's Mail2Blogger address.

    Blogger's email publishing does not return a post ID or permalink and does
    not support updating a previously emailed post. The returned URL is the
    configured public blog homepage.
    """
    recipient = _required_setting("BLOGGER_POST_EMAIL")
    blog_url = _required_setting("BLOGGER_SITE_URL").rstrip("/") + "/"
    parsed_blog_url = urlparse(blog_url)
    if parsed_blog_url.scheme != "https" or not parsed_blog_url.netloc:
        raise RuntimeError("BLOGGER_SITE_URL must be a public HTTPS URL")

    host = _required_setting("SMTP_HOST")
    username = _required_setting("SMTP_USERNAME")
    password = _required_setting("SMTP_PASSWORD")
    sender = _required_setting("SMTP_FROM_EMAIL")
    port = int(os.getenv("SMTP_PORT", "587"))

    message = EmailMessage()
    message["Subject"] = title
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"{title}\nExperience level: {seniority}\n\n"
        "Open this email in an HTML-capable mail client to view the complete listing."
    )
    html_content = (
        f"<h1>{escape(title)}</h1>"
        f"<p><strong>Experience level:</strong> {escape(seniority)}</p>"
        f"{description_html}"
        f'<p><a href="{escape(application_url, quote=True)}">Apply through RecruitO</a></p>'
        "<p>#end</p>"
    )
    message.add_alternative(html_content, subtype="html")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(
                host, port, context=ssl.create_default_context(), timeout=20
            ) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError(f"Could not send the job post email: {exc}") from exc

    return json.dumps({"post_id": "", "url": blog_url})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
