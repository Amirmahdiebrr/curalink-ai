document.addEventListener("DOMContentLoaded", function () {

    const fileInput = document.getElementById("file");
    const fileLabel = document.getElementById("file-label");
    const dropzone = document.getElementById("dropzone");

    if (fileInput && fileLabel && dropzone) {

        function updateLabel(file) {
            fileLabel.textContent = file ? file.name : "فایل PDF یا تصویر آزمایش را انتخاب کنید";
        }

        fileInput.addEventListener("change", function () {
            updateLabel(fileInput.files[0]);
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
            const file = e.dataTransfer.files[0];
            if (file) {
                fileInput.files = e.dataTransfer.files;
                updateLabel(file);
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
                const formData = new FormData(form);

                const res = await fetch("/analyze", {
                    method: "POST",
                    body: formData
                });

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