"""Bound raw uploads before Starlette's multipart parser can spool them."""

from tempfile import TemporaryFile

from starlette.responses import JSONResponse

from app.documents.settings import DocumentSettings


class UploadBodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"].rstrip("/") != "/api/v1/documents"
        ):
            return await self.app(scope, receive, send)
        # Multipart names and headers consume the same finite budget as file bytes.
        limit = DocumentSettings().max_batch_bytes + 1024 * 1024

        async def reject():
            await JSONResponse(
                {
                    "error": {
                        "code": "UPLOAD_TOO_LARGE",
                        "message": "Upload request exceeds the configured size limit",
                        "details": None,
                    }
                },
                status_code=413,
            )(scope, receive, send)

        for name, value in scope["headers"]:
            if name.lower() == b"content-length":
                try:
                    if int(value) > limit:
                        return await reject()
                except ValueError:
                    pass
        # Buffer only the bounded raw stream. Parsing starts after the entire size is known,
        # including for chunked bodies and incorrect Content-Length declarations.
        with TemporaryFile() as body:
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > limit:
                    return await reject()
                body.write(chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            complete = False

            async def replay():
                nonlocal complete
                if complete:
                    return await receive()
                chunk = body.read(64 * 1024)
                complete = body.tell() == size
                return {"type": "http.request", "body": chunk, "more_body": not complete}

            await self.app(scope, replay, send)
