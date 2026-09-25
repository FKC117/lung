# Production prescription media

Prescription PDFs and rendered page images contain patient data. They must
never be exposed by a web server's general `MEDIA_ROOT` mapping.

The application exposes these files only through authenticated, authorized
API actions:

- `/api/prescriptions/documents/<document_id>/source-file/`
- `/api/prescriptions/documents/<document_id>/pages/<page_id>/image/`

Non-staff access is limited to the uploader or an assigned/completed reviewer.
Staff and superusers retain registry-wide access. The API deliberately returns
API URLs instead of raw `/media/` URLs.

## Required reverse-proxy rule

Use the applicable checked-in example:

- [`nginx.conf.example`](nginx.conf.example)
- [`apache.conf.example`](apache.conf.example)

The denial must cover both paths before or in addition to the general media
mapping:

- `/media/prescriptions/`
- `/media/prescription_pages/`

Do not replace these rules with `X-Accel-Redirect`, `X-Sendfile`, or a public
object-storage URL unless the replacement preserves the same per-request API
authorization. If prescription media is moved to object storage, use private
objects and short-lived URLs issued only after the API authorization check.

## Deployment verification

1. Test the server configuration before reload:
   - Nginx: `sudo nginx -t`
   - Apache: `sudo apachectl configtest`
2. Reload the web server.
3. Verify both direct paths return `403` or `404`, even with a valid application
   session:
   - `curl -I https://registry.example.org/media/prescriptions/test.pdf`
   - `curl -I https://registry.example.org/media/prescription_pages/test.png`
4. Verify an unauthorized account receives `404` from each API file endpoint.
5. Verify the uploader, assigned reviewer, or staff user can retrieve the same
   file through its API endpoint.

The Django URL denial remains as defense in depth for development and any
deployment that routes media requests through Django. It does not replace the
Nginx or Apache rule.
