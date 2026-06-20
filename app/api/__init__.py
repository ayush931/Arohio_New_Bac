from fastapi import APIRouter
from .routes_home import router as home_router
from .routes_users import router as user_router
from .routes_ai_chat import router as chat_router
from .routes_upload_pdf_images import router as upload_pdf_images
from .uploads import router as uploads_routers
from .routes_uploads_excel_to_alttext import router as uploads_excel_to_alttext
from .routes_projects import router as projects_routes
from .routes_projects_files import router as projects_files_routes
from .routes_user_plans import router as user_plans
from .routes_plans_transactions import router as plans_transactions
from .routes_usage_logs import router as usage_logs
from .newsletter import router as newsletters
from .routes_about import router as aboutus
from .routes_contact import router as conatctus
from .routes_contact_support import router as contact_support
from .routes_blogs import router as blogs_import
from .routes_admin_audits import router as admin_audits
from .roles import router as roless
from .admin_users import router as admin_userss
api_router = APIRouter()

api_router.include_router(home_router)
api_router.include_router(user_router)
api_router.include_router(chat_router)
api_router.include_router(upload_pdf_images)
api_router.include_router(uploads_routers)
api_router.include_router(uploads_excel_to_alttext)
api_router.include_router(projects_routes)
api_router.include_router(projects_files_routes)
api_router.include_router(user_plans)
api_router.include_router(plans_transactions)
api_router.include_router(usage_logs)
api_router.include_router(newsletters)
api_router.include_router(aboutus)
api_router.include_router(conatctus)
api_router.include_router(contact_support)
api_router.include_router(blogs_import)
api_router.include_router(admin_audits)
api_router.include_router(roless)
api_router.include_router(admin_userss)