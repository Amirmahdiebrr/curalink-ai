document.addEventListener("DOMContentLoaded", function () {

    const fileInput = document.getElementById("file");
    const fileLabel = document.getElementById("file-label");
    const dropzone = document.getElementById("dropzone");

    if (fileInput && fileLabel && dropzone) {

        function updateLabel(fileList) {
            if (!fileList || fileList.length === 0) {
                fileLabel.textContent = "یک یا چند فایل PDF/تصویر آزمایش را انتخاب کنید";
                return;
            }

            if (fileList.length === 1) {
                fileLabel.textContent = fileList[0].name;
                return;
            }

            fileLabel.textContent = `${fileList.length} فایل انتخاب شد`;
        }

        fileInput.addEventListener("change", function () {
            updateLabel(fileInput.files);
        });

        ["dragenter", "dragover"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                dropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                dropzone.classList.remove("dragover");
            });
        });

        dropzone.addEventListener("drop", function (e) {
            const droppedFiles = e.dataTransfer.files;
            if (droppedFiles && droppedFiles.length > 0) {
                fileInput.files = droppedFiles;
                updateLabel(droppedFiles);
            }
        });
    }

    const form = document.getElementById("upload-form");

    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();

            const submitBtn = form.querySelector("button[type='submit']");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "در حال ارسال...";
            }

            try {
                const formData = new FormData();

                const examType = document.getElementById("exam_type");
                if (examType) {
                    formData.append("exam_type", examType.value);
                }

                const symptoms = document.getElementById("symptoms");
                if (symptoms) {
                    formData.append("symptoms", symptoms.value);
                }

                const csrfInput = document.getElementById("csrf_token");
                if (csrfInput) {
                    formData.append("csrf_token", csrfInput.value);
                }

                if (fileInput && fileInput.files.length > 0) {
                    for (let i = 0; i < fileInput.files.length; i++) {
                        formData.append("files", fileInput.files[i]);
                    }
                }

                const res = await fetch("/analyze", {
                    method: "POST",
                    body: formData
                });

                if (res.status === 401) {
                    window.location.href = "/login";
                    return;
                }

                if (res.status === 403) {
                    alert("خطای اعتبارسنجی امنیتی. لطفاً صفحه را رفرش کرده و دوباره تلاش کنید.");
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = "شروع تحلیل با AI";
                    }
                    return;
                }

                if (!res.ok) {
                    throw new Error("Upload failed");
                }

                const data = await res.json();

                window.location.href = `/processing/${data.job_id}`;

            } catch (err) {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "شروع تحلیل با AI";
                }
                alert("خطا در ارسال فایل. لطفاً دوباره تلاش کنید.");
            }
        });
    }
});