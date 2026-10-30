"""Test-only assembly of the profiles router with the real foundation middleware."""

from app import main
from app.platform.routes import router as platform_router
from app.profiles.routes import router as profiles_router
from fastapi import APIRouter

# Shared application registration belongs to member 5; this entrypoint is only a test harness.
router = APIRouter()
router.include_router(profiles_router)
router.routes.extend(
    route for route in platform_router.routes if not route.path.startswith(("/forms", "/profiles"))
)
main.router = router
app = main.create_app()
