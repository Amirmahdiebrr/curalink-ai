async def process(
        self,
        files: list[tuple[bytes, str]],
        exam_type: str = None,
        symptoms: str | None = None,
        patient_age: int | None = None,
        patient_gender: str | None = None,
        on_stage=None,
    ):
        total_start = time.perf_counter()

        logger.info("=" * 50)
        logger.info("START REPORT PROCESS")
        logger.info(f"FILE COUNT: {len(files)}")
        logger.info(f"EXAM TYPE: {exam_type}")
        logger.info(f"HAS SYMPTOMS: {bool(symptoms and symptoms.strip())}")
        logger.info(f"PATIENT AGE/GENDER: {patient_age} / {patient_gender}")
        logger.info("=" * 50)

        requested_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)

        self._notify(on_stage, "saving")

        saved_paths = []
        original_names = []

        for content, original_filename in files:
            try:
                filepath = self.file_service.save_bytes(original_filename, content)
            except Exception as e:
                logger.error(f"[ReportService] File validation/save failed for {original_filename}: {e}")
                continue

            saved_paths.append(filepath)
            original_names.append(original_filename)

        if not saved_paths:
            raise Exception("هیچ‌کدام از فایل‌های ارسالی معتبر نبودند یا ذخیره نشدند.")

        self._notify(on_stage, "ocr")

        ocr_tasks = [
            self._ocr_single_file(filepath, filename, index + 1)
            for index, (filepath, filename) in enumerate(zip(saved_paths, original_names))
        ]

        ocr_results = await asyncio.gather(*ocr_tasks)

        self._cleanup_files(saved_paths)

        combined_parts = []
        full_ocr_parts = []
        failed_filenames = []

        for part_text, failed_filename in ocr_results:
            if part_text:
                combined_parts.append(part_text)
                full_ocr_parts.append(part_text)
            if failed_filename:
                failed_filenames.append(failed_filename)

        if not combined_parts:
            raise Exception("استخراج متن از هیچ‌یک از فایل‌های ارسالی موفق نبود.")

        full_ocr_text = "\n\n".join(full_ocr_parts)
        limited_text = self._build_limited_text(combined_parts)

        ocr_warning = self._notify_ocr_failures(failed_filenames)

        # اگر کاربر خودش نوع آزمایش معتبر را انتخاب کرده، مرحله‌ی
        # تشخیص خودکار (که یک فراخوانی کامل AI اضافه است) را کاملاً
        # رد می‌کنیم تا زمان کل تحلیل تقریباً نصف شود.
        exam_type_mismatch = False
        final_exam_type = exam_type
        detected_exam_type = None

        if not exam_type or exam_type not in VALID_EXAM_TYPES:
            detected_exam_type = await self._detect_exam_type(limited_text)
            if detected_exam_type:
                final_exam_type = detected_exam_type

        self._notify(on_stage, "ai")

        symptoms_display = self._prepare_symptoms(symptoms)
        patient_profile = self._prepare_patient_profile(patient_age, patient_gender)

        prompt_template = get_prompt_template(final_exam_type)

        prompt = prompt_template.format(
            text=limited_text,
            symptoms=symptoms_display,
            patient_profile=patient_profile,
        )

        raw_analysis = await self.ai.analyze(prompt)

        narrative_text, structured_results = self._extract_structured_results(raw_analysis)

        analysis_html = self._to_html(narrative_text)

        total_elapsed = time.perf_counter() - total_start

        logger.info(
            f"[ReportService] Finished in {total_elapsed:.2f}s, "
            f"structured_results: {len(structured_results)}"
        )

        if len(original_names) == 1:
            filename_display = original_names[0]
        else:
            filename_display = f"{original_names[0]} و {len(original_names) - 1} فایل دیگر"

        return {
            "exam_type": final_exam_type,
            "filename": filename_display,
            "ocr": full_ocr_text,
            "analysis": narrative_text,
            "analysis_html": analysis_html,
            "structured_results": structured_results,
            "symptoms": (symptoms or "").strip() or None,
            "exam_type_mismatch": exam_type_mismatch,
            "requested_exam_type_label": requested_label if exam_type_mismatch else None,
            "detected_exam_type_label": (
                EXAM_TYPE_LABELS.get(detected_exam_type, detected_exam_type)
                if exam_type_mismatch else None
            ),
            "ocr_warning": ocr_warning,
        }