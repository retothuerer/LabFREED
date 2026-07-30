// Marks .lf-service links as unreachable, asynchronously, without blocking page render.
// The reachability check itself runs server-side (see /check_service in app_factory.py) -
// checking arbitrary third-party service URLs from the browser directly would be limited
// by CORS to "did some response come back", not the real HTTP status.
(function () {
    function checkServiceLinks(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var links = scope.querySelectorAll('a.lf-service[data-check-service-url]');
        links.forEach(function (link) {
            if (link.dataset.availabilityChecked) return;
            link.dataset.availabilityChecked = 'true';

            var checkUrl = link.getAttribute('data-check-service-url');
            fetch(checkUrl, { signal: AbortSignal.timeout(4000) })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.reachable) {
                        link.classList.add('lf-service--unreachable');
                    }
                })
                .catch(function () {
                    // Couldn't reach our own /check_service endpoint (network hiccup,
                    // timeout) - leave the link unmarked rather than risk a false positive.
                });
        });
    }

    // htmx:load fires once for the initial page body and again for every fragment
    // htmx swaps in later (e.g. the landing page's slow-loading content) - this is
    // the one hook that covers both cases.
    document.body.addEventListener('htmx:load', function (evt) {
        checkServiceLinks(evt.detail && evt.detail.elt);
    });
})();
