"""
app/prompts/classify_prompt.py

Lightweight classification prompt used to detect the *actual* type
of an uploaded medical document from its OCR text, independent of
whatever exam_type the user selected in the upload form.
"""

CLASSIFY_PROMPT_TEMPLATE = """
تو یک متخصص تشخیص نوع مدارک پزشکی هستی.

متن زیر از روی یک مدرک پزشکی توسط OCR استخراج شده است. وظیفه‌ی تو این
است که نوع این مدرک را از میان کدهای زیر تشخیص بدهی:

blood -> آزمایش خون (CBC، هموگلوبین، پلاکت، RBC، WBC و مشابه)
urine -> آزمایش ادرار (Urine Analysis، وزن مخصوص ادرار، pH ادرار و مشابه)
biochemistry -> بیوشیمی خون (قند خون، چربی خون، کلسترول، تری‌گلیسیرید، کراتینین، آنزیم‌های کبدی و مشابه؛ در صورتی که CBC در متن نباشد)
sonography -> گزارش سونوگرافی
radiology -> گزارش رادیولوژی / X-Ray
mri -> گزارش MRI
ct_scan -> گزارش CT Scan
mammography -> گزارش ماموگرافی
hse -> گزارش معاینات طب کار / HSE (معمولاً ترکیبی از چند بخش مثل اسپیرومتری، ادیومتری، بینایی‌سنجی، رادیوگرافی قفسه سینه، نوار قلب و آزمایش‌های پایه، همراه با نظر نهایی صلاحیت شغلی)
other -> هر مدرک پزشکی دیگری که با موارد بالا مطابقت ندارد

فقط و فقط دقیقاً یکی از این کدها (مثلاً: blood) را به‌عنوان خروجی
برگردان. هیچ توضیح، علامت‌گذاری، یا متن اضافه‌ای ننویس.

متن مدرک:
-----------------------
{}
"""