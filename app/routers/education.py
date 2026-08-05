# app/routers/education.py / یا داخل home.py
@router.get("/education")
async def education_page(...): return templates.TemplateResponse(..., "education.html", ...)

@router.get("/education/course/{id}")
async def education_course_page(...): return templates.TemplateResponse(..., "education_course.html", ...)

@router.get("/admin/analytics")
async def analytics_page(...): return templates.TemplateResponse(..., "analytics.html", ...)  # platform_admin only