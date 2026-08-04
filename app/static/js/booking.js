/**
 * app/static/js/booking.js
 * Client-side booking stepper (UI-only). No backend endpoint exists
 * for real appointments yet — final step explicitly tells the user
 * this is a placeholder instead of pretending to submit anywhere.
 */
(function () {
    function initBooking(modal) {
        var steps = modal.querySelectorAll('.cl-stepper-step');
        var panels = modal.querySelectorAll('.cl-booking-panel');
        var current = 0;
        var selectedService = null;

        function render() {
            steps.forEach(function (s, i) {
                s.classList.toggle('is-active', i === current);
                s.classList.toggle('is-done', i < current);
            });
            panels.forEach(function (p, i) {
                p.classList.toggle('is-active', i === current);
            });
        }

        modal.querySelectorAll('.cl-booking-option[data-service]').forEach(function (opt) {
            opt.addEventListener('click', function () {
                modal.querySelectorAll('.cl-booking-option').forEach(function (o) { o.classList.remove('is-selected'); });
                opt.classList.add('is-selected');
                selectedService = opt.getAttribute('data-service');
                var summary = modal.querySelector('[data-selected-service]');
                if (summary) summary.textContent = selectedService;
            });
        });

        modal.querySelectorAll('[data-step-next]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (current < panels.length - 1) { current++; render(); }
            });
        });
        modal.querySelectorAll('[data-step-prev]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (current > 0) { current--; render(); }
            });
        });

        render();
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.cl-booking-modal').forEach(initBooking);

        document.querySelectorAll('[data-open-booking]').forEach(function (trigger) {
            trigger.addEventListener('click', function (e) {
                e.preventDefault();
                var overlay = document.getElementById('cl-booking-overlay');
                if (overlay) overlay.classList.add('is-open');
            });
        });
        var closeBtn = document.getElementById('cl-booking-close');
        var overlay = document.getElementById('cl-booking-overlay');
        if (closeBtn && overlay) {
            closeBtn.addEventListener('click', function () { overlay.classList.remove('is-open'); });
            overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.classList.remove('is-open'); });
        }
    });
})();