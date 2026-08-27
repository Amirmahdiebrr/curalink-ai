"""
app/core/feature_flags.py

فلگ‌های ساده‌ی فیچر برای مخفی/آشکار کردن بخش‌هایی از پروژه که هنوز
آماده‌ی production نیستند (مثل صفحات placeholder با داده‌ی fake).
تغییر این مقادیر به True، بدون نیاز به تغییر تمپلیت‌ها یا روترها،
همان بخش را برای همه‌ی کاربران فعال می‌کند.
"""

# صفحه‌ی آموزش سلامت (education.html) — فعلاً محتوای واقعی ندارد.
FEATURE_EDUCATION_ENABLED = False

# داشبورد تحلیل داده‌ی سازمانی (analytics.html) — فعلاً به داده‌ی
# واقعی گزارش‌گیری وصل نیست.
FEATURE_ANALYTICS_ENABLED = False