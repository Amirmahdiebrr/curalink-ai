/**
 * app/static/js/workspace.js
 * Shared behavior for every healthcare workspace (doctor, hospital,
 * lab, nurse). Pure client-side: mobile sidebar toggle, table
 * search/filter over rows already rendered by the server, and a
 * generic details drawer. No network calls.
 */
(function () {

    var toggle = document.getElementById('cl-ws-toggle');
    var sidebar = document.getElementById('cl-ws-sidebar');
    var overlayBackdrop = document.getElementById('cl-ws-sidebar-backdrop');

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('is-open');
        if (overlayBackdrop) overlayBackdrop.classList.remove('is-open');
    }

    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('is-open');
            if (overlayBackdrop) overlayBackdrop.classList.toggle('is-open');
        });
    }
    if (overlayBackdrop) {
        overlayBackdrop.addEventListener('click', closeSidebar);
    }

    document.querySelectorAll('[data-ws-search]').forEach(function (input) {
        var targetSel = input.getAttribute('data-ws-search-target');
        var container = targetSel ? document.querySelector(targetSel) : null;
        if (!container) return;

        input.addEventListener('input', function () {
            var q = input.value.trim().toLowerCase();
            var rows = container.querySelectorAll('[data-ws-row]');
            var visible = 0;
            rows.forEach(function (row) {
                var text = (row.getAttribute('data-ws-search-text') || '').toLowerCase();
                var match = !q || text.indexOf(q) !== -1;
                row.style.display = match ? '' : 'none';
                if (match) visible++;
            });
            var emptyEl = container.parentElement ? container.parentElement.querySelector('[data-ws-empty]') : null;
            if (emptyEl) emptyEl.style.display = visible === 0 ? '' : 'none';
        });
    });

    document.querySelectorAll('[data-ws-filter-group]').forEach(function (group) {
        var targetSel = group.getAttribute('data-ws-filter-target');
        var container = targetSel ? document.querySelector(targetSel) : null;
        if (!container) return;

        var chips = group.querySelectorAll('[data-ws-filter-value]');
        chips.forEach(function (chip) {
            chip.addEventListener('click', function () {
                chips.forEach(function (c) { c.classList.remove('is-active'); });
                chip.classList.add('is-active');
                var val = chip.getAttribute('data-ws-filter-value');
                var rows = container.querySelectorAll('[data-ws-row]');
                var visible = 0;
                rows.forEach(function (row) {
                    var key = row.getAttribute('data-ws-filter-key') || '';
                    var match = val === 'all' || key === val;
                    row.style.display = match ? '' : 'none';
                    if (match) visible++;
                });
                var emptyEl = container.parentElement ? container.parentElement.querySelector('[data-ws-empty]') : null;
                if (emptyEl) emptyEl.style.display = visible === 0 ? '' : 'none';
            });
        });
    });

    document.querySelectorAll('[data-ws-open-drawer]').forEach(function (trigger) {
        trigger.addEventListener('click', function () {
            var drawerId = trigger.getAttribute('data-ws-open-drawer');
            var overlay = document.getElementById(drawerId);
            if (!overlay) return;

            overlay.querySelectorAll('[data-ws-fill]').forEach(function (field) {
                var key = field.getAttribute('data-ws-fill');
                var value = trigger.getAttribute('data-ws-field-' + key);
                if (value !== null) field.textContent = value;
            });

            overlay.classList.add('is-open');
        });
    });

    document.querySelectorAll('.cl-ws-drawer-overlay').forEach(function (overlay) {
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) overlay.classList.remove('is-open');
        });
        var closeBtn = overlay.querySelector('.cl-ws-drawer-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () { overlay.classList.remove('is-open'); });
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.cl-ws-drawer-overlay.is-open').forEach(function (o) {
                o.classList.remove('is-open');
            });
            closeSidebar();
        }
    });

})();